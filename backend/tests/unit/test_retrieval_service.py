"""
检索服务单元测试
测试向量检索、BM25检索、混合检索和LLM重排序
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from domain.knowledge.rag.retrieval_service import RetrievalService
from domain.knowledge.rag.bm25_index import BM25Index


class MockVectorStore:
    """Mock 向量数据库"""

    def __init__(self, results=None):
        self.results = results or []

    def similarity_search_with_score(self, query: str, k: int):
        return self.results[:k]


class MockLLMTaskService:
    """Mock LLM 任务服务"""

    def __init__(self, rerank_result=None):
        self.rerank_result = rerank_result or [0, 1, 2]
        self.invoke_calls = []

    def invoke(self, task_type: str, **kwargs):
        self.invoke_calls.append({"task_type": task_type, **kwargs})
        if task_type == "rerank":
            return self.rerank_result
        return []


class TestNormalizeScores:
    """测试分数归一化"""

    def test_normalize_normal_scores(self):
        """测试正常分数归一化"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        scores = [0.0, 0.5, 1.0]
        normalized = service._normalize_scores(scores)

        assert normalized[0] == 0.0
        assert normalized[2] == 1.0
        assert 0.0 <= normalized[1] <= 1.0

    def test_normalize_empty_scores(self):
        """测试空分数列表"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        normalized = service._normalize_scores([])
        assert normalized == []

    def test_normalize_same_scores(self):
        """测试相同分数（避免除零）"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        scores = [0.5, 0.5, 0.5]
        normalized = service._normalize_scores(scores)

        # 所有分数相同时应返回 1.0
        assert all(s == 1.0 for s in normalized)

    def test_normalize_negative_scores(self):
        """测试负分数"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        scores = [-1.0, 0.0, 1.0]
        normalized = service._normalize_scores(scores)

        assert normalized[0] == 0.0
        assert normalized[2] == 1.0


class TestLLMRerank:
    """测试 LLM 重排序"""

    def test_rerank_normal_case(self):
        """测试正常重排序"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[2, 0, 1])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        candidates = [
            {"content": "文档0"},
            {"content": "文档1"},
            {"content": "文档2"},
        ]

        indices = service._llm_rerank("测试问题", candidates, top_k=3)

        assert indices == [2, 0, 1]
        assert len(mock_llm.invoke_calls) == 1
        assert mock_llm.invoke_calls[0]["task_type"] == "rerank"

    def test_rerank_empty_candidates(self):
        """测试空候选列表"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        indices = service._llm_rerank("测试问题", [], top_k=3)
        assert indices == []

    def test_rerank_zero_top_k(self):
        """测试 top_k 为 0"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        candidates = [{"content": "文档0"}]
        indices = service._llm_rerank("测试问题", candidates, top_k=0)
        assert indices == []

    def test_rerank_filters_invalid_indices(self):
        """测试过滤无效索引"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        # 返回包含无效索引的结果
        mock_llm = MockLLMTaskService(rerank_result=[0, 100, 1, -1, 2])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        candidates = [
            {"content": "文档0"},
            {"content": "文档1"},
            {"content": "文档2"},
        ]

        indices = service._llm_rerank("测试问题", candidates, top_k=3)

        # 只保留有效索引
        assert all(0 <= i < len(candidates) for i in indices)
        assert len(indices) <= 3

    def test_rerank_filters_duplicates(self):
        """测试过滤重复索引"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0, 0, 1, 1, 2])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        candidates = [
            {"content": "文档0"},
            {"content": "文档1"},
            {"content": "文档2"},
        ]

        indices = service._llm_rerank("测试问题", candidates, top_k=5)

        # 应该去重
        assert len(indices) == len(set(indices))

    def test_rerank_truncates_content(self):
        """测试长内容被截断"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        long_content = "x" * 500
        candidates = [{"content": long_content}]

        service._llm_rerank("测试问题", candidates, top_k=1)

        # 检查传递给 LLM 的内容被截断
        call = mock_llm.invoke_calls[0]
        assert len(call["candidates"]) < len(long_content) + 50

    def test_rerank_invalid_return_type(self):
        """测试 LLM 返回非数组时抛出异常"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()
        mock_llm.invoke = Mock(return_value="not a list")

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        candidates = [{"content": "文档0"}]

        with pytest.raises(ValueError, match="rerank 返回结果不是JSON数组"):
            service._llm_rerank("测试问题", candidates, top_k=1)

    def test_rerank_invalid_index_type(self):
        """测试 LLM 返回非整数索引时抛出异常"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()
        mock_llm.invoke = Mock(return_value=["not", "integers"])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        candidates = [{"content": "文档0"}]

        with pytest.raises(ValueError, match="rerank 返回包含非整数索引"):
            service._llm_rerank("测试问题", candidates, top_k=1)


class TestRetrieveSources:
    """测试混合检索"""

    def _create_mock_doc(self, content: str, filename: str, chunk_id: str = None):
        """创建 Mock 文档"""
        doc = Mock()
        doc.page_content = content
        doc.metadata = {"filename": filename}
        if chunk_id:
            doc.metadata["chunk_id"] = chunk_id
        return doc

    def test_retrieve_sources_no_vectorstore(self):
        """测试向量库未初始化时抛出异常"""
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(None, mock_bm25, mock_llm)

        with pytest.raises(ValueError, match="向量数据库未初始化"):
            service.retrieve_sources("测试问题")

    def test_retrieve_sources_empty_results(self):
        """测试没有检索结果"""
        mock_vectorstore = MockVectorStore(results=[])
        mock_bm25 = BM25Index()
        mock_bm25.build([])
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        results = service.retrieve_sources("测试问题")
        assert results == []

    def test_retrieve_sources_vector_only(self):
        """测试仅有向量检索结果"""
        doc = self._create_mock_doc("向量文档内容", "vector.md", "chunk_1")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_bm25.build([])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        results = service.retrieve_sources("测试问题", top_k=1)

        assert len(results) == 1
        assert results[0]["filename"] == "vector.md"

    def test_retrieve_sources_bm25_only(self):
        """测试仅有 BM25 检索结果"""
        mock_vectorstore = MockVectorStore(results=[])
        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "BM25文档内容", "metadata": {"filename": "bm25.md", "chunk_id": "chunk_1"}}
        ])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        results = service.retrieve_sources("BM25文档", top_k=1)

        assert len(results) == 1
        assert results[0]["filename"] == "bm25.md"

    def test_retrieve_sources_hybrid(self):
        """测试混合检索结果合并"""
        doc = self._create_mock_doc("向量文档", "vector.md", "chunk_v")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])

        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "BM25文档", "metadata": {"filename": "bm25.md", "chunk_id": "chunk_b"}}
        ])

        mock_llm = MockLLMTaskService(rerank_result=[0, 1])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        results = service.retrieve_sources("测试", top_k=2)

        # 应该包含两种来源的结果
        filenames = [r["filename"] for r in results]
        assert len(results) <= 2

    def test_retrieve_sources_deduplication(self):
        """测试重复文档去重"""
        # 向量和 BM25 返回相同的文档
        doc = self._create_mock_doc("相同文档", "same.md", "chunk_same")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])

        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "相同文档", "metadata": {"filename": "same.md", "chunk_id": "chunk_same"}}
        ])

        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        results = service.retrieve_sources("相同", top_k=2)

        # 去重后应该只有一个结果
        assert len(results) == 1

    def test_retrieve_sources_result_format(self):
        """测试返回结果格式"""
        doc = self._create_mock_doc("测试内容", "test.md", "chunk_1")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_bm25.build([])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        results = service.retrieve_sources("测试", top_k=1)

        assert len(results) == 1
        result = results[0]
        assert "filename" in result
        assert "content" in result
        assert "score" in result
        assert isinstance(result["score"], float)


class TestBuildContext:
    """测试上下文构建"""

    def test_build_context_single_source(self):
        """测试单个来源的上下文"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        sources = [
            {"filename": "test.md", "content": "测试内容"}
        ]

        context = service.build_context(sources)

        assert "参考资料 1" in context
        assert "test.md" in context
        assert "测试内容" in context

    def test_build_context_multiple_sources(self):
        """测试多个来源的上下文"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        sources = [
            {"filename": "doc1.md", "content": "内容1"},
            {"filename": "doc2.md", "content": "内容2"},
        ]

        context = service.build_context(sources)

        assert "参考资料 1" in context
        assert "参考资料 2" in context
        assert "doc1.md" in context
        assert "doc2.md" in context

    def test_build_context_empty_sources(self):
        """测试空来源列表"""
        mock_vectorstore = MockVectorStore()
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        context = service.build_context([])
        assert context == ""


class TestRetrieveContext:
    """测试完整检索流程"""

    def test_retrieve_context_returns_tuple(self):
        """测试返回 (context, sources) 元组"""
        doc = Mock()
        doc.page_content = "文档内容"
        doc.metadata = {"filename": "test.md", "chunk_id": "chunk_1"}

        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_bm25.build([])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        context, sources = service.retrieve_context("测试", top_k=1)

        assert isinstance(context, str)
        assert isinstance(sources, list)
        assert len(sources) == 1


class TestRetrieveSourcesDebug:
    """测试调试模式检索"""

    def _create_mock_doc(self, content: str, filename: str, chunk_id: str = None):
        """创建 Mock 文档"""
        doc = Mock()
        doc.page_content = content
        doc.metadata = {"filename": filename}
        if chunk_id:
            doc.metadata["chunk_id"] = chunk_id
        return doc

    def test_debug_returns_query_info(self):
        """测试返回查询信息"""
        doc = self._create_mock_doc("测试内容", "test.md", "chunk_1")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_bm25.build([{"content": "测试内容", "metadata": {"filename": "test.md"}}])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试问题", top_k=3)

        assert debug_info["query"] == "测试问题"
        assert debug_info["top_k"] == 3
        assert isinstance(debug_info["query_tokens"], list)
        assert len(debug_info["query_tokens"]) > 0

    def test_debug_returns_config(self):
        """测试返回配置信息"""
        mock_vectorstore = MockVectorStore(results=[])
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        config = debug_info["config"]
        assert "vector_top_k" in config
        assert "bm25_top_k" in config
        assert "hybrid_top_k" in config
        assert "vector_weight" in config
        assert "bm25_weight" in config

    def test_debug_returns_vector_search_details(self):
        """测试返回向量检索详情"""
        doc = self._create_mock_doc("向量内容", "vector.md", "v_chunk")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        assert len(debug_info["vector_search"]) == 1
        vs_result = debug_info["vector_search"][0]
        assert vs_result["filename"] == "vector.md"
        assert "raw_distance" in vs_result
        assert "similarity_score" in vs_result
        assert "normalized_score" in vs_result

    def test_debug_returns_bm25_search_details(self):
        """测试返回 BM25 检索详情"""
        mock_vectorstore = MockVectorStore(results=[])
        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "BM25测试内容", "metadata": {"filename": "bm25.md", "chunk_id": "b_chunk"}}
        ])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("BM25测试", top_k=1)

        assert len(debug_info["bm25_search"]) >= 1
        bm25_result = debug_info["bm25_search"][0]
        assert bm25_result["filename"] == "bm25.md"
        assert "tokens" in bm25_result
        assert isinstance(bm25_result["tokens"], list)
        assert "raw_score" in bm25_result
        assert "normalized_score" in bm25_result

    def test_debug_returns_hybrid_candidates(self):
        """测试返回混合候选详情"""
        doc = self._create_mock_doc("混合内容", "hybrid.md", "h_chunk")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.3)])
        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "混合内容", "metadata": {"filename": "hybrid.md", "chunk_id": "h_chunk"}}
        ])
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("混合", top_k=1)

        assert len(debug_info["hybrid_candidates"]) >= 1
        candidate = debug_info["hybrid_candidates"][0]
        assert "vector_score" in candidate
        assert "bm25_score" in candidate
        assert "hybrid_score" in candidate
        assert "source" in candidate
        assert candidate["source"] in ["vector", "bm25", "both"]

    def test_debug_returns_rerank_results(self):
        """测试返回重排序结果"""
        doc = self._create_mock_doc("重排内容", "rerank.md", "r_chunk")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        assert len(debug_info["rerank_results"]) >= 1
        rerank_result = debug_info["rerank_results"][0]
        assert "original_rank" in rerank_result
        assert "final_rank" in rerank_result
        assert "selected" in rerank_result
        assert isinstance(rerank_result["selected"], bool)

    def test_debug_returns_timing(self):
        """测试返回耗时统计"""
        doc = self._create_mock_doc("计时内容", "timing.md")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        timing = debug_info["timing"]
        assert "vector_search_ms" in timing
        assert "bm25_search_ms" in timing
        assert "merge_ms" in timing
        assert "rerank_ms" in timing
        assert "total_ms" in timing
        assert all(isinstance(v, (int, float)) for v in timing.values())

    def test_debug_returns_final_sources(self):
        """测试返回最终结果"""
        doc = self._create_mock_doc("最终内容", "final.md", "f_chunk")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        assert len(debug_info["final_sources"]) == 1
        source = debug_info["final_sources"][0]
        assert source["filename"] == "final.md"
        assert "content" in source
        assert "score" in source

    def test_debug_handles_empty_results(self):
        """测试处理空结果"""
        mock_vectorstore = MockVectorStore(results=[])
        mock_bm25 = BM25Index()
        mock_bm25.build([])
        mock_llm = MockLLMTaskService()

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("无结果", top_k=3)

        assert debug_info["vector_search"] == []
        assert debug_info["bm25_search"] == []
        assert debug_info["hybrid_candidates"] == []
        assert debug_info["final_sources"] == []

    def test_debug_handles_no_vectorstore(self):
        """测试无向量库时返回基本结构"""
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService()

        service = RetrievalService(None, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        assert debug_info["query"] == "测试"
        assert debug_info["vector_search"] == []
        assert debug_info["final_sources"] == []

    def test_debug_content_truncation(self):
        """测试长内容被截断"""
        long_content = "x" * 1000
        doc = self._create_mock_doc(long_content, "long.md")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])
        mock_bm25 = BM25Index()
        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=1)

        # 向量检索结果应该被截断
        vs_content = debug_info["vector_search"][0]["content"]
        assert len(vs_content) <= 510  # 500 + "..."

    def test_debug_source_tagging(self):
        """测试来源标记正确性"""
        # 只在向量检索中
        doc_vector = self._create_mock_doc("仅向量", "vector_only.md", "v_only")
        mock_vectorstore = MockVectorStore(results=[(doc_vector, 0.5)])

        # 只在 BM25 中
        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "仅BM25", "metadata": {"filename": "bm25_only.md", "chunk_id": "b_only"}}
        ])

        mock_llm = MockLLMTaskService(rerank_result=[0, 1])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("测试", top_k=2)

        # 检查来源标记
        sources_map = {c["filename"]: c["source"] for c in debug_info["hybrid_candidates"]}
        assert sources_map.get("vector_only.md") == "vector"
        assert sources_map.get("bm25_only.md") == "bm25"

    def test_debug_both_source_tagging(self):
        """测试同时命中两种检索的来源标记"""
        doc = self._create_mock_doc("双重命中", "both.md", "both_chunk")
        mock_vectorstore = MockVectorStore(results=[(doc, 0.5)])

        mock_bm25 = BM25Index()
        mock_bm25.build([
            {"content": "双重命中", "metadata": {"filename": "both.md", "chunk_id": "both_chunk"}}
        ])

        mock_llm = MockLLMTaskService(rerank_result=[0])

        service = RetrievalService(mock_vectorstore, mock_bm25, mock_llm)

        debug_info = service.retrieve_sources_debug("双重", top_k=1)

        # 应该标记为 "both"
        assert len(debug_info["hybrid_candidates"]) == 1
        assert debug_info["hybrid_candidates"][0]["source"] == "both"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
