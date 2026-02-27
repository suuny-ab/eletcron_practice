"""
核心模块 - 异常处理、日志等基础功能
"""
from .exceptions import (
    BaseBusinessException,
    NotFoundException,
    ValidationException,
    ExternalServiceException,
    ConfigError
)
from .exception_handlers import (
    register_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
    business_exception_handler,
    generic_exception_handler
)


__all__ = [
    # 异常类
    "BaseBusinessException",
    "NotFoundException",
    "ValidationException",
    "ExternalServiceException",
    "ConfigError",
    # 异常处理器
    "register_exception_handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "business_exception_handler",
    "generic_exception_handler",
]
