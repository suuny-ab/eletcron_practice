"""
RAG服务核心
整合索引、检索功能
"""
from pathlib import Path
from threading import Thread, Lock
import json
import time
from datetime import datetime, timezone
from langchain_community.vectorstores import Chroma
from .config import VECTOR_DB_PATH, INDEX_MARKER_PATH
from .document_processor import DocumentProcessor
from .file_watcher import FileWatcher
from ..core.model_provider import ModelProvider
from ..core import get_logger

logger = get_logger(__name__)


class RAGService:
    """RAG服务核心"""

    def __init__(self, model_provider: ModelProvider, notes_root: str, api_key: str = "", model_name: str = "text-embedding-v3", llm_model: str = "qwen-max"):
        """
        初始化RAG服务

        Args:
            model_provider: 模型提供者实例
            notes_root: 笔记根目录路径
            api_key: API密钥（DashScope）- 已废弃，保留参数用于兼容
            model_name: Embedding模型名称 - 已废弃
            llm_model: 大语言模型名称 - 已废弃
        """
        self._model_provider = model_provider
        self.notes_root = Path(notes_root)

        # 初始化文档处理器
        self.document_processor = DocumentProcessor()

        # 初始化向量数据库（使用注入的模型实例）
        self.vectorstore = Chroma(
            persist_directory=str(VECTOR_DB_PATH),
            embedding_function=self._model_provider.embedding_model,
            collection_name="knowledge_base"
        )

        # 初始化文件监听器
        self.file_watcher = FileWatcher(self._on_file_changed)
        self._is_watcher_started = False

        # 索引线程控制
        self._indexing_lock = Lock()
        self._is_indexing = False
        self._indexing_thread: Thread | None = None

    def start_indexing(self):
        """后台启动全量索引，避免阻塞启动"""
        if not self.notes_root.exists():
            logger.warning("[RAG] 笔记根目录不存在，跳过索引")
            return

        if self._should_skip_full_index():
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
                self._write_index_marker(file_count=0, chunk_count=0)
                return

            logger.info(f"[RAG] 开始全量索引，共 {len(md_files)} 个文件...")

            # 切分并添加文档
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

            if documents:
                texts = [doc["content"] for doc in documents]
                metadatas = [doc["metadata"] for doc in documents]
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
                logger.info(f"[RAG] 全量索引完成，共添加 {len(texts)} 个文档块")
                self._write_index_marker(file_count=len(md_files), chunk_count=len(texts))
            else:
                logger.info("[RAG] 没有文档需要索引")
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
        检索相关文档来源

        Args:
            question: 问题
            top_k: 返回的最相关文档数量

        Returns:
            来源列表（去重后的文件级别）
        """
        if not self.vectorstore:
            raise ValueError("向量数据库未初始化")

        results = self.vectorstore.similarity_search_with_score(
            query=question,
            k=top_k
        )

        sources = []
        seen_files = set()
        for doc, score in results:
            filename = doc.metadata.get("filename", "")
            if filename not in seen_files:
                seen_files.add(filename)
                sources.append({
                    "filename": filename,
                    "content": doc.page_content,
                    "score": float(score)
                })
                if len(sources) >= top_k:
                    break

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
