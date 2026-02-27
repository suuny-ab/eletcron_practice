"""
API响应模型 - 定义API接口的响应数据结构
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar
from datetime import datetime


# ==================== Generic 类型变量 ====================
T = TypeVar('T')


# ==================== 基础响应模型 ====================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class DataResponse(BaseModel, Generic[T]):
    """
    带数据的统一响应模型（使用 Generic）
    
    用于包装任意类型的响应数据，提供统一的响应格式。
    
    Type Parameters:
        T: 数据类型（可以是 dict、list、或其他 BaseModel）
    
    Attributes:
        success: 操作是否成功，默认 true
        message: 提示信息，默认"操作成功"
        data: 响应数据，类型为 T
        timestamp: 时间戳

    """
    success: bool = True
    message: str = "操作成功"
    data: T
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    """统一错误响应模型"""
    success: bool = False
    message: str
    error_code: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ==================== 数据模型（只定义数据部分）====================

class FileReadResult(BaseModel):
    """文件读取结果"""
    success: bool
    filename: str
    file_size: int
    file_path: str
    content: str


class FileWriteResult(BaseModel):
    """文件写入结果"""
    success: bool
    filename: str
    file_size: int
    file_path: str


class ConfigData(BaseModel):
    """配置数据"""
    obsidian_vault_path: str
    api_key: str
    model_name: str
    prompts: dict[str, dict[str, str]] | None = None


class FileTreeNode(BaseModel):
    """文件树节点"""
    key: str
    title: str
    is_leaf: bool
    children: list['FileTreeNode'] | None = None


class FileTreeData(BaseModel):
    """文件树数据"""
    tree: list[FileTreeNode]


class RAGSource(BaseModel):
    """RAG 检索到的文档来源"""
    filename: str
    content: str
    score: float | None = None  # 相关性得分


class RAGAnswer(BaseModel):
    """RAG 问答回答"""
    answer: str
    sources: list[RAGSource] = Field(default_factory=list)


# ==================== RAG 调试响应模型 ====================

class VectorSearchResult(BaseModel):
    """向量检索单条结果"""
    filename: str
    content: str
    chunk_id: str | None = None
    raw_distance: float  # 原始距离
    similarity_score: float  # 相似度得分 (1 / (1 + distance))
    normalized_score: float  # 归一化后得分


class BM25SearchResult(BaseModel):
    """BM25检索单条结果"""
    filename: str
    content: str
    chunk_id: str | None = None
    tokens: list[str]  # 分词结果
    raw_score: float  # 原始BM25得分
    normalized_score: float  # 归一化后得分


class HybridCandidate(BaseModel):
    """混合检索候选"""
    filename: str
    content: str
    chunk_id: str | None = None
    vector_score: float  # 向量归一化得分
    bm25_score: float  # BM25归一化得分
    hybrid_score: float  # 混合得分 = vector_weight * vector + bm25_weight * bm25
    source: str  # 来源: "vector", "bm25", "both"


class RerankResult(BaseModel):
    """重排序结果"""
    original_rank: int  # 原始排名（混合检索后）
    final_rank: int | None = None  # 重排序后排名，未选中时为 None
    filename: str
    content: str
    hybrid_score: float
    selected: bool  # 是否被选中


class RAGDebugInfo(BaseModel):
    """RAG 调试信息"""
    # 查询信息
    query: str
    query_tokens: list[str]  # 查询分词结果
    top_k: int
    
    # 配置信息
    config: dict = Field(default_factory=dict)
    
    # 检索步骤详情
    vector_search: list[VectorSearchResult] = Field(default_factory=list)
    bm25_search: list[BM25SearchResult] = Field(default_factory=list)
    hybrid_candidates: list[HybridCandidate] = Field(default_factory=list)
    rerank_results: list[RerankResult] = Field(default_factory=list)
    
    # 性能指标
    timing: dict = Field(default_factory=dict)  # 各阶段耗时
    
    # 最终结果
    final_sources: list[RAGSource] = Field(default_factory=list)
