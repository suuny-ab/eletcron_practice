"""
依赖注入 - 提供 FastAPI 依赖函数
"""
from fastapi import Request

from domain.ai.models.model_provider import ModelProvider
from domain.ai.services.chat_model import ChatModelService
from domain.ai.services.llm_task_service import LLMTaskService
from domain.knowledge.repositories.knowledge_repository import KnowledgeRepository
from .services import AIService, SessionCleanupService
from domain.knowledge.services.knowledge_service import KnowledgeService
from infrastructure.config.config_context import ConfigContext





class ServiceFactory:
    """服务工厂 - 统一管理服务实例生命周期"""

    def __init__(self):
        self._model_provider: ModelProvider | None = None
        self._chat_model_service: ChatModelService | None = None
        self._llm_task_service: LLMTaskService | None = None
        self._ai_service: AIService | None = None
        self._knowledge_repository: KnowledgeRepository | None = None
        self._knowledge_service: KnowledgeService | None = None
        self._config_context: ConfigContext | None = None




    def set_config_context(self, config_context: ConfigContext) -> None:
        """设置配置上下文"""
        self._config_context = config_context

    def set_model_provider(self, model_provider: ModelProvider | None) -> None:
        """更新模型提供者并重置依赖服务"""
        self._model_provider = model_provider
        self._chat_model_service = None
        self._llm_task_service = None
        self._ai_service = None



    def get_model_provider(self) -> ModelProvider:
        """获取模型提供者实例（单例）"""
        if not self._model_provider:
            raise ValueError("ModelProvider 未初始化")
        return self._model_provider

    def get_chat_model_service(self) -> ChatModelService:
        """获取聊天模型服务实例（单例）"""
        if not self._chat_model_service:
            self._chat_model_service = ChatModelService(self.get_model_provider())
        return self._chat_model_service

    def get_llm_task_service(self) -> LLMTaskService:
        """获取统一LLM任务服务实例（单例）"""
        if not self._llm_task_service:
            self._llm_task_service = LLMTaskService(self.get_chat_model_service())
        return self._llm_task_service

    def get_knowledge_repository(self) -> KnowledgeRepository:
        """获取知识库仓储实例（单例）"""
        if not self._config_context:
            raise ValueError("ConfigContext 未初始化")
        if not self._knowledge_repository:
            self._knowledge_repository = KnowledgeRepository(self._config_context)
        return self._knowledge_repository


    def get_knowledge_service(self) -> KnowledgeService:
        """获取知识库服务实例（单例）"""
        if not self._knowledge_service:
            self._knowledge_service = KnowledgeService(self.get_knowledge_repository())
        return self._knowledge_service

    def get_ai_service(self) -> AIService:
        """获取 AI 服务实例（单例）"""
        if not self._ai_service:
            llm_task_service = self.get_llm_task_service()
            knowledge_repository = self.get_knowledge_repository()
            self._ai_service = AIService(llm_task_service, knowledge_repository)
        return self._ai_service



    def snapshot(self) -> tuple[
        ModelProvider | None,
        ChatModelService | None,
        LLMTaskService | None,
        AIService | None
    ]:
        """保存当前状态快照，用于回滚"""
        return (
            self._model_provider,
            self._chat_model_service,
            self._llm_task_service,
            self._ai_service
        )

    def restore(self, snapshot: tuple[
        ModelProvider | None,
        ChatModelService | None,
        LLMTaskService | None,
        AIService | None
    ]) -> None:
        """恢复到指定快照"""
        (
            self._model_provider,
            self._chat_model_service,
            self._llm_task_service,
            self._ai_service
        ) = snapshot




def get_model_provider(request: Request) -> ModelProvider:
    """
    获取模型提供者实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        ModelProvider 实例
    """
    return request.app.state.service_factory.get_model_provider()




def get_chat_model_service(request: Request) -> ChatModelService:
    """
    获取聊天模型服务实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        ChatModelService 实例
    """
    return request.app.state.service_factory.get_chat_model_service()



def get_ai_service(request: Request) -> AIService:
    """
    获取 AI 服务实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        AIService 实例
    """
    return request.app.state.service_factory.get_ai_service()


def get_knowledge_service(request: Request) -> KnowledgeService:
    """
    获取知识库服务实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        KnowledgeService 实例
    """
    return request.app.state.service_factory.get_knowledge_service()




def get_cleanup_service(request: Request) -> SessionCleanupService:
    """
    获取清理服务实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        SessionCleanupService 实例
    """
    return request.app.state.cleanup_service


def get_config(request: Request):
    """
    获取当前配置

    Args:
        request: FastAPI 请求对象

    Returns:
        配置对象
    """
    return request.app.state.config_context.config



def get_rag_service(request: Request):
    """
    获取 RAG 服务实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        RAGService 实例，如果未初始化则返回 None
    """
    return getattr(request.app.state, "rag_service", None)
