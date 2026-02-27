"""
BM25 索引管理
提供BM25检索能力
"""
import re
import math
from threading import Lock
from rank_bm25 import BM25Okapi
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


class BM25Index:
    """BM25索引管理器"""

    def __init__(self):
        self._lock = Lock()
        self._index: BM25Okapi | None = None
        self._texts: list[str] = []
        self._metadatas: list[dict] = []

    def _tokenize(self, text: str) -> list[str]:
        """将文本拆分为BM25可用的tokens（中英文混合）"""
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

    def build(self, documents: list[dict]) -> None:
        """
        基于文档块构建索引

        Args:
            documents: 文档列表，每个文档包含 content 和 metadata
        """
        with self._lock:
            self._texts = [doc["content"] for doc in documents]
            self._metadatas = [doc["metadata"] for doc in documents]
            tokenized = [self._tokenize(text) for text in self._texts]
            self._index = BM25Okapi(tokenized) if tokenized else None

    def update_file(self, filename: str, chunks: list[dict]) -> None:
        """
        更新指定文件的索引条目

        Args:
            filename: 文件名（相对路径）
            chunks: 新的文档块列表
        """
        with self._lock:
            # 移除旧条目
            kept_texts: list[str] = []
            kept_metadatas: list[dict] = []
            for text, metadata in zip(self._texts, self._metadatas):
                if metadata.get("filename") != filename:
                    kept_texts.append(text)
                    kept_metadatas.append(metadata)

            # 添加新条目
            for doc in chunks:
                kept_texts.append(doc["content"])
                kept_metadatas.append(doc["metadata"])

            self._texts = kept_texts
            self._metadatas = kept_metadatas
            tokenized = [self._tokenize(text) for text in self._texts]
            self._index = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, top_k: int) -> list[tuple[str, dict, float]]:
        """
        执行BM25检索

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            (content, metadata, score) 元组列表
        """
        if not self._index or not self._texts:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self._index.get_scores(tokens)
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            results.append((self._texts[idx], self._metadatas[idx], score))
        return results

    @property
    def is_built(self) -> bool:
        """索引是否已构建"""
        return self._index is not None
