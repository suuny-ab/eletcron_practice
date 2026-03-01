# 统一 Agent 工作流设计文档

## 概述

统一 Agent 工作流（UnifiedAgent）是系统的核心 AI 交互引擎，基于 **LangGraph 状态机模式** 实现。它将用户输入通过意图识别、文档检查、RAG 检索循环、权限校验等节点进行处理，最终生成流式响应。

**核心特性**：
- 基于状态图的条件路由，支持 5 种意图类型
- RAG 检索循环（最多 3 轮：检索 → 评估 → 查询重写）
- 全程流式输出（status / thinking / sources / chunk / diff / complete）
- 会话记忆管理（JSONL 持久化、摘要滚动）
- 节点级指标采集

## 系统架构

### 节点拓扑

```
                        ┌────────────────┐
                        │  load_history  │  加载会话历史和摘要
                        └───────┬────────┘
                                │
                        ┌───────▼────────┐
                        │   classify     │  识别用户意图
                        └───────┬────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
     intent=chitchat    needs_doc=true     needs_rag=true
              │                 │                  │
              ▼                 ▼                  │
        [流外生成]       ┌─────────────┐           │
        direct_answer    │  check_doc  │           │
                         └──────┬──────┘           │
                                │                  │
                    ┌───────────┼──────────┐       │
                    │                      │       │
             doc缺失                  doc存在       │
                    │                      │       │
                    ▼                      │       │
             ┌────────────┐               │       │
             │ prompt_doc │               │       │
             │  (提示用户) │               │       │
             └────────────┘               │       │
                                          │       │
                 ┌────────────────────────┼───────┘
                 │                        │
          needs_rag=true           needs_rag=false
                 │                        │
                 ▼                        ▼
          ┌────────────┐        ┌─────────────────┐
          │  analyze   │        │check_permission │
          └─────┬──────┘        └────────┬────────┘
                │                        │
                ▼                ┌───────┼───────┐
         ┌────────────┐         │               │
         │  retrieve   │    权限不足         权限满足
         └─────┬──────┘        │               │
               │                ▼               ▼
               ▼         ┌──────────┐    [流外生成]
        ┌────────────┐   │suggest_  │    doc_advise /
        │  evaluate  │   │mode      │    doc_edit /
        └─────┬──────┘   └──────────┘    doc_format
              │
    ┌─────────┼─────────┐
    │         │         │
  retry    proceed   give_up
    │         │         │
    ▼         │         │
┌──────────┐  │         │
│ rewrite  │  │         │
└────┬─────┘  │         │
     │        │         │
     └──►retrieve      │
     (循环)    │         │
              ▼         ▼
        [流外生成]  [流外生成]
        generate    generate
        _answer     _answer
```

### 意图类型

| 意图 | 说明 | 需要文档 | 需要 RAG | 需要权限 |
|------|------|---------|---------|---------|
| `chitchat` | 闲聊/通用问答 | 否 | 否 | assistant |
| `rag_query` | 知识库问答 | 否 | 是 | assistant |
| `doc_advise` | 文档分析建议 | 是 | 可选 | assistant |
| `doc_edit` | 文档编辑 | 是 | 否 | **editor** |
| `doc_format` | 文档格式化 | 是 | 否 | **editor** |

## Agent 状态

**文件**：`backend/domain/ai/agent/state.py`

```python
UnifiedAgentState = TypedDict(
    # --- 输入 ---
    session_id: str                  # 会话标识
    user_input: str                  # 用户输入
    permission_mode: str             # 权限模式 (assistant/editor)
    document_content: str | None     # 文档内容（可选）
    document_name: str | None        # 文档名称（可选）

    # --- 历史上下文 ---
    history_summary: str             # 历史摘要
    recent_turns: list[dict]         # 近期对话轮次

    # --- 意图分类 ---
    intent_type: str                 # 意图类型
    needs_rag: bool                  # 是否需要 RAG 检索
    needs_doc: bool                  # 是否需要文档

    # --- RAG 检索状态 ---
    analysis: dict                   # 问题分析结果
    current_round: int               # 当前检索轮次
    max_rounds: int                  # 最大检索轮次（默认 3）
    current_query: str               # 当前查询（可被 rewrite 更新）
    all_sources: list[dict]          # 累积的检索结果
    evaluation: dict                 # 评估结果
    top_k: int                       # 每轮检索数量

    # --- 输出 ---
    output_messages: list[dict]      # 流式消息队列
    final_output: str                # 最终文本输出

    # --- 控制流 ---
    should_end: bool                 # 是否提前结束
    end_reason: str                  # 结束原因 (prompt_doc/suggest_mode)
    error: str                       # 错误信息
)
```

## 流式消息协议

Agent 通过 `output_messages` 队列向前端发送流式消息，格式统一为：

```json
{"type": "<类型>", "content": "<内容>", "data": {<附加数据>}}
```

| 类型 | 说明 | 示例 |
|------|------|------|
| `status` | 阶段状态更新 | `{"stage": "classifying"}` |
| `thinking` | AI 思考过程 | 推理文本 |
| `sources` | 检索来源列表 | `[{filename, content, score}]` |
| `chunk` | 流式文本输出 | 逐块文本 |
| `diff` | 文档修改差异 | `{format, edited_content}` |
| `prompt` | 需要用户操作 | 提示选择文档/切换模式 |
| `error` | 错误消息 | 异常信息 |
| `complete` | 完成信号 | `{intent_type, retrieval_rounds, total_sources}` |

## 节点实现

### 1. 历史加载（load_history）

**文件**：`backend/domain/ai/agent/nodes/history.py`

- 从 `UnifiedMemoryManager` 加载当前会话历史
- 返回 `history_summary`（摘要文本）和 `recent_turns`（近期对话轮次）
- 对应保存方法 `save_history` 在工作流结束时调用

### 2. 意图分类（classify）

**文件**：`backend/domain/ai/agent/nodes/classify.py`

调用 LLM 分析用户输入，输出结构化 JSON：

```json
{
    "intent_type": "rag_query",
    "needs_rag": true,
    "needs_doc": false,
    "reasoning": "用户在询问知识库中的内容..."
}
```

**降级策略**：JSON 解析失败时，根据是否有文档上下文自动判断意图。

### 3. 文档检查（check_doc）

**文件**：`backend/domain/ai/agent/nodes/check_doc.py`

- `needs_doc=true` 且无文档内容 → `should_end=true, end_reason="prompt_doc"`
- 文档存在 → 发送 thinking 消息 "已获取文档: {name}"
- 配套 `prompt_document()` 节点生成用户提示

### 4. 问题分析（analyze）

**文件**：`backend/domain/ai/agent/nodes/analyze.py`

RAG 流程入口，调用 LLM 分析问题：

```json
{
    "question_type": "knowledge_query",
    "should_retrieve": true,
    "key_entities": ["机器学习", "深度学习"],
    "initial_query": "优化后的检索查询"
}
```

### 5. 检索执行（retrieve）

**文件**：`backend/domain/ai/agent/nodes/retrieve.py`

- 调用 `retrieval_service.retrieve_sources(query, top_k)` 执行混合检索
- 结果与已有来源去重（基于 filename + content[:100]）
- 合并到 `all_sources`，递增 `current_round`

### 6. 结果评估（evaluate）

**文件**：`backend/domain/ai/agent/nodes/evaluate.py`

调用 LLM 评估检索结果是否足以回答问题：

```json
{
    "is_sufficient": false,
    "confidence": 0.4,
    "missing_aspects": ["最新进展", "应用场景"],
    "suggestion": "retry"
}
```

**路由决策**：
- `retry` 且未达最大轮次 → 进入 rewrite 节点
- `proceed` → 进入生成阶段
- `give_up` 或超出轮次 → 基于已有结果生成

### 7. 查询重写（rewrite）

**文件**：`backend/domain/ai/agent/nodes/rewrite.py`

根据评估中的 `missing_aspects` 重构检索查询，然后回到 retrieve 节点形成循环。

### 8. 权限检查（check_permission）

**文件**：`backend/domain/ai/agent/nodes/check_permission.py`

权限级别：`assistant(0) < editor(1)`

| 意图 | 需要权限 |
|------|---------|
| chitchat / rag_query / doc_advise | assistant |
| doc_edit / doc_format | editor |

权限不足时触发 `suggest_mode_switch` 提示用户切换模式。

### 9. 流式生成节点（图外处理）

以下节点在图执行完成后由 `astream()` 方法根据 `intent_type` 调用，以 AsyncGenerator 方式流式输出：

| 节点 | 文件 | 输入 | 输出类型 |
|------|------|------|---------|
| `direct_answer` | `nodes/direct.py` | 用户输入 + 历史 | chunk（纯文本流） |
| `generate_answer` | `nodes/generate.py` | 用户输入 + RAG 来源 | sources + chunk |
| `advise_document` | `nodes/doc_advise.py` | 文档 + 用户需求 + RAG 来源(可选) | chunk |
| `edit_document` | `nodes/doc_edit.py` | 文档 + 编辑需求 | chunk + diff |
| `format_document` | `nodes/doc_format.py` | 文档内容 | chunk + diff |

**diff 消息格式**：
```json
{
    "type": "diff",
    "content": "unified diff 文本",
    "data": {
        "format": "unified_diff",
        "original_length": 1500,
        "edited_length": 1520,
        "edited_content": "完整的编辑后内容"
    }
}
```

## 条件路由

**文件**：`backend/domain/ai/agent/graphs/unified_agent.py`

```python
# classify 之后
def _route_after_classify(state):
    if intent == "chitchat":
        return "generate"          # → END（流外处理）
    elif needs_doc:
        return "check_doc"
    elif needs_rag:
        return "rag_analyze"
    else:
        return "generate"          # → END

# check_doc 之后
def _route_after_check_doc(state):
    if should_end:
        return "prompt_doc"        # → END
    elif needs_rag:
        return "rag_analyze"
    else:
        return "check_permission"

# evaluate 之后
def _route_after_evaluate(state):
    if suggestion == "retry" and current_round < max_rounds:
        return "rewrite"           # → retrieve（循环）
    elif needs_doc:
        return "check_permission"
    else:
        return "done"              # → END（流外处理）

# check_permission 之后
def _route_after_permission(state):
    if should_end:
        return "suggest_mode"      # → END
    else:
        return "done"              # → END（流外处理）
```

## 执行流程

`astream()` 方法的五个阶段：

```
阶段 1: 图状态转换
├─ 构建初始状态
├─ 执行 LangGraph 图（astream, stream_mode="values"）
├─ 增量发送 output_messages 中的新消息
└─ 收集最终状态

阶段 2: 检查提前结束
├─ should_end=true → 发送 complete + 保存历史 → return
└─ 继续

阶段 3: 流式生成（根据 intent_type 分发）
├─ chitchat → direct_answer
├─ rag_query → generate_answer
├─ doc_advise → advise_document
├─ doc_edit → edit_document
└─ doc_format → format_document

阶段 4: 保存历史
├─ 记录 final_output
├─ 调用 save_history → UnifiedMemoryManager
└─ 更新会话元数据 (标题/轮次/意图/文档引用)

阶段 5: 完成信号
└─ yield complete 消息（含 intent_type, retrieval_rounds, total_sources）
```

## 会话记忆系统

### UnifiedMemoryManager

**文件**：`backend/domain/ai/memory/unified_memory.py`

**存储**：`.data/ai_sessions/{session_id}.jsonl`

**核心能力**：
- 全局共享历史（跨文档、跨操作类型）
- JSONL 格式存储，原子写入（先写 `.tmp` 再 rename）
- 20 轮对话后自动触发摘要滚动（取最早 6 轮生成摘要）

**JSONL 格式**：
```json
{"type": "summary", "content": "...", "covered_turns": 6, "topics": [...]}
{"type": "turn", "user_input": "...", "assistant_output": "...", "intent_type": "rag_query", ...}
```

**接口**：

| 方法 | 说明 |
|------|------|
| `get_history()` | 返回 (摘要, 近期轮次) |
| `add_turn(turn)` | 添加轮次，检查是否需要摘要 |
| `format_for_langchain()` | 转为 LangChain 消息格式 |
| `format_for_prompt()` | 转为纯文本提示词 |
| `clear()` | 清空历史 |

### SessionMetadataManager

**文件**：`backend/domain/ai/memory/session_metadata_manager.py`

**存储**：`.data/ai_sessions/sessions_metadata.json`

**元数据结构**：

| 字段 | 说明 |
|------|------|
| `session_id` | 会话标识 |
| `title` | 会话标题（LLM 生成或截取） |
| `created_at` / `updated_at` | 时间戳 |
| `turn_count` | 对话轮次数 |
| `last_intent` | 最后意图类型 |
| `referenced_documents` | 引用的文档列表 |

**接口**：

| 方法 | 说明 |
|------|------|
| `get_all_sessions()` | 获取所有会话（按 updated_at 排序） |
| `create_session()` | 创建会话 |
| `update_session()` | 更新元数据 |
| `delete_session()` | 删除会话（含 JSONL 文件） |
| `generate_title()` | 使用 LLM 生成标题 |

## API 集成

**文件**：`backend/app/api/routes/ai_routes.py`

### Agent 入口

```
POST /ai/agent
```

请求体：
```json
{
    "user_input": "用户输入",
    "session_id": "会话ID",
    "permission_mode": "assistant",
    "document_content": "文档内容（可选）",
    "document_name": "文档名（可选）",
    "top_k": 3,
    "max_rounds": 3
}
```

响应：NDJSON 流（StreamingResponse）
```
{"type": "status", "content": "正在分析意图...", "data": {"stage": "classifying"}}
{"type": "thinking", "content": "用户在询问...", "data": null}
{"type": "sources", "content": null, "data": [{"filename": "...", "content": "...", "score": 0.85}]}
{"type": "chunk", "content": "根据知识库...", "data": null}
{"type": "complete", "content": null, "data": {"intent_type": "rag_query", "retrieval_rounds": 1}}
```

### 会话管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/ai/sessions` | GET | 获取所有会话列表 |
| `/ai/sessions/{id}` | GET | 获取会话详情 |
| `/ai/sessions/{id}/history` | GET | 获取对话历史 |
| `/ai/sessions/{id}` | DELETE | 删除会话 |
| `/ai/sessions/{id}/rename` | PUT | 重命名会话 |

## 典型流程示例

### RAG 知识库问答（多轮检索）

```
用户: "关于向量数据库的选型建议"

1. load_history → 加载历史摘要和近期轮次
2. classify → intent_type="rag_query", needs_rag=true
3. analyze → key_entities=["向量数据库", "选型"], initial_query="向量数据库选型方案对比"
4. retrieve (round 1) → 检索到 3 篇文档
5. evaluate → is_sufficient=false, missing=["性能对比", "成本分析"], suggestion="retry"
6. rewrite → new_query="向量数据库性能基准测试和部署成本分析"
7. retrieve (round 2) → 检索到更多相关文档
8. evaluate → is_sufficient=true, suggestion="proceed"
9. generate_answer → 流式输出 sources + 答案文本
10. save_history → 保存轮次、元数据
11. complete → {intent_type: "rag_query", retrieval_rounds: 2, total_sources: 5}
```

### 文档编辑（需要权限）

```
用户: "修复代码缩进" (permission_mode="editor", 有文档)

1. load_history → 加载历史
2. classify → intent_type="doc_edit", needs_doc=true
3. check_doc → 文档存在，通过
4. check_permission → editor 权限满足 doc_edit 需求
5. edit_document → 流式输出编辑过程 + diff
6. save_history + complete
```

### 权限不足场景

```
用户: "帮我修改这个文件" (permission_mode="assistant", 有文档)

1. load_history → 加载历史
2. classify → intent_type="doc_edit", needs_doc=true
3. check_doc → 文档存在
4. check_permission → assistant 权限不足 (需要 editor)
5. suggest_mode → 提示用户切换到编辑模式
6. complete → {end_reason: "suggest_mode"}
```

## 文件索引

| 文件 | 说明 |
|------|------|
| `domain/ai/agent/state.py` | 状态类型定义 |
| `domain/ai/agent/graphs/unified_agent.py` | 图定义、路由、astream 入口 |
| `domain/ai/agent/nodes/history.py` | 历史加载/保存 |
| `domain/ai/agent/nodes/classify.py` | 意图分类 |
| `domain/ai/agent/nodes/check_doc.py` | 文档检查 + 提示 |
| `domain/ai/agent/nodes/analyze.py` | 问题分析 |
| `domain/ai/agent/nodes/retrieve.py` | RAG 检索执行 |
| `domain/ai/agent/nodes/evaluate.py` | 结果评估 |
| `domain/ai/agent/nodes/rewrite.py` | 查询重写 |
| `domain/ai/agent/nodes/check_permission.py` | 权限检查 + 模式建议 |
| `domain/ai/agent/nodes/direct.py` | 闲聊直接回答 |
| `domain/ai/agent/nodes/generate.py` | RAG 答案生成 |
| `domain/ai/agent/nodes/doc_advise.py` | 文档建议 |
| `domain/ai/agent/nodes/doc_edit.py` | 文档编辑 |
| `domain/ai/agent/nodes/doc_format.py` | 文档格式化 |
| `domain/ai/memory/unified_memory.py` | 统一记忆管理 |
| `domain/ai/memory/session_metadata_manager.py` | 会话元数据管理 |
