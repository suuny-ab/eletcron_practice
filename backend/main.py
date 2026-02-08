"""
FastAPI 主应用 - 应用初始化和路由注册
"""
from fastapi import FastAPI


# 导入路由模块
from .routes import file_router, ai_router, config_router, knowledge_router

# 导入全局异常处理器
from .core import register_exception_handlers, get_logger

# 导入配置管理器
from .utils.config_manager import config_manager

logger = get_logger(__name__)

app = FastAPI()

# 注册全局异常处理器
register_exception_handlers(app)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("应用启动中...")

    # 尝试从配置文件加载配置
    try:
        config = config_manager.read_config()
        if config:
            logger.info(f"已加载配置: Obsidian Vault={config.obsidian_vault_path}, 模型={config.model_name}")
            # 初始化 AI 服务（会在内部读取配置）
            from .services.ai_service import get_ai_service
            get_ai_service()
        else:
            logger.info("未找到配置文件，请在界面中配置")
    except Exception as e:
        logger.error(f"加载配置失败: {e}")

    logger.info("应用初始化完成")


# 注册路由
app.include_router(file_router, tags=["files"])
app.include_router(ai_router, tags=["AI"])
app.include_router(config_router, tags=["config"])
app.include_router(knowledge_router, tags=["knowledge"])



