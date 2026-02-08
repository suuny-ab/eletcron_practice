"""
自定义异常类 - 定义业务异常类型
"""
from typing import Optional


class BaseBusinessException(Exception):
    """
    基础业务异常类

    所有业务异常都应继承此类
    """
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class NotFoundException(BaseBusinessException):
    """资源不存在异常"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message=message, error_code=error_code, status_code=404)


class ValidationException(BaseBusinessException):
    """数据验证失败异常"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message=message, error_code=error_code, status_code=422)


class ExternalServiceException(BaseBusinessException):
    """外部服务异常"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message=message, error_code=error_code, status_code=502)


class ConfigError(BaseBusinessException):
    """配置相关异常"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message=message, error_code=error_code, status_code=500)
