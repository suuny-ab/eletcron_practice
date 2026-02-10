"""
依赖注入 - 提供 FastAPI 依赖函数
"""
from fastapi import Request

from ..ai_engine import AIEngine
from ..services import AIService, SessionCleanupService
from ..utils.config_manager import config_manager


def get_ai_engine(request: Request) -> AIEngine:
    """
    获取 AI 引擎实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        AIEngine 实例
    """
    return request.app.state.ai_engine


def get_ai_service(request: Request) -> AIService:
    """
    获取 AI 服务实例（单例）

    Args:
        request: FastAPI 请求对象

    Returns:
        AIService 实例
    """
    return request.app.state.ai_service


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
    return config_manager.read_config()
