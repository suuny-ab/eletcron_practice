# RAG 技术设计文档

## 概述

本项目实现了一个完整的 RAG（Retrieval-Augmented Generation）检索增强生成系统，用于智能知识库问答。系统采用**向量检索 + BM25 混合检索 + LLM 重排序**的三阶段检索策略，显著提升了检索的准确性和相关性。

## 系统架构

```
用户问题
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG 检索管道                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐    ┌──────────────┐                     │
│   │ 向量检索      │    │ BM25 检索    │                     │
│   │ (ChromaDB)   │    │ (rank-bm25)  │                     │
│   │              │    │              │                     │
│   │ Top-20 结果  │    │ Top-20 结果  │                     │
│   └──────┬───────┘    └──────┬───────┘                     │
│          │                   │                             │
│          └─────────┬─────────┘                             │
│                    ▼                                       │
│          ┌─────────────────┐                               │
│          │   混合评分融合   │                               │
│          │ vector*0.6 +    │                               │
│          │ bm25*0.4        │                               │
│          └────────┬────────┘                               │
│                   ▼                                        │
│          ┌─────────────────┐                               │
│          │  LLM 重排序     │                               │
│          │  (Top-K 精选)   │                               │
│          └────────┬────────┘                               │
│                   ▼                                        │
│            检索结果 (Top-3)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│  上下文构建     │
│  + LLM 生成     │
└─────────────────┘
    │
    ▼
  最终答案
```

## 核心技术实现

### 1. 文档索引

#### 1.1 文档切分策略

采用**基于标题层级的语义切分**，确保每个文档块保持语义完整性：

```python
# 切分配置
CHUNK_SIZE = 500          # 文档块最大长度
CHUNK_OVERLAP = 100       # 重叠长度（用于超长块二次切分）
MIN_CHUNK_SIZE = 80       # 最小长度（用于合并过短块）

# 标题层级切分
MARKDOWN_HEADERS_TO_SPLIT_ON = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    # ...
]
```

**切分流程：**
1. **Frontmatter 解析**：提取 YAML 元数据（标签、标题等）
2. **标题树构建**：按 Markdown 标题层级构建树结构
3. **智能合并**：合并过短的小节，保持语义完整
4. **保护块处理**：代码块、表格等不被切分
5. **二次切分**：超长块按句子边界切分并添加重叠

#### 1.2 双重索引机制

**向量索引（ChromaDB）：**
- 使用 LangChain 集成的 Chroma 向量数据库
- 支持语义相似度检索
- 持久化存储，支持增量更新

**BM25 索引（rank-bm25）：**
- 基于词频的传统检索算法
- 中英文混合分词：英文按单词，中文按单字
- 内存索引，支持实时更新

```python
# BM25 分词实现
def _tokenize(self, text: str) -> list[str]:
    parts = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text.lower())
    tokens = []
    for part in parts:
        if re.match(r"[\u4e00-\u9fff]+", part):
            tokens.extend(list(part))  # 中文单字切分
        else:
            tokens.append(part)  # 英文保持完整
    return tokens
```

### 2. 混合检索算法

#### 2.1 分数归一化

将不同检索源的分数统一到 [0, 1] 区间：

```python
def _normalize_scores(self, scores: list[float]) -> list[float]:
    """Min-Max 归一化"""
    if not scores:
        return []
    min_score = min(scores)
    max_score = max(scores)
    if math.isclose(max_score, min_score):
        return [1.0 for _ in scores]  # 避免除零
    return [(s - min_score) / (max_score - min_score) for s in scores]
```

#### 2.2 混合评分公式

```python
# 配置权重
VECTOR_WEIGHT = 0.6  # 向量检索权重
BM25_WEIGHT = 0.4    # BM25 检索权重

# 混合评分计算
hybrid_score = VECTOR_WEIGHT * vector_norm + BM25_WEIGHT * bm25_norm
```

**权重选择理由：**
- 向量检索擅长语义理解，权重较高
- BM25 检索擅长精确匹配，作为补充
- 经验值 0.6:0.4 在知识库场景表现良好

#### 2.3 候选去重

使用 `chunk_id` 作为唯一标识，避免重复文档：

```python
# 去重逻辑
key = metadata.get("chunk_id") or f"{metadata.get('filename', '')}::{content}"
if key not in candidates:
    candidates[key] = {...}
```

### 3. LLM 重排序

#### 3.1 重排序原理

利用大语言模型的语义理解能力，对混合检索的候选结果进行二次排序：

```python
def _llm_rerank(self, question: str, candidates: list[dict], top_k: int) -> list[int]:
    """
    使用 LLM 对候选进行重排序
    
    输入：问题 + 候选文档摘要
    输出：按相关性排序的索引列表
    """
    # 构建候选摘要（截断到 400 字符）
    snippets = []
    for idx, cand in enumerate(candidates):
        snippet = cand["content"][:400] + "..." if len(cand["content"]) > 400 else cand["content"]
        snippets.append(f"{idx}. {snippet}")
    
    # 调用 LLM 进行重排序
    indices = self._llm_task_service.invoke(
        task_type="rerank",
        question=question,
        candidates="\n".join(snippets),
        top_k=top_k
    )
    
    # 验证和过滤索引
    return self._filter_valid_indices(indices, len(candidates), top_k)
```

#### 3.2 索引验证

确保 LLM 返回的索引有效且无重复：

```python
def _filter_valid_indices(self, indices, max_idx, top_k):
    seen = set()
    filtered = []
    for idx in indices:
        if isinstance(idx, int) and 0 <= idx < max_idx and idx not in seen:
            seen.add(idx)
            filtered.append(idx)
        if len(filtered) >= top_k:
            break
    return filtered
```

### 4. 检索配置

```python
# 各阶段召回数量
VECTOR_TOP_K = 20    # 向量检索召回数
BM25_TOP_K = 20      # BM25 检索召回数
HYBRID_TOP_K = 40    # 混合候选数量上限

# 默认返回 Top-3 最相关结果
DEFAULT_TOP_K = 3
```

## 索引管理

### 1. 全量索引

```python
def _full_index(self):
    """全量索引流程"""
    # 1. 检查索引标记，跳过已索引数据
    if self._should_skip_full_index():
        self._rebuild_bm25_from_files()
        return
    
    # 2. 收集所有 Markdown 文件
    md_files = list(self._notes_root.rglob("*.md"))
    
    # 3. 切分文档
    documents = self._collect_documents_from_files(md_files)
    
    # 4. 批量添加到向量库
    added = self._add_texts_in_batches(texts, metadatas, batch_size=20)
    
    # 5. 构建 BM25 索引
    self._bm25_index.build(documents)
    
    # 6. 写入索引标记
    self._write_index_marker(file_count, chunk_count)
```

### 2. 增量索引

监听文件变化，实现实时索引更新：

```python
def _on_file_changed(self, file_path: str, event_type: str):
    """文件变化回调"""
    if event_type == "deleted":
        self._remove_file_documents(relative_path)
    else:
        self._index_single_file(file_path, relative_path)
```

### 3. 索引标记同步机制

**问题背景**：增量索引（文件新增/修改/删除）会改变向量库中的实际文档数量，但如果不同步更新 `index_marker.json` 中的 `chunk_count`，会导致系统重启时检测到"数据不一致"，误触发全量重建。

**解决方案**：`_sync_marker_to_actual()` 方法

```python
def _sync_marker_to_actual(self):
    """将 index_marker 同步为向量库的实际数据量"""
    actual_count = self._vectorstore._collection.count()
    marker = self._load_index_marker()
    file_count = marker.get("file_count", 0) if marker else 0
    self._write_index_marker(file_count=file_count, chunk_count=actual_count)
```

**调用时机**：
1. `_index_single_file()` 完成后 — 增量索引会增加 chunk_count
2. `_remove_file_documents()` 完成后 — 文件删除会减少 chunk_count

**效果**：确保 `index_marker.json` 始终反映向量库的真实状态，避免不必要的全量重建。

### 4. 停止信号机制

支持优雅中断长时间索引任务：

```python
def _add_texts_in_batches(self, texts, metadatas, batch_size=20):
    for i in range(0, total, batch_size):
        # 检查停止信号
        if self._stop_event.is_set():
            logger.info(f"收到停止信号，已添加 {added}/{total} 个文档")
            return added
        
        # 批量添加
        self._vectorstore.add_texts(batch_texts, batch_metadatas)
        added += len(batch_texts)
    
    return added
```

## 性能优化

### 1. 索引优化

| 优化项 | 说明 |
|--------|------|
| 批量添加 | 每批 20 个文档，减少 I/O 次数 |
| 索引标记 | 跳过已索引数据，避免重复索引 |
| 增量更新 | 文件级更新，无需全量重建 |
| 停止信号 | 支持中断，避免阻塞应用关闭 |

### 2. 检索优化

| 优化项 | 说明 |
|--------|------|
| 分数缓存 | 归一化分数在单次检索中复用 |
| 候选去重 | 使用 chunk_id 快速去重 |
| 内容截断 | LLM 重排序时截断长文本 |
| 索引验证 | 过滤无效索引，增强鲁棒性 |

## 可观测性

### 1. 性能指标

```python
# 记录检索耗时
metrics.observe("rag.retrieval.duration_seconds", elapsed)
metrics.increment("rag.retrieval.queries")

# 记录索引耗时
metrics.observe("rag.index.duration_seconds", elapsed)
metrics.increment("rag.index.files_indexed", file_count)
metrics.increment("rag.index.chunks_created", chunk_count)
```

### 2. 结构化日志

```python
logger.info(
    "全量索引完成",
    extra={"context": LogContext(
        operation="rag.index.full",
        duration_ms=elapsed * 1000,
        extra={"files": file_count, "chunks": chunk_count}
    )}
)
```

### 3. 数据一致性校验

系统启动时执行索引标记验证（`_should_skip_full_index`），确保索引数据完整性：

1. 读取 `index_marker.json` 中的 `chunk_count`
2. 查询向量库实际文档数 `vectorstore.count()`
3. 两者不一致时，删除 marker 并触发全量重建

```
# 日志示例
[RAG] 向量库数据量不一致 (期望:862, 实际:863)，重新索引
[RAG] 已清理向量库旧数据 (863 条)
[RAG] 全量索引完成，共添加 863 个文档块
```

配合增量索引的 `_sync_marker_to_actual()` 机制，可有效避免因增量操作导致的误判重建。

## 技术选型理由

| 技术 | 选择 | 理由 |
|------|------|------|
| 向量数据库 | ChromaDB | 轻量级、Python 原生、适合本地部署 |
| BM25 实现 | rank-bm25 | 纯 Python、易于集成、性能足够 |
| 文本切分 | 自研 | 针对 Markdown 优化、保护代码块 |
| LLM 框架 | LangChain | 生态丰富、易于扩展、支持流式输出 |

## 与传统搜索对比

| 特性 | 传统关键词搜索 | 本项目 RAG |
|------|---------------|-----------|
| 语义理解 | 无 | 向量检索支持 |
| 精确匹配 | 支持 | BM25 支持 |
| 同义词处理 | 需要词典 | 向量自动处理 |
| 排序质量 | 词频统计 | LLM 语义排序 |
| 上下文生成 | 无 | LLM 生成答案 |

## 测试覆盖

本模块包含完整的单元测试：

- **test_bm25_index.py**: 21 个测试用例
  - 分词测试（中英文、混合、特殊字符）
  - 索引构建测试
  - 检索测试（相关性、Top-K、空查询）
  - 文件更新测试
  - 线程安全测试

- **test_retrieval_service.py**: 23 个测试用例
  - 分数归一化测试
  - LLM 重排序测试（正常、异常、边界情况）
  - 混合检索测试
  - 上下文构建测试

- **test_index_service.py**: 19 个测试用例
  - 文档收集测试
  - 批量添加测试
  - 索引标记测试
  - 启动/停止测试

## 扩展方向

1. **多语言支持**：集成专业分词器（jieba、pkuseg）
2. **检索评估**：引入 MRR、NDCG 等评估指标
3. **Query 改写**：使用 LLM 扩展查询
4. **知识图谱**：结合实体关系增强检索
5. **缓存机制**：热门查询结果缓存
