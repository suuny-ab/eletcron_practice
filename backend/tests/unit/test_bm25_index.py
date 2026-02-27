"""
BM25 索引单元测试
测试分词、索引构建、检索功能
"""
import pytest
from domain.knowledge.rag.bm25_index import BM25Index


class TestBM25Tokenize:
    """测试分词功能"""

    def test_tokenize_english_text(self):
        """测试英文分词"""
        index = BM25Index()
        tokens = index._tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_tokenize_chinese_text(self):
        """测试中文分词（单字切分）"""
        index = BM25Index()
        tokens = index._tokenize("你好世界")
        assert tokens == ["你", "好", "世", "界"]

    def test_tokenize_mixed_text(self):
        """测试中英混合分词"""
        index = BM25Index()
        tokens = index._tokenize("Hello你好World世界")
        assert "hello" in tokens
        assert "world" in tokens
        assert "你" in tokens
        assert "好" in tokens

    def test_tokenize_with_numbers(self):
        """测试包含数字的文本"""
        index = BM25Index()
        tokens = index._tokenize("Python3.8 版本 2024年")
        assert "python3" in tokens
        assert "8" in tokens
        assert "2024" in tokens

    def test_tokenize_empty_text(self):
        """测试空文本"""
        index = BM25Index()
        tokens = index._tokenize("")
        assert tokens == []

    def test_tokenize_none_text(self):
        """测试 None 输入"""
        index = BM25Index()
        tokens = index._tokenize(None)
        assert tokens == []

    def test_tokenize_special_characters(self):
        """测试特殊字符被过滤"""
        index = BM25Index()
        tokens = index._tokenize("Hello!@#$%World")
        assert tokens == ["hello", "world"]


class TestBM25Build:
    """测试索引构建"""

    def test_build_with_documents(self):
        """测试正常构建索引"""
        index = BM25Index()
        documents = [
            {"content": "Python 是一种编程语言", "metadata": {"filename": "doc1.md"}},
            {"content": "机器学习是人工智能的一个分支", "metadata": {"filename": "doc2.md"}},
        ]
        index.build(documents)
        assert index.is_built is True

    def test_build_with_empty_documents(self):
        """测试空文档列表"""
        index = BM25Index()
        index.build([])
        assert index.is_built is False

    def test_build_updates_internal_state(self):
        """测试构建后内部状态正确"""
        index = BM25Index()
        documents = [
            {"content": "文档内容1", "metadata": {"filename": "doc1.md"}},
            {"content": "文档内容2", "metadata": {"filename": "doc2.md"}},
        ]
        index.build(documents)
        assert len(index._texts) == 2
        assert len(index._metadatas) == 2


class TestBM25Search:
    """测试检索功能"""

    @pytest.fixture
    def built_index(self):
        """预构建的索引"""
        index = BM25Index()
        documents = [
            {"content": "Python 是一种流行的编程语言", "metadata": {"filename": "python.md"}},
            {"content": "机器学习需要大量数据", "metadata": {"filename": "ml.md"}},
            {"content": "深度学习是机器学习的子集", "metadata": {"filename": "dl.md"}},
            {"content": "Python 可以用于机器学习开发", "metadata": {"filename": "pyml.md"}},
        ]
        index.build(documents)
        return index

    def test_search_returns_results(self, built_index):
        """测试检索返回结果"""
        results = built_index.search("Python 编程", top_k=2)
        assert len(results) > 0
        assert len(results) <= 2

    def test_search_result_format(self, built_index):
        """测试结果格式正确"""
        results = built_index.search("机器学习", top_k=1)
        assert len(results) == 1
        content, metadata, score = results[0]
        assert isinstance(content, str)
        assert isinstance(metadata, dict)
        assert isinstance(score, float)

    def test_search_relevance(self, built_index):
        """测试检索相关性"""
        results = built_index.search("Python", top_k=4)
        # Python 相关的文档应该排在前面
        top_filenames = [r[1]["filename"] for r in results[:2]]
        assert any("python" in f.lower() for f in top_filenames)

    def test_search_empty_query(self, built_index):
        """测试空查询"""
        results = built_index.search("", top_k=2)
        assert results == []

    def test_search_on_empty_index(self):
        """测试空索引上的检索"""
        index = BM25Index()
        results = index.search("test", top_k=2)
        assert results == []

    def test_search_top_k_limit(self, built_index):
        """测试 top_k 限制"""
        results = built_index.search("学习", top_k=2)
        assert len(results) <= 2

    def test_search_chinese_query(self, built_index):
        """测试中文查询"""
        results = built_index.search("深度学习", top_k=2)
        assert len(results) > 0
        # 深度学习文档应该排在前面
        assert "深度学习" in results[0][0] or "机器学习" in results[0][0]


class TestBM25UpdateFile:
    """测试文件更新功能"""

    def test_update_file_add_new(self):
        """测试添加新文件"""
        index = BM25Index()
        documents = [
            {"content": "原始文档", "metadata": {"filename": "original.md"}},
        ]
        index.build(documents)

        new_chunks = [
            {"content": "新文档内容", "metadata": {"filename": "new.md"}},
        ]
        index.update_file("new.md", new_chunks)

        assert len(index._texts) == 2

    def test_update_file_replace_existing(self):
        """测试替换已有文件"""
        index = BM25Index()
        documents = [
            {"content": "旧内容", "metadata": {"filename": "doc.md"}},
            {"content": "其他文档", "metadata": {"filename": "other.md"}},
        ]
        index.build(documents)

        new_chunks = [
            {"content": "新内容", "metadata": {"filename": "doc.md"}},
        ]
        index.update_file("doc.md", new_chunks)

        # 总数不变（1 个被替换）
        assert len(index._texts) == 2
        # 新内容应该存在
        assert "新内容" in index._texts

    def test_update_file_remove(self):
        """测试移除文件（传入空 chunks）"""
        index = BM25Index()
        documents = [
            {"content": "文档1", "metadata": {"filename": "doc1.md"}},
            {"content": "文档2", "metadata": {"filename": "doc2.md"}},
        ]
        index.build(documents)

        index.update_file("doc1.md", [])

        assert len(index._texts) == 1
        assert index._metadatas[0]["filename"] == "doc2.md"


class TestBM25ThreadSafety:
    """测试线程安全性"""

    def test_concurrent_search(self):
        """测试并发检索"""
        import threading

        index = BM25Index()
        documents = [
            {"content": f"文档 {i}", "metadata": {"filename": f"doc{i}.md"}}
            for i in range(100)
        ]
        index.build(documents)

        results = []
        errors = []

        def search_task():
            try:
                for _ in range(10):
                    result = index.search("文档", top_k=5)
                    results.append(len(result))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=search_task) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r > 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
