"""
核心模块 - 异常处理、日志等基础功能
"""
from .exceptions import (
    BaseBusinessException,
    NotFoundException,
    ValidationException,
    ExternalServiceException
)
from .exception_handlers import (
    register_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
    business_exception_handler,
    generic_exception_handler
)
from .logger import setup_logging, get_logger

__all__ = [
    # 异常类
    "BaseBusinessException",
    "NotFoundException",
    "ValidationException",
    "ExternalServiceException",
    # 异常处理器
    "register_exception_handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "business_exception_handler",
    "generic_exception_handler",
    # 日志
    "setup_logging",
    "get_logger",
]
