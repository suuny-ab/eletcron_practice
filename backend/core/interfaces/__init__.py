"""
核心接口定义模块
提供所有核心组件的抽象接口
"""
from .ai import (
    IModelProvider,
    IChatModelService,
    ILLMTaskService,
)
from .knowledge import (
    IKnowledgeRepository,
    IKnowledgeService,
    IRAGService,
)
from .config import (
    IConfigContext,
    IConfigManager,
)
from .storage import IDocumentProcessor

__all__ = [
    # AI
    "IModelProvider",
    "IChatModelService", 
    "ILLMTaskService",
    # Knowledge
    "IKnowledgeRepository",
    "IKnowledgeService",
    "IRAGService",
    # Config
    "IConfigContext",
    "IConfigManager",
    # Storage
    "IDocumentProcessor",
]
