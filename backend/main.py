"""
FastAPI 主应用 - 应用初始化和路由注册
"""
from fastapi import FastAPI


# 导入路由模块
from .routes import file_router, ai_router

# 导入全局异常处理器
from .core import register_exception_handlers, get_logger

logger = get_logger(__name__)

app = FastAPI()

# 注册全局异常处理器
register_exception_handlers(app)
logger.info("应用初始化完成")

# 注册路由
app.include_router(file_router, tags=["files"])
app.include_router(ai_router, tags=["AI"])



