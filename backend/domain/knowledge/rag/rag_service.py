"""
RAG服务核心
整合索引、检索功能
"""
from pathlib import Path
from threading import Thread, Lock
import json
import time
import math
import re
from datetime import datetime, timezone
from langchain_community.vectorstores import Chroma
from rank_bm25 import BM25Okapi
from .config import (
    VECTOR_DB_PATH,
    INDEX_MARKER_PATH,
    VECTOR_TOP_K,
    BM25_TOP_K,
    HYBRID_TOP_K,
    VECTOR_WEIGHT,
    BM25_WEIGHT,
)
from ....infrastructure.storage.document_processor import DocumentProcessor
from ....infrastructure.storage.file_watcher import FileWatcher
from ...ai.models.model_provider import ModelProvider
from ...ai.services.llm_task_service import LLMTaskService
from ....infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


class RAGService:
    """RAG服务核心"""

    def __init__(
        self,
        model_provider: ModelProvider,
        notes_root: str,
        llm_task_service: LLMTaskService,
        api_key: str = "",
        model_name: str = "text-embedding-v3",
        llm_model: str = "qwen-max"
    ):
        """
        初始化RAG服务

        Args:
            model_provider: 模型提供者实例
            notes_root: 笔记根目录路径
            llm_task_service: 统一LLM任务服务实例
            api_key: API密钥（DashScope）- 已废弃，保留参数用于兼容
            model_name: Embedding模型名称 - 已废弃
            llm_model: 大语言模型名称 - 已废弃
        """
        self._model_provider = model_provider
        self._llm_task_service = llm_task_service
        self.notes_root = Path(notes_root)

        # 初始化文档处理器
        self.document_processor = DocumentProcessor()

        # 初始化向量数据库（使用注入的模型实例）
        self.vectorstore = Chroma(
            persist_directory=str(VECTOR_DB_PATH),
            embedding_function=self._model_provider.embedding_model,
            collection_name="knowledge_base"
        )

        # 初始化BM25索引（内存）
        self._bm25_lock = Lock()
        self._bm25_index: BM25Okapi | None = None
        self._bm25_texts: list[str] = []
        self._bm25_metadatas: list[dict] = []

        # 初始化文件监听器
        self.file_watcher = FileWatcher(self._on_file_changed)
        self._is_watcher_started = False

        # 索引线程控制
        self._indexing_lock = Lock()
        self._is_indexing = False
        self._indexing_thread: Thread | None = None

    def _tokenize(self, text: str) -> list[str]:
        """将文本拆分为BM25可用的tokens（中英文混合）。"""
        if not text:
            return []
        parts = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text.lower())
        tokens: list[str] = []
        for part in parts:
            if re.match(r"[\u4e00-\u9fff]+", part):
                tokens.extend(list(part))
            else:
                tokens.append(part)
        return tokens

    def _collect_documents_from_files(self, md_files: list[Path]) -> list[dict]:
        """从文件列表中构建文档块集合。"""
        documents = []
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                filename = md_file.relative_to(self.notes_root).as_posix()
                chunks = self.document_processor.split_documents(filename, content)
                documents.extend(chunks)
            except Exception as e:
                logger.warning(f"[RAG] 读取文件失败 {md_file}: {e}")
                continue
        return documents

    def _build_bm25_index(self, documents: list[dict]):
        """基于文档块构建BM25索引。"""
        with self._bm25_lock:
            self._bm25_texts = [doc["content"] for doc in documents]
            self._bm25_metadatas = [doc["metadata"] for doc in documents]
            tokenized = [self._tokenize(text) for text in self._bm25_texts]
            self._bm25_index = BM25Okapi(tokenized) if tokenized else None

    def _rebuild_bm25_from_files(self):
        """从当前笔记文件重建BM25索引（不触发向量重建）。"""
        if not self.notes_root.exists():
            self._build_bm25_index([])
            return
        md_files = list(self.notes_root.rglob("*.md"))
        md_files.extend(list(self.notes_root.rglob("*.markdown")))
        documents = self._collect_documents_from_files(md_files)
        self._build_bm25_index(documents)

    def _update_bm25_for_file(self, filename: str, chunks: list[dict]):
        """更新指定文件在BM25中的条目，并重建索引。"""
        with self._bm25_lock:
            kept_texts: list[str] = []
            kept_metadatas: list[dict] = []
            for text, metadata in zip(self._bm25_texts, self._bm25_metadatas):
                if metadata.get("filename") != filename:
                    kept_texts.append(text)
                    kept_metadatas.append(metadata)

            for doc in chunks:
                kept_texts.append(doc["content"])
                kept_metadatas.append(doc["metadata"])

            self._bm25_texts = kept_texts
            self._bm25_metadatas = kept_metadatas
            tokenized = [self._tokenize(text) for text in self._bm25_texts]
            self._bm25_index = BM25Okapi(tokenized) if tokenized else None

    def _bm25_search(self, query: str, top_k: int) -> list[tuple[str, dict, float]]:
        """执行BM25检索，返回(content, metadata, score)。"""
        if not self._bm25_index or not self._bm25_texts:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self._bm25_index.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            results.append((self._bm25_texts[idx], self._bm25_metadatas[idx], score))
        return results

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """将分数归一化到0-1区间。"""
        if not scores:
            return []
        min_score = min(scores)
        max_score = max(scores)
        if math.isclose(max_score, min_score):
            return [1.0 for _ in scores]
        return [(score - min_score) / (max_score - min_score) for score in scores]

    def _llm_rerank(self, question: str, candidates: list[dict], top_k: int) -> list[int]:
        """使用LLM对候选进行重排序，返回候选索引列表。"""
        if not candidates or top_k <= 0:
            return []
        snippets = []
        for idx, cand in enumerate(candidates):
            snippet = cand["content"].replace("\n", " ").strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            snippets.append(f"{idx}. {snippet}")

        candidates_text = "\n".join(snippets)
        indices = self._llm_task_service.invoke(
            task_type="rerank",
            question=question,
            top_k=top_k,
            candidates=candidates_text
        )

        if not isinstance(indices, list):
            raise ValueError("rerank 返回结果不是JSON数组")

        seen = set()
        filtered = []
        for idx in indices:
            if not isinstance(idx, int):
                raise ValueError("rerank 返回包含非整数索引")
            if 0 <= idx < len(candidates) and idx not in seen:
                seen.add(idx)
                filtered.append(idx)
            if len(filtered) >= top_k:
                break
        return filtered

    def start_indexing(self):
        """后台启动全量索引，避免阻塞启动"""
        if not self.notes_root.exists():
            logger.warning("[RAG] 笔记根目录不存在，跳过索引")
            return

        with self._indexing_lock:
            if self._indexing_thread and self._indexing_thread.is_alive():
                logger.info("[RAG] 全量索引已在运行，跳过重复启动")
                return

            self._indexing_thread = Thread(
                target=self._full_index,
                name="rag-full-index",
                daemon=True
            )
            self._indexing_thread.start()

    def _load_index_marker(self) -> dict | None:
        """读取索引标记文件"""
        if not INDEX_MARKER_PATH.exists():
            return None

        try:
            content = INDEX_MARKER_PATH.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            logger.warning(f"[RAG] 读取索引标记失败: {e}")
            return None

    def _write_index_marker(self, file_count: int, chunk_count: int):
        """写入索引标记文件"""
        try:
            INDEX_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "notes_root": str(self.notes_root),
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "file_count": file_count,
                "chunk_count": chunk_count
            }
            INDEX_MARKER_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"[RAG] 写入索引标记失败: {e}")

    def _remove_index_marker(self):
        """删除索引标记文件"""
        try:
            if INDEX_MARKER_PATH.exists():
                INDEX_MARKER_PATH.unlink()
        except Exception as e:
            logger.warning(f"[RAG] 删除索引标记失败: {e}")

    def _should_skip_full_index(self) -> bool:
        """判断是否应跳过全量索引"""
        marker = self._load_index_marker()
        if not marker:
            return False

        if marker.get("notes_root") != str(self.notes_root):
            logger.info("[RAG] 索引标记与当前笔记目录不一致，重新索引")
            self._remove_index_marker()
            return False

        logger.info("[RAG] 已存在索引标记，跳过全量索引")
        return True

    def _full_index(self):
        """全量索引：索引所有Markdown文件"""
        with self._indexing_lock:
            if self._is_indexing:
                return
            self._is_indexing = True

        start_time = None
        try:
            if self._should_skip_full_index():
                self._rebuild_bm25_from_files()
                return

            if not self.notes_root.exists():
                logger.warning("[RAG] 笔记根目录不存在，跳过索引")
                return

            start_time = time.monotonic()

            # 向量数据库已在 __init__ 中创建

            # 查找所有Markdown文件
            md_files = list(self.notes_root.rglob("*.md"))
            md_files.extend(list(self.notes_root.rglob("*.markdown")))

            if not md_files:
                logger.info("[RAG] 未找到 Markdown 文件")
                self._build_bm25_index([])
                self._write_index_marker(file_count=0, chunk_count=0)
                return

            logger.info(f"[RAG] 开始全量索引，共 {len(md_files)} 个文件...")

            # 切分并添加文档
            documents = self._collect_documents_from_files(md_files)

            if documents:
                texts = [doc["content"] for doc in documents]
                metadatas = [doc["metadata"] for doc in documents]
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
                self._build_bm25_index(documents)
                logger.info(f"[RAG] 全量索引完成，共添加 {len(texts)} 个文档块")
                self._write_index_marker(file_count=len(md_files), chunk_count=len(texts))
            else:
                logger.info("[RAG] 没有文档需要索引")
                self._build_bm25_index([])
                self._write_index_marker(file_count=len(md_files), chunk_count=0)
        except Exception as e:
            logger.exception(f"[RAG] 全量索引失败: {e}")
        finally:
            if start_time is not None:
                elapsed = time.monotonic() - start_time
                logger.info(f"[RAG] 全量索引耗时 {elapsed:.2f} 秒")
            with self._indexing_lock:
                self._is_indexing = False

    def _on_file_changed(self, file_path: str, event_type: str):
        """
        文件变化回调

        Args:
            file_path: 文件路径
            event_type: 事件类型（created/modified/deleted）
        """
        try:
            relative_path = Path(file_path).relative_to(self.notes_root).as_posix()
            logger.info(f"[RAG] 检测到文件变化: {relative_path} (事件: {event_type})")

            if event_type == "deleted":
                # 删除：移除该文件的所有文档块
                self._remove_file_documents(relative_path)
            else:
                # 创建或修改：重新索引该文件
                self._index_single_file(file_path, relative_path)
        except Exception as e:
            logger.error(f"[RAG] 文件变化处理失败: {e}")

    def _index_single_file(self, file_path: str, relative_path: str):
        """
        索引单个文件

        Args:
            file_path: 文件绝对路径
            relative_path: 文件相对路径
        """
        try:
            # 先删除该文件的旧文档
            self._remove_file_documents(relative_path)

            # 读取并切分文档
            content = Path(file_path).read_text(encoding="utf-8")
            chunks = self.document_processor.split_documents(relative_path, content)

            # 添加到向量数据库
            if chunks:
                texts = [doc["content"] for doc in chunks]
                metadatas = [doc["metadata"] for doc in chunks]
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
                logger.info(f"[RAG] 文件索引完成: {relative_path} (添加 {len(texts)} 个文档块)")
            else:
                logger.warning(f"[RAG] 文件无内容可索引: {relative_path}")

            # 更新BM25索引
            self._update_bm25_for_file(relative_path, chunks)
        except Exception as e:
            logger.error(f"[RAG] 文件索引失败 {relative_path}: {e}")

    def _remove_file_documents(self, filename: str):
        """
        从向量数据库中移除指定文件的所有文档

        Args:
            filename: 文件名（相对路径）
        """
        try:
            # ChromaDB删除文档需要根据ID或条件
            # 这里通过metadata filter获取并删除
            self.vectorstore.delete(where={"filename": filename})
            self._update_bm25_for_file(filename, [])
            logger.info(f"[RAG] 文档已移除: {filename}")
        except Exception as e:
            logger.error(f"[RAG] 移除文档失败 {filename}: {e}")

    def get_index_status(self) -> dict:
        """获取索引状态"""
        marker = self._load_index_marker()
        return {
            "notes_root": str(self.notes_root),
            "is_indexing": self._is_indexing,
            "marker": marker
        }

    def start_watcher(self):
        """启动文件监听器"""
        if not self._is_watcher_started and self.notes_root.exists():
            self.file_watcher.start(str(self.notes_root))
            self._is_watcher_started = True

    def stop_watcher(self):
        """停止文件监听器"""
        if self._is_watcher_started:
            self.file_watcher.stop()
            self._is_watcher_started = False

    def retrieve_sources(self, question: str, top_k: int = 3) -> list[dict]:
        """
        检索相关文档来源（chunk级输出）

        Args:
            question: 问题
            top_k: 返回的最相关文档数量

        Returns:
            来源列表（chunk级别）
        """
        if not self.vectorstore:
            raise ValueError("向量数据库未初始化")

        if self._bm25_index is None:
            self._rebuild_bm25_from_files()

        vector_results = self.vectorstore.similarity_search_with_score(
            query=question,
            k=VECTOR_TOP_K
        )
        bm25_results = self._bm25_search(question, BM25_TOP_K)

        if not vector_results and not bm25_results:
            return []

        candidates: dict[str, dict] = {}

        vector_sims: list[float] = []
        vector_docs: list[tuple] = []
        for doc, score in vector_results:
            raw_score = float(score)
            sim_score = 1.0 / (1.0 + raw_score)
            vector_sims.append(sim_score)
            vector_docs.append((doc, raw_score))

        vector_norms = self._normalize_scores(vector_sims)
        for idx, (doc, raw_score) in enumerate(vector_docs):
            metadata = doc.metadata or {}
            key = metadata.get("chunk_id") or f"{metadata.get('filename', '')}::{doc.page_content}"
            if key not in candidates:
                candidates[key] = {
                    "filename": metadata.get("filename", ""),
                    "content": doc.page_content,
                    "metadata": metadata,
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                }
            candidates[key]["vector_score"] = vector_norms[idx]
            candidates[key]["raw_vector_score"] = raw_score

        bm25_scores = [score for _, _, score in bm25_results]
        bm25_norms = self._normalize_scores(bm25_scores)
        for idx, (content, metadata, score) in enumerate(bm25_results):
            key = metadata.get("chunk_id") or f"{metadata.get('filename', '')}::{content}"
            if key not in candidates:
                candidates[key] = {
                    "filename": metadata.get("filename", ""),
                    "content": content,
                    "metadata": metadata,
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                }
            candidates[key]["bm25_score"] = bm25_norms[idx]
            candidates[key]["raw_bm25_score"] = float(score)

        merged = []
        for cand in candidates.values():
            hybrid_score = VECTOR_WEIGHT * cand["vector_score"] + BM25_WEIGHT * cand["bm25_score"]
            cand["hybrid_score"] = hybrid_score
            merged.append(cand)

        merged.sort(key=lambda item: item["hybrid_score"], reverse=True)
        if HYBRID_TOP_K > 0:
            merged = merged[:min(HYBRID_TOP_K, len(merged))]

        rerank_indices = self._llm_rerank(question, merged, min(top_k, len(merged)))
        if rerank_indices:
            selected = [merged[i] for i in rerank_indices]
        else:
            selected = merged[:top_k]

        sources = []
        for item in selected:
            sources.append({
                "filename": item["filename"],
                "content": item["content"],
                "score": float(item.get("hybrid_score", 0.0))
            })

        return sources

    def build_context(self, sources: list[dict]) -> str:
        """根据检索来源构建上下文"""
        context_parts = []
        for i, source in enumerate(sources, 1):
            context_parts.append(
                f"\n参考资料 {i}（来自 {source['filename']}）：\n{source['content']}\n"
            )
        return "\n".join(context_parts)

    def retrieve_context(self, question: str, top_k: int = 3) -> tuple[str, list[dict]]:
        """
        检索上下文

        Returns:
            (context, sources)
        """
        sources = self.retrieve_sources(question=question, top_k=top_k)
        context = self.build_context(sources)
        return context, sources
