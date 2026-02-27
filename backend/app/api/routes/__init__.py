"""
路由层模块
定义API路由
"""
from .ai_routes import router as ai_router
from .config_routes import router as config_router
from .knowledge_routes import router as knowledge_router
from .health_routes import router as health_router

__all__ = ['ai_router', 'config_router', 'knowledge_router', 'health_router']
