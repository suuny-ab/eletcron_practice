"""
依赖注入 - 提供 FastAPI 依赖函数
使用 DI 容器管理服务实例
"""
from fastapi import Request
from typing import TYPE_CHECKING

from core.container import get_container
from core.interfaces import (
    IConfigContext,
    IModelProvider,
    IChatModelService,
    ILLMTaskService,
    IKnowledgeRepository,
    IKnowledgeService,
)
from .services import AIService, SessionCleanupService

if TYPE_CHECKING:
    from domain.knowledge.rag.rag_service import RAGService


# 从容器解析服务的依赖函数

def get_config_context() -> IConfigContext:
    """获取配置上下文"""
    return get_container().resolve(IConfigContext)


def get_model_provider() -> IModelProvider:
    """获取模型提供者"""
    return get_container().resolve(IModelProvider)


def get_chat_model_service() -> IChatModelService:
    """获取聊天模型服务"""
    return get_container().resolve(IChatModelService)


def get_llm_task_service() -> ILLMTaskService:
    """获取 LLM 任务服务"""
    return get_container().resolve(ILLMTaskService)


def get_knowledge_repository() -> IKnowledgeRepository:
    """获取知识库仓储"""
    return get_container().resolve(IKnowledgeRepository)


def get_knowledge_service() -> IKnowledgeService:
    """获取知识库服务"""
    return get_container().resolve(IKnowledgeService)


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
