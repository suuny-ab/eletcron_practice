"""
依赖注入 - 提供 FastAPI 依赖函数
使用 DI 容器管理服务实例
"""
from fastapi import Request

from core.container import get_container
from domain.ai.models.model_provider import ModelProvider
from domain.ai.services.chat_model import ChatModelService
from domain.ai.services.llm_task_service import LLMTaskService
from domain.knowledge.repositories.knowledge_repository import KnowledgeRepository
from .services import AIService, SessionCleanupService
from domain.knowledge.services.knowledge_service import KnowledgeService
from infrastructure.config.config_context import ConfigContext


# 从容器解析服务的依赖函数

def get_config_context() -> ConfigContext:
    """获取配置上下文"""
    return get_container().resolve(ConfigContext)


def get_model_provider() -> ModelProvider:
    """获取模型提供者"""
    return get_container().resolve(ModelProvider)


def get_chat_model_service() -> ChatModelService:
    """获取聊天模型服务"""
    return get_container().resolve(ChatModelService)


def get_llm_task_service() -> LLMTaskService:
    """获取 LLM 任务服务"""
    return get_container().resolve(LLMTaskService)


def get_knowledge_repository() -> KnowledgeRepository:
    """获取知识库仓储"""
    return get_container().resolve(KnowledgeRepository)


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务"""
    return get_container().resolve(KnowledgeService)


def get_ai_service() -> AIService:
    """获取 AI 服务"""
    return get_container().resolve(AIService)


def get_session_cleanup_service() -> SessionCleanupService:
    """获取会话清理服务"""
    return get_container().resolve(SessionCleanupService)


def get_rag_service(request: Request):
    """获取 RAG 服务"""
    return getattr(request.app.state, "rag_service", None)


# 保持向后兼容
ServiceFactory = None  # 标记为已弃用
