"""
应用容器配置
注册所有服务到 DI 容器
"""
from core.container import Container, Lifetime, get_container
from core.interfaces import (
    IConfigContext,
    IModelProvider,
    IChatModelService,
    ILLMTaskService,
    IKnowledgeRepository,
    IKnowledgeService,
)
from infrastructure.config.config_context import ConfigContext
from domain.ai.models.model_provider import ModelProvider
from domain.ai.services.chat_model import ChatModelService
from domain.ai.services.llm_task_service import LLMTaskService
from domain.knowledge.repositories.knowledge_repository import KnowledgeRepository
from domain.knowledge.services.knowledge_service import KnowledgeService
from .services import AIService, SessionCleanupService


def configure_container(container: Container = None) -> Container:
    """
    配置 DI 容器

    Args:
        container: 可选的容器实例，如果不提供则使用默认容器

    Returns:
        配置好的容器
    """
    if container is None:
        container = get_container()

    # 基础设施层 - 单例
    container.register(IConfigContext, ConfigContext, Lifetime.SINGLETON)

    # AI 领域 - 单例（模型加载成本高）
    # 注意：ModelProvider 需要配置参数，在配置更新时重新注册
    container.register(IModelProvider, ModelProvider, Lifetime.SINGLETON)
    container.register(IChatModelService, ChatModelService, Lifetime.SINGLETON)
    container.register(ILLMTaskService, LLMTaskService, Lifetime.SINGLETON)

    # 知识库领域 - 单例
    container.register(IKnowledgeRepository, KnowledgeRepository, Lifetime.SINGLETON)
    container.register(IKnowledgeService, KnowledgeService, Lifetime.SINGLETON)

    # 应用服务 - 单例
    container.register(AIService, AIService, Lifetime.SINGLETON)
    container.register(SessionCleanupService, SessionCleanupService, Lifetime.SINGLETON)

    return container


def create_test_container() -> Container:
    """
    创建测试用容器
    可以注册 Mock 实现，便于单元测试
    """
    # 重置全局容器以确保测试隔离
    from core.container import reset_container
    reset_container()
    
    container = Container()

    # 测试时可以替换为 Mock 实现
    # from tests.mocks import MockModelProvider
    # container.register(IModelProvider, MockModelProvider, Lifetime.SINGLETON)

    # 其他服务使用真实实现
    configure_container(container)

    return container
