"""
统一异常处理工具 - 提供一致的异常日志记录逻辑
"""
from .logger import get_logger
from .exceptions import BaseBusinessException

logger = get_logger(__name__)


def log_exception(exception: Exception, context: str) -> None:
    """
    统一的异常日志记录

    Args:
        exception: 异常对象
        context: 异常发生上下文信息（如请求路径、生成器名称等）
    """
    error_type = type(exception).__name__
    error_module = type(exception).__module__

    # 业务异常用 warning 级别（所有继承自 BaseBusinessException 的异常）
    if isinstance(exception, BaseBusinessException):
        logger.warning(f"{context} | {error_type}: {str(exception)}")
    else:
        # 系统异常用 error 级别 + 堆栈信息
        logger.error(
            f"{context} | {error_type}: {str(exception)} | 模块: {error_module}",
            exc_info=True
        )
