"""
索引服务
负责全量索引、增量索引、文件监听和停止信号处理
"""
import json
import time
from pathlib import Path
from threading import Thread, Lock, Event
from datetime import datetime, timezone
from langchain_community.vectorstores import Chroma
from .bm25_index import BM25Index
from .config import VECTOR_DB_PATH, INDEX_MARKER_PATH
from infrastructure.storage.document_processor import DocumentProcessor
from infrastructure.storage.file_watcher import FileWatcher
from infrastructure.logging.logger import get_logger, LogContext
from infrastructure.metrics import get_metrics

logger = get_logger(__name__)


class IndexService:
    """索引服务"""

    def __init__(
        self,
        vectorstore: Chroma,
        bm25_index: BM25Index,
        notes_root: Path,
        document_processor: DocumentProcessor,
    ):
        """
        初始化索引服务

        Args:
            vectorstore: 向量数据库实例
            bm25_index: BM25索引实例
            notes_root: 笔记根目录
            document_processor: 文档处理器实例
        """
        self._vectorstore = vectorstore
        self._bm25_index = bm25_index
        self._notes_root = notes_root
        self._document_processor = document_processor

        # 文件监听
        self._file_watcher = FileWatcher(self._on_file_changed)
        self._is_watcher_started = False

        # 索引线程控制
        self._indexing_lock = Lock()
        self._is_indexing = False
        self._indexing_thread: Thread | None = None
        self._stop_event = Event()

    def _collect_documents_from_files(self, md_files: list[Path]) -> list[dict]:
        """从文件列表中构建文档块集合"""
        documents = []
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                filename = md_file.relative_to(self._notes_root).as_posix()
                chunks = self._document_processor.split_documents(filename, content)
                documents.extend(chunks)
            except Exception as e:
                logger.warning(f"[RAG] 读取文件失败 {md_file}: {e}")
                continue
        return documents

    def _add_texts_in_batches(
        self,
        texts: list[str],
        metadatas: list[dict],
        batch_size: int = 20
    ) -> int:
        """
        分批添加文档到向量库，支持停止信号中断

        Returns:
            已成功添加的文档数
        """
        total = len(texts)
        added = 0

        for i in range(0, total, batch_size):
            if self._stop_event.is_set():
                logger.info(f"[RAG] 收到停止信号，已添加 {added}/{total} 个文档")
                return added

            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            try:
                self._vectorstore.add_texts(texts=batch_texts, metadatas=batch_metadatas)
                added += len(batch_texts)
            except Exception as e:
                logger.warning(f"[RAG] 批量添加文档失败 [{i}:{i + batch_size}]: {e}")
                # 单个文档重试
                for j, (text, meta) in enumerate(zip(batch_texts, batch_metadatas)):
                    try:
                        self._vectorstore.add_texts(texts=[text], metadatas=[meta])
                        added += 1
                    except Exception as e2:
                        logger.warning(f"[RAG] 单个文档添加失败: {e2}")

        return added

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
                "notes_root": str(self._notes_root),
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
        """判断是否应跳过全量索引（标记文件存在 + 向量库数据有效）"""
        marker = self._load_index_marker()
        if not marker:
            return False

        # 验证向量库中实际数据量
        try:
            collection = self._vectorstore._collection
            actual_count = collection.count()
            expected_count = marker.get("chunk_count", 0)

            if actual_count == 0 and expected_count > 0:
                logger.info("[RAG] 向量库数据丢失，重新索引")
                self._remove_index_marker()
                return False

            if actual_count != expected_count:
                logger.warning(f"[RAG] 向量库数据量不一致 (期望:{expected_count}, 实际:{actual_count})，重新索引")
                self._remove_index_marker()
                return False
        except Exception as e:
            logger.warning(f"[RAG] 验证向量库失败: {e}，重新索引")
            self._remove_index_marker()
            return False

        logger.info("[RAG] 已存在索引标记，跳过全量索引")
        return True

    def _rebuild_bm25_from_files(self):
        """从当前笔记文件重建BM25索引"""
        if not self._notes_root.exists():
            self._bm25_index.build([])
            return
        md_files = list(self._notes_root.rglob("*.md"))
        md_files.extend(list(self._notes_root.rglob("*.markdown")))
        documents = self._collect_documents_from_files(md_files)
        self._bm25_index.build(documents)

    def start_indexing(self) -> None:
        """后台启动全量索引"""
        if not self._notes_root.exists():
            logger.warning("[RAG] 笔记根目录不存在，跳过索引")
            return

        with self._indexing_lock:
            if self._indexing_thread and self._indexing_thread.is_alive():
                logger.info("[RAG] 全量索引已在运行，跳过重复启动")
                return

            self._stop_event.clear()
            self._indexing_thread = Thread(
                target=self._full_index,
                name="rag-full-index",
                daemon=True
            )
            self._indexing_thread.start()

    def stop_indexing(self, timeout: float = 30.0) -> bool:
        """
        停止索引线程并等待完成

        Returns:
            True 表示线程已停止，False 表示超时
        """
        if not self._indexing_thread or not self._indexing_thread.is_alive():
            return True

        logger.info("[RAG] 正在停止索引线程...")
        self._stop_event.set()

        self._indexing_thread.join(timeout=timeout)
        stopped = not self._indexing_thread.is_alive()

        if stopped:
            logger.info("[RAG] 索引线程已停止")
        else:
            logger.warning("[RAG] 索引线程停止超时")

        return stopped

    def _full_index(self):
        """全量索引：索引所有Markdown文件"""
        metrics = get_metrics()

        with self._indexing_lock:
            if self._is_indexing:
                return
            self._is_indexing = True

        start_time = None
        file_count = 0
        chunk_count = 0
        try:
            if self._stop_event.is_set():
                logger.info("[RAG] 收到停止信号，跳过索引")
                return

            if self._should_skip_full_index():
                self._rebuild_bm25_from_files()
                return

            if not self._notes_root.exists():
                logger.warning("[RAG] 笔记根目录不存在，跳过索引")
                return

            start_time = time.monotonic()

            # 查找所有Markdown文件
            md_files = list(self._notes_root.rglob("*.md"))
            md_files.extend(list(self._notes_root.rglob("*.markdown")))
            file_count = len(md_files)

            if not md_files:
                logger.info("[RAG] 未找到 Markdown 文件")
                self._bm25_index.build([])
                self._write_index_marker(file_count=0, chunk_count=0)
                return

            logger.info(f"[RAG] 开始全量索引，共 {file_count} 个文件...")

            if self._stop_event.is_set():
                logger.info("[RAG] 收到停止信号，中断索引")
                return

            # 清理向量库中的旧数据，避免数据累积
            try:
                self._vectorstore._collection.delete()
                logger.info("[RAG] 已清理向量库旧数据")
            except Exception as e:
                logger.warning(f"[RAG] 清理向量库失败: {e}，继续索引")

            # 切分并添加文档
            documents = self._collect_documents_from_files(md_files)

            if self._stop_event.is_set():
                logger.info("[RAG] 收到停止信号，中断索引")
                return

            if documents:
                texts = [doc["content"] for doc in documents]
                metadatas = [doc["metadata"] for doc in documents]

                added_count = self._add_texts_in_batches(texts, metadatas)
                chunk_count = added_count

                if self._stop_event.is_set():
                    logger.info("[RAG] 收到停止信号，跳过BM25索引和标记写入")
                    return

                self._bm25_index.build(documents)
                logger.info(f"[RAG] 全量索引完成，共添加 {added_count} 个文档块")
                self._write_index_marker(file_count=len(md_files), chunk_count=added_count)
            else:
                logger.info("[RAG] 没有文档需要索引")
                self._bm25_index.build([])
                self._write_index_marker(file_count=len(md_files), chunk_count=0)
        except Exception as e:
            logger.exception(f"[RAG] 全量索引失败: {e}")
        finally:
            if start_time is not None:
                elapsed = time.monotonic() - start_time
                # 记录指标
                metrics.observe("rag.index.duration_seconds", elapsed)
                metrics.increment("rag.index.files_indexed", file_count)
                metrics.increment("rag.index.chunks_created", chunk_count)

                # 结构化日志
                logger.info(
                    "全量索引完成",
                    extra={"context": LogContext(
                        operation="rag.index.full",
                        duration_ms=elapsed * 1000,
                        extra={"files": file_count, "chunks": chunk_count}
                    )}
                )
            with self._indexing_lock:
                self._is_indexing = False

    def _on_file_changed(self, file_path: str, event_type: str):
        """文件变化回调"""
        try:
            relative_path = Path(file_path).relative_to(self._notes_root).as_posix()
            logger.info(f"[RAG] 检测到文件变化: {relative_path} (事件: {event_type})")

            if event_type == "deleted":
                self._remove_file_documents(relative_path)
            else:
                self._index_single_file(file_path, relative_path)
        except Exception as e:
            logger.error(f"[RAG] 文件变化处理失败: {e}")

    def _index_single_file(self, file_path: str, relative_path: str):
        """索引单个文件"""
        try:
            self._remove_file_documents(relative_path)

            content = Path(file_path).read_text(encoding="utf-8")
            chunks = self._document_processor.split_documents(relative_path, content)

            if chunks:
                texts = [doc["content"] for doc in chunks]
                metadatas = [doc["metadata"] for doc in chunks]
                self._vectorstore.add_texts(texts=texts, metadatas=metadatas)
                logger.info(f"[RAG] 文件索引完成: {relative_path} (添加 {len(texts)} 个文档块)")
            else:
                logger.warning(f"[RAG] 文件无内容可索引: {relative_path}")

            self._bm25_index.update_file(relative_path, chunks)
        except Exception as e:
            logger.error(f"[RAG] 文件索引失败 {relative_path}: {e}")

    def _remove_file_documents(self, filename: str):
        """从向量数据库中移除指定文件的所有文档"""
        try:
            self._vectorstore.delete(where={"filename": filename})
            self._bm25_index.update_file(filename, [])
            logger.info(f"[RAG] 文档已移除: {filename}")
        except Exception as e:
            logger.error(f"[RAG] 移除文档失败 {filename}: {e}")

    def get_status(self) -> dict:
        """获取索引状态"""
        marker = self._load_index_marker()
        return {
            "notes_root": str(self._notes_root),
            "is_indexing": self._is_indexing,
            "marker": marker
        }

    def start_watcher(self) -> None:
        """启动文件监听器"""
        if not self._is_watcher_started and self._notes_root.exists():
            self._file_watcher.start(str(self._notes_root))
            self._is_watcher_started = True

    def stop_watcher(self) -> None:
        """停止文件监听器"""
        if self._is_watcher_started:
            self._file_watcher.stop()
            self._is_watcher_started = False
