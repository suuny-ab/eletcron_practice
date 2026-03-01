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

    def _distance_to_similarity(self, distance: float) -> float:
        """
        将距离转换为相似度得分
        
        使用指数衰减函数：exp(-distance * alpha)
        - alpha = 0.5 时：距离 0 -> 1.0, 距离 1 -> 0.61, 距离 2 -> 0.37
        - 比 1/(1+x) 有更好的区分度
        """
        import math
        alpha = 0.5  # 衰减系数，可根据实际情况调整
        return math.exp(-distance * alpha)

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """将分数归一化到0-1区间"""
        if not scores:
            return []
        min_score = min(scores)
        max_score = max(scores)
        if math.isclose(max_score, min_score):
            return [1.0 for _ in scores]
        return [(score - min_score) / (max_score - min_score) for score in scores]

    def _llm_rerank(self, question: str, candidates: list[dict]) -> list[int]:
        """
        使用LLM对候选进行重排序

        LLM根据相关性自主决定返回多少条结果，不设固定数量约束。

        Args:
            question: 查询问题
            candidates: 候选文档列表

        Returns:
            重排序后的索引列表
        """
        if not candidates:
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

        logger.info(f"[Rerank] LLM 从 {len(candidates)} 个候选中选出 {len(filtered)} 条相关结果")
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
                sim_score = self._distance_to_similarity(raw_score)
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
            rerank_indices = self._llm_rerank(question, merged)
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

    def retrieve_sources_debug(self, question: str, top_k: int = 3) -> dict:
        """
        带调试信息的检索（用于可视化调试面板）

        Args:
            question: 查询问题
            top_k: 返回的最相关文档数量

        Returns:
            包含详细检索步骤信息的字典
        """
        import time
        from .config import VECTOR_TOP_K, BM25_TOP_K, HYBRID_TOP_K, VECTOR_WEIGHT, BM25_WEIGHT

        debug_info = {
            "query": question,
            "query_tokens": self._bm25_index._tokenize(question),
            "top_k": top_k,
            "config": {
                "vector_top_k": VECTOR_TOP_K,
                "bm25_top_k": BM25_TOP_K,
                "hybrid_top_k": HYBRID_TOP_K,
                "vector_weight": VECTOR_WEIGHT,
                "bm25_weight": BM25_WEIGHT,
            },
            "vector_search": [],
            "bm25_search": [],
            "hybrid_candidates": [],
            "rerank_results": [],
            "timing": {},
            "final_sources": [],
        }

        if not self._vectorstore:
            return debug_info

        total_start = time.perf_counter()

        # ==================== 向量检索阶段 ====================
        vector_start = time.perf_counter()
        vector_results = self._vectorstore.similarity_search_with_score(
            query=question,
            k=VECTOR_TOP_K
        )
        debug_info["timing"]["vector_search_ms"] = round((time.perf_counter() - vector_start) * 1000, 2)

        # 处理向量检索结果
        vector_sims: list[float] = []
        vector_docs: list[tuple] = []
        for doc, score in vector_results:
            raw_score = float(score)
            sim_score = self._distance_to_similarity(raw_score)
            vector_sims.append(sim_score)
            vector_docs.append((doc, raw_score, sim_score))

        vector_norms = self._normalize_scores(vector_sims)

        for idx, (doc, raw_distance, sim_score) in enumerate(vector_docs):
            metadata = doc.metadata or {}
            debug_info["vector_search"].append({
                "filename": metadata.get("filename", ""),
                "content": doc.page_content[:500] + ("..." if len(doc.page_content) > 500 else ""),
                "chunk_id": metadata.get("chunk_id"),
                "raw_distance": round(raw_distance, 4),
                "similarity_score": round(sim_score, 4),
                "normalized_score": round(vector_norms[idx], 4),
            })

        # ==================== BM25检索阶段 ====================
        bm25_start = time.perf_counter()
        bm25_results = self._bm25_index.search(question, BM25_TOP_K)
        debug_info["timing"]["bm25_search_ms"] = round((time.perf_counter() - bm25_start) * 1000, 2)

        # 处理BM25检索结果
        bm25_scores = [score for _, _, score in bm25_results]
        bm25_norms = self._normalize_scores(bm25_scores)

        for idx, (content, metadata, score) in enumerate(bm25_results):
            tokens = self._bm25_index._tokenize(content)
            debug_info["bm25_search"].append({
                "filename": metadata.get("filename", ""),
                "content": content[:500] + ("..." if len(content) > 500 else ""),
                "chunk_id": metadata.get("chunk_id"),
                "tokens": tokens[:50] + (["..."] if len(tokens) > 50 else []),  # 限制token数量
                "raw_score": round(float(score), 4),
                "normalized_score": round(bm25_norms[idx], 4) if idx < len(bm25_norms) else 0.0,
            })

        # ==================== 混合评分阶段 ====================
        merge_start = time.perf_counter()

        candidates: dict[str, dict] = {}

        # 合并向量检索结果
        for idx, (doc, raw_distance, sim_score) in enumerate(vector_docs):
            metadata = doc.metadata or {}
            key = metadata.get("chunk_id") or f"{metadata.get('filename', '')}::{doc.page_content}"
            if key not in candidates:
                candidates[key] = {
                    "filename": metadata.get("filename", ""),
                    "content": doc.page_content,
                    "chunk_id": metadata.get("chunk_id"),
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                    "source": "vector",
                }
            candidates[key]["vector_score"] = vector_norms[idx]

        # 合并BM25检索结果
        for idx, (content, metadata, score) in enumerate(bm25_results):
            key = metadata.get("chunk_id") or f"{metadata.get('filename', '')}::{content}"
            if key not in candidates:
                candidates[key] = {
                    "filename": metadata.get("filename", ""),
                    "content": content,
                    "chunk_id": metadata.get("chunk_id"),
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                    "source": "bm25",
                }
            else:
                # 两种检索都命中
                candidates[key]["source"] = "both"
            candidates[key]["bm25_score"] = bm25_norms[idx] if idx < len(bm25_norms) else 0.0

        # 计算混合得分
        merged = []
        for cand in candidates.values():
            hybrid_score = VECTOR_WEIGHT * cand["vector_score"] + BM25_WEIGHT * cand["bm25_score"]
            cand["hybrid_score"] = hybrid_score
            merged.append(cand)

        merged.sort(key=lambda item: item["hybrid_score"], reverse=True)
        if HYBRID_TOP_K > 0:
            merged = merged[:min(HYBRID_TOP_K, len(merged))]

        debug_info["timing"]["merge_ms"] = round((time.perf_counter() - merge_start) * 1000, 2)

        # 记录混合候选
        for cand in merged:
            debug_info["hybrid_candidates"].append({
                "filename": cand["filename"],
                "content": cand["content"][:500] + ("..." if len(cand["content"]) > 500 else ""),
                "chunk_id": cand["chunk_id"],
                "vector_score": round(cand["vector_score"], 4),
                "bm25_score": round(cand["bm25_score"], 4),
                "hybrid_score": round(cand["hybrid_score"], 4),
                "source": cand["source"],
            })

        # ==================== LLM重排序阶段 ====================
        rerank_start = time.perf_counter()
        try:
            rerank_indices = self._llm_rerank(question, merged)
        except Exception as e:
            logger.warning(f"[RAG Debug] LLM重排序失败: {e}")
            rerank_indices = []
        debug_info["timing"]["rerank_ms"] = round((time.perf_counter() - rerank_start) * 1000, 2)

        # 记录重排序结果
        selected_set = set(rerank_indices)
        for original_rank, cand in enumerate(merged):
            final_rank = rerank_indices.index(original_rank) if original_rank in selected_set else -1
            debug_info["rerank_results"].append({
                "original_rank": original_rank,
                "final_rank": final_rank if final_rank >= 0 else None,
                "filename": cand["filename"],
                "content": cand["content"][:300] + ("..." if len(cand["content"]) > 300 else ""),
                "hybrid_score": round(cand["hybrid_score"], 4),
                "selected": original_rank in selected_set,
            })

        # ==================== 最终结果 ====================
        if rerank_indices:
            selected = [merged[i] for i in rerank_indices]
        else:
            selected = merged[:top_k]

        for item in selected:
            debug_info["final_sources"].append({
                "filename": item["filename"],
                "content": item["content"],
                "score": round(float(item.get("hybrid_score", 0.0)), 4),
            })

        debug_info["timing"]["total_ms"] = round((time.perf_counter() - total_start) * 1000, 2)

        return debug_info
