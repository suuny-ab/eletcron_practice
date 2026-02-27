"""
RAG服务核心
整合索引、检索功能（门面模式）
"""
from pathlib import Path
from langchain_community.vectorstores import Chroma
from .config import VECTOR_DB_PATH
from .bm25_index import BM25Index
from .index_service import IndexService
from .retrieval_service import RetrievalService
from infrastructure.storage.document_processor import DocumentProcessor
from domain.ai.models.model_provider import ModelProvider
from domain.ai.services.llm_task_service import LLMTaskService
from infrastructure.logging.logger import get_logger
from core.interfaces import IRAGService, IModelProvider, ILLMTaskService

logger = get_logger(__name__)


class RAGService(IRAGService):
    """
    RAG服务门面

    协调IndexService和RetrievalService，提供统一的RAG能力
    """

    def __init__(
        self,
        model_provider: IModelProvider,
        notes_root: str,
        llm_task_service: ILLMTaskService,
    ):
        """
        初始化RAG服务

        Args:
            model_provider: 模型提供者实例
            notes_root: 笔记根目录路径
            llm_task_service: 统一LLM任务服务实例
        """
        self._notes_root = Path(notes_root)

        # 初始化向量数据库
        self._vectorstore = Chroma(
            persist_directory=str(VECTOR_DB_PATH),
            embedding_function=model_provider.embedding_model,
            collection_name="knowledge_base"
        )

        # 初始化BM25索引
        self._bm25_index = BM25Index()

        # 初始化文档处理器
        self._document_processor = DocumentProcessor()

        # 初始化子服务
        self._index_service = IndexService(
            vectorstore=self._vectorstore,
            bm25_index=self._bm25_index,
            notes_root=self._notes_root,
            document_processor=self._document_processor,
        )

        self._retrieval_service = RetrievalService(
            vectorstore=self._vectorstore,
            bm25_index=self._bm25_index,
            llm_task_service=llm_task_service,
        )

        logger.info("[RAG] 服务初始化完成")

    # ==================== 索引相关接口 ====================

    def start_indexing(self) -> None:
        """后台启动全量索引"""
        self._index_service.start_indexing()

    def stop_indexing(self, timeout: float = 30.0) -> bool:
        """停止索引线程"""
        return self._index_service.stop_indexing(timeout)

    def get_index_status(self) -> dict:
        """获取索引状态"""
        return self._index_service.get_status()

    def start_watcher(self) -> None:
        """启动文件监听器"""
        self._index_service.start_watcher()

    def stop_watcher(self) -> None:
        """停止文件监听器"""
        self._index_service.stop_watcher()

    # ==================== 检索相关接口 ====================

    def retrieve_sources(self, question: str, top_k: int = 3) -> list[dict]:
        """检索相关文档来源"""
        return self._retrieval_service.retrieve_sources(question, top_k)

    def build_context(self, sources: list[dict]) -> str:
        """根据检索来源构建上下文"""
        return self._retrieval_service.build_context(sources)

    def retrieve_context(self, question: str, top_k: int = 3) -> tuple[str, list[dict]]:
        """检索上下文"""
        return self._retrieval_service.retrieve_context(question, top_k)

    def retrieve_sources_debug(self, question: str, top_k: int = 3) -> dict:
        """带调试信息的检索（用于可视化调试面板）"""
        return self._retrieval_service.retrieve_sources_debug(question, top_k)

    # ==================== 属性访问（供外部直接访问子服务） ====================

    @property
    def vectorstore(self) -> Chroma:
        """向量数据库实例"""
        return self._vectorstore

    @property
    def bm25_index(self) -> BM25Index:
        """BM25索引实例"""
        return self._bm25_index

    @property
    def document_processor(self) -> DocumentProcessor:
        """文档处理器实例"""
        return self._document_processor
