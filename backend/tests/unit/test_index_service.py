"""
索引服务单元测试
测试全量索引、增量索引、停止信号和文件监听
"""
import json
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from domain.knowledge.rag.index_service import IndexService
from domain.knowledge.rag.bm25_index import BM25Index


class MockVectorStore:
    """Mock 向量数据库"""

    def __init__(self):
        self.texts = []
        self.metadatas = []
        self.add_texts_calls = []
        self.delete_calls = []
        self._collection = Mock()
        self._collection.count = Mock(return_value=0)

    def add_texts(self, texts, metadatas):
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)
        self.add_texts_calls.append({"texts": texts, "metadatas": metadatas})

    def delete(self, where):
        self.delete_calls.append(where)
        # 模拟删除
        self.texts = [t for t, m in zip(self.texts, self.metadatas) if m.get("filename") != where.get("filename")]
        self.metadatas = [m for m in self.metadatas if m.get("filename") != where.get("filename")]


class MockDocumentProcessor:
    """Mock 文档处理器"""

    def __init__(self, chunks_per_file=2):
        self.chunks_per_file = chunks_per_file
        self.split_calls = []

    def split_documents(self, filename, content):
        self.split_calls.append({"filename": filename, "content": content})
        return [
            {
                "content": f"chunk_{i}_{filename}",
                "metadata": {"filename": filename, "chunk_id": f"{filename}_chunk_{i}"}
            }
            for i in range(self.chunks_per_file)
        ]


class TestIndexServiceInit:
    """测试索引服务初始化"""

    def test_init_with_valid_params(self):
        """测试正常初始化"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        notes_root = Path(tempfile.mkdtemp())
        mock_processor = MockDocumentProcessor()

        service = IndexService(
            vectorstore=mock_vectorstore,
            bm25_index=mock_bm25,
            notes_root=notes_root,
            document_processor=mock_processor
        )

        assert service._vectorstore == mock_vectorstore
        assert service._bm25_index == mock_bm25
        assert service._notes_root == notes_root
        assert service._is_indexing is False


class TestCollectDocuments:
    """测试文档收集"""

    def test_collect_from_valid_files(self):
        """测试从有效文件收集文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)

            # 创建测试文件
            (notes_root / "test1.md").write_text("# 测试1\n内容1", encoding="utf-8")
            (notes_root / "test2.md").write_text("# 测试2\n内容2", encoding="utf-8")

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            md_files = list(notes_root.glob("*.md"))
            documents = service._collect_documents_from_files(md_files)

            assert len(documents) == 4  # 2 files * 2 chunks each
            assert len(mock_processor.split_calls) == 2

    def test_collect_handles_read_errors(self):
        """测试处理读取错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            # 传入不存在的文件
            non_existent = [Path(tmpdir) / "non_existent.md"]
            documents = service._collect_documents_from_files(non_existent)

            # 应该返回空列表而不是抛出异常
            assert documents == []


class TestAddTextsInBatches:
    """测试批量添加文档"""

    def test_add_texts_normal(self):
        """测试正常批量添加"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=Path(tmpdir),
                document_processor=mock_processor
            )

            texts = [f"text_{i}" for i in range(50)]
            metadatas = [{"index": i} for i in range(50)]

            added = service._add_texts_in_batches(texts, metadatas, batch_size=20)

            assert added == 50
            assert len(mock_vectorstore.texts) == 50

    def test_add_texts_respects_stop_signal(self):
        """测试停止信号中断"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=Path(tmpdir),
                document_processor=mock_processor
            )

            # 设置停止信号
            service._stop_event.set()

            texts = [f"text_{i}" for i in range(100)]
            metadatas = [{"index": i} for i in range(100)]

            added = service._add_texts_in_batches(texts, metadatas, batch_size=20)

            # 应该在第一个批次之前就停止
            assert added == 0

    def test_add_texts_handles_batch_error(self):
        """测试批量添加失败时逐个重试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=Path(tmpdir),
                document_processor=mock_processor
            )

            call_count = [0]
            original_add_texts = mock_vectorstore.add_texts

            def failing_add_texts(texts, metadatas):
                call_count[0] += 1
                if call_count[0] == 1 and len(texts) > 1:
                    raise Exception("Batch error")
                original_add_texts(texts, metadatas)

            mock_vectorstore.add_texts = failing_add_texts

            texts = ["text_0", "text_1"]
            metadatas = [{"index": 0}, {"index": 1}]

            added = service._add_texts_in_batches(texts, metadatas, batch_size=2)

            # 批量失败后应该逐个添加
            assert added == 2


class TestIndexMarker:
    """测试索引标记文件"""

    def test_write_and_load_marker(self):
        """测试写入和读取标记文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            marker_path = notes_root / "test_marker.json"

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            # 使用 patch 临时修改标记路径
            with patch("domain.knowledge.rag.index_service.INDEX_MARKER_PATH", marker_path):
                service._write_index_marker(file_count=10, chunk_count=50)

                marker = service._load_index_marker()

                assert marker is not None
                assert marker["file_count"] == 10
                assert marker["chunk_count"] == 50
                assert marker["notes_root"] == str(notes_root)
                assert "indexed_at" in marker

    def test_load_marker_not_exists(self):
        """测试标记文件不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            marker_path = notes_root / "non_existent_marker.json"

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            with patch("domain.knowledge.rag.index_service.INDEX_MARKER_PATH", marker_path):
                marker = service._load_index_marker()
                assert marker is None

    def test_remove_marker(self):
        """测试删除标记文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            marker_path = notes_root / "test_marker.json"
            marker_path.write_text("{}", encoding="utf-8")

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            with patch("domain.knowledge.rag.index_service.INDEX_MARKER_PATH", marker_path):
                service._remove_index_marker()
                assert not marker_path.exists()


class TestShouldSkipFullIndex:
    """测试跳过全量索引判断"""

    def test_skip_when_marker_matches(self):
        """测试标记匹配时跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            marker_path = notes_root / "marker.json"

            mock_vectorstore = MockVectorStore()
            mock_vectorstore._collection.count = Mock(return_value=50)
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            # 写入匹配的标记
            marker_data = {
                "notes_root": str(notes_root),
                "chunk_count": 50,
                "file_count": 10
            }
            marker_path.write_text(json.dumps(marker_data), encoding="utf-8")

            with patch("domain.knowledge.rag.index_service.INDEX_MARKER_PATH", marker_path):
                should_skip = service._should_skip_full_index()
                assert should_skip is True

    def test_no_skip_when_no_marker(self):
        """测试无标记时不跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            marker_path = notes_root / "non_existent.json"

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            with patch("domain.knowledge.rag.index_service.INDEX_MARKER_PATH", marker_path):
                should_skip = service._should_skip_full_index()
                assert should_skip is False

    def test_no_skip_when_count_mismatch(self):
        """测试向量库数据量不匹配时不跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            marker_path = notes_root / "marker.json"

            mock_vectorstore = MockVectorStore()
            mock_vectorstore._collection.count = Mock(return_value=30)
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            # 标记中 chunk_count 与向量库实际数量不一致
            marker_data = {
                "notes_root": str(notes_root),
                "chunk_count": 50
            }
            marker_path.write_text(json.dumps(marker_data), encoding="utf-8")

            with patch("domain.knowledge.rag.index_service.INDEX_MARKER_PATH", marker_path):
                should_skip = service._should_skip_full_index()
                assert should_skip is False


class TestStartStopIndexing:
    """测试启动和停止索引"""

    def test_start_indexing_creates_thread(self):
        """测试启动索引创建线程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            (notes_root / "test.md").write_text("# Test", encoding="utf-8")

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            service.start_indexing()

            assert service._indexing_thread is not None
            assert service._indexing_thread.is_alive()

            # 等待完成
            service._indexing_thread.join(timeout=5)

    def test_start_indexing_skips_if_already_running(self):
        """测试已有索引线程时跳过启动"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            (notes_root / "test.md").write_text("# Test", encoding="utf-8")

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            # 启动第一个线程
            service.start_indexing()
            first_thread = service._indexing_thread

            # 尝试再次启动
            service.start_indexing()

            # 应该还是同一个线程
            assert service._indexing_thread == first_thread

            service._indexing_thread.join(timeout=5)

    def test_stop_indexing(self):
        """测试停止索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            # 创建多个文件以延长索引时间
            for i in range(10):
                (notes_root / f"test{i}.md").write_text(f"# Test {i}\n" * 100, encoding="utf-8")

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            service.start_indexing()
            time.sleep(0.1)  # 让索引开始

            stopped = service.stop_indexing(timeout=5)

            # 应该成功停止（无论是正常完成还是被中断）
            assert stopped is True

    def test_start_indexing_nonexistent_root(self):
        """测试笔记目录不存在时跳过"""
        notes_root = Path("/non/existent/path")

        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_processor = MockDocumentProcessor()

        service = IndexService(
            vectorstore=mock_vectorstore,
            bm25_index=mock_bm25,
            notes_root=notes_root,
            document_processor=mock_processor
        )

        service.start_indexing()

        # 不应该启动线程
        assert service._indexing_thread is None or not service._indexing_thread.is_alive()


class TestSingleFileIndex:
    """测试单文件索引"""

    def test_index_single_file(self):
        """测试索引单个文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)
            test_file = notes_root / "test.md"
            test_file.write_text("# 测试\n内容", encoding="utf-8")

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_bm25.build([])
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            service._index_single_file(str(test_file), "test.md")

            # 应该先删除旧文档，再添加新文档
            assert len(mock_vectorstore.delete_calls) == 1
            assert len(mock_vectorstore.add_texts_calls) == 1

    def test_remove_file_documents(self):
        """测试移除文件文档"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)

            mock_vectorstore = MockVectorStore()
            mock_vectorstore.texts = ["content1", "content2"]
            mock_vectorstore.metadatas = [
                {"filename": "test.md"},
                {"filename": "other.md"}
            ]
            mock_bm25 = BM25Index()
            mock_bm25.build([
                {"content": "content1", "metadata": {"filename": "test.md"}},
                {"content": "content2", "metadata": {"filename": "other.md"}}
            ])
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            service._remove_file_documents("test.md")

            assert len(mock_vectorstore.delete_calls) == 1
            assert mock_vectorstore.delete_calls[0] == {"filename": "test.md"}


class TestGetStatus:
    """测试获取索引状态"""

    def test_get_status(self):
        """测试获取状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_root = Path(tmpdir)

            mock_vectorstore = MockVectorStore()
            mock_bm25 = BM25Index()
            mock_processor = MockDocumentProcessor()

            service = IndexService(
                vectorstore=mock_vectorstore,
                bm25_index=mock_bm25,
                notes_root=notes_root,
                document_processor=mock_processor
            )

            status = service.get_status()

            assert "notes_root" in status
            assert "is_indexing" in status
            assert "marker" in status
            assert status["notes_root"] == str(notes_root)
            assert status["is_indexing"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
