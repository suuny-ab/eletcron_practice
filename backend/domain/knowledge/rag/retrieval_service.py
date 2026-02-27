"""
检索服务
负责向量检索、BM25检索、混合检索和重排序
"""
import math
import time
from langchain_community.vectorstores import Chroma
from .bm25_index import BM25Index
from .config import VECTOR_TOP_K, BM25_TOP_K, HYBRID_TOP_K, VECTOR_WEIGHT, BM25_WEIGHT
from domain.ai.services.llm_task_service import LLMTaskService
from infrastructure.logging.logger import get_logger, LogContext
from infrastructure.metrics import get_metrics

logger = get_logger(__name__)


class RetrievalService:
    """检索服务"""

    def __init__(
        self,
        vectorstore: Chroma,
        bm25_index: BM25Index,
        llm_task_service: LLMTaskService,
    ):
        """
        初始化检索服务

        Args:
            vectorstore: 向量数据库实例
            bm25_index: BM25索引实例
            llm_task_service: LLM任务服务实例
        """
        self._vectorstore = vectorstore
        self._bm25_index = bm25_index
        self._llm_task_service = llm_task_service

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """将分数归一化到0-1区间"""
        if not scores:
            return []
        min_score = min(scores)
        max_score = max(scores)
        if math.isclose(max_score, min_score):
            return [1.0 for _ in scores]
        return [(score - min_score) / (max_score - min_score) for score in scores]

    def _llm_rerank(self, question: str, candidates: list[dict], top_k: int) -> list[int]:
        """
        使用LLM对候选进行重排序

        Args:
            question: 查询问题
            candidates: 候选文档列表
            top_k: 返回数量

        Returns:
            重排序后的索引列表
        """
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

    def retrieve_sources(self, question: str, top_k: int = 3) -> list[dict]:
        """
        检索相关文档来源（混合检索 + LLM重排序）

        Args:
            question: 查询问题
            top_k: 返回的最相关文档数量

        Returns:
            来源列表
        """
        metrics = get_metrics()
        start_time = time.perf_counter()

        if not self._vectorstore:
            raise ValueError("向量数据库未初始化")

        try:
            # 向量检索
            vector_results = self._vectorstore.similarity_search_with_score(
                query=question,
                k=VECTOR_TOP_K
            )
            # BM25检索
            bm25_results = self._bm25_index.search(question, BM25_TOP_K)

            if not vector_results and not bm25_results:
                return []

            # 合并候选
            candidates: dict[str, dict] = {}

            # 处理向量检索结果
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

            # 处理BM25检索结果
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

            # 混合评分
            merged = []
            for cand in candidates.values():
                hybrid_score = VECTOR_WEIGHT * cand["vector_score"] + BM25_WEIGHT * cand["bm25_score"]
                cand["hybrid_score"] = hybrid_score
                merged.append(cand)

            merged.sort(key=lambda item: item["hybrid_score"], reverse=True)
            if HYBRID_TOP_K > 0:
                merged = merged[:min(HYBRID_TOP_K, len(merged))]

            # LLM重排序
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
        finally:
            elapsed = time.perf_counter() - start_time
            metrics.observe("rag.retrieval.duration_seconds", elapsed)
            metrics.increment("rag.retrieval.queries")

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

        Args:
            question: 查询问题
            top_k: 返回数量

        Returns:
            (context, sources)
        """
        sources = self.retrieve_sources(question=question, top_k=top_k)
        context = self.build_context(sources)
        return context, sources
