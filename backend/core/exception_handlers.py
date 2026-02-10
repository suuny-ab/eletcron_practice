"""
全局异常处理器 - 统一处理所有异常
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .exceptions import BaseBusinessException
from ..schemas.responses import ErrorResponse
from .logger import get_logger
from .error_handler import log_exception

logger = get_logger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTPException 异常

    Args:
        request: 请求对象
        exc: HTTP异常

    Returns:
        JSONResponse: 错误响应
    """
    log_exception(exc, f"HTTP异常 {exc.status_code} | 路径: {request.url.path}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理 Pydantic 请求验证异常

    Args:
        request: 请求对象
        exc: 验证异常

    Returns:
        JSONResponse: 错误响应
    """
    log_exception(exc, f"请求参数验证失败 | 路径: {request.url.path}")

    # 提取第一个错误信息
    error_detail = exc.errors()[0]
    field = " -> ".join(str(loc) for loc in error_detail["loc"])
    message = f"参数 '{field}' {error_detail['msg']}"

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            success=False,
            message=message,
            error_code="VALIDATION_ERROR"
        ).model_dump()
    )


async def business_exception_handler(request: Request, exc: BaseBusinessException):
    """
    处理自定义业务异常

    Args:
        request: 请求对象
        exc: 业务异常

    Returns:
        JSONResponse: 错误响应
    """
    log_exception(exc, f"业务异常 | 错误码: {exc.error_code} | 路径: {request.url.path}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    处理所有未捕获的通用异常

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSONResponse: 错误响应
    """
    log_exception(exc, f"未捕获的异常 | 路径: {request.url.path}")

    # 生产环境不返回详细错误信息，开发环境返回
    from ..main import app
    is_dev = app.debug

    message = "服务器内部错误" if not is_dev else str(exc)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message=message,
            error_code="INTERNAL_SERVER_ERROR"
        ).model_dump()
    )


def register_exception_handlers(app):
    """
    注册所有异常处理器到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    # 注册业务异常处理器
    app.add_exception_handler(BaseBusinessException, business_exception_handler)

    # 注册HTTP异常处理器
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 注册请求验证异常处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # 注册通用异常处理器（必须最后注册，作为兜底）
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("全局异常处理器注册完成")
