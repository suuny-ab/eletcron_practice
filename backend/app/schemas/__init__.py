"""
Pydantic 模型定义
定义API请求和响应的数据模型
"""

from .requests import SaveRequest, FileUpdateRequest, RAGRequest, UnifiedAgentRequest
from .responses import (
    BaseResponse,
    DataResponse,
    ErrorResponse,
    ConfigData,
    FileTreeNode,
    FileTreeData,
    FileReadResult,
    FileWriteResult,
    RAGSource,
    RAGAnswer,
    # RAG 调试响应模型
    VectorSearchResult,
    BM25SearchResult,
    HybridCandidate,
    RerankResult,
    RAGDebugInfo,
)
from .stream_models import StreamChunk, StreamComplete, StreamError

__all__ = [
    'SaveRequest',
    'FileUpdateRequest',
    'RAGRequest',
    'UnifiedAgentRequest',

    # 新的统一响应模型
    'BaseResponse',
    'DataResponse',
    'ErrorResponse',
    # 数据模型
    'ConfigData',
    'FileTreeNode',
    'FileTreeData',
    'FileReadResult',
    'FileWriteResult',
    'RAGSource',
    'RAGAnswer',
    # RAG 调试响应模型
    'VectorSearchResult',
    'BM25SearchResult',
    'HybridCandidate',
    'RerankResult',
    'RAGDebugInfo',

    # 流式模型
    'StreamChunk',
    'StreamComplete',
    'StreamError',
]
