"""
FastAPI 主应用 - 应用初始化和路由注册
"""
from fastapi import FastAPI
from pathlib import Path

# 导入路由模块
from .routes import ai_router, config_router, knowledge_router

# 导入全局异常处理器
from .core import register_exception_handlers, get_logger, ConfigContext

# 导入配置管理器
from .utils.config_manager import config_manager

# 导入 AI 引擎
from .ai_engine import AIEngine

# 导入清理服务
from .services.cleanup_service import set_cleanup_notes_root, get_cleanup_service

logger = get_logger(__name__)

app = FastAPI()

# 注册全局异常处理器
register_exception_handlers(app)

# 创建配置上下文
app.state.config_context = ConfigContext()


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("应用启动中...")

    # 尝试从配置文件加载配置
    try:
        config = config_manager.read_config()
        if config:
            logger.info(f"已加载配置: Obsidian Vault={config.obsidian_vault_path}, 模型={config.model_name}")

            # 注册配置变更监听器
            _register_config_listeners()

            # 更新配置上下文（自动触发所有监听器）
            app.state.config_context.update(config)

            # 启动时自动清理孤儿会话
            if config.obsidian_vault_path:
                cleanup_service = get_cleanup_service()
                cleaned_count = await cleanup_service.cleanup_orphaned_sessions()
                if cleaned_count > 0:
                    logger.info(f"启动时清理了 {cleaned_count} 个孤儿会话")
        else:
            logger.warning("未找到配置文件，请在界面中配置")
            # 初始化一个空的 AI 引擎占位符（配置时会被替换）
            app.state.ai_engine = None
    except Exception as e:
        logger.error(f"加载配置失败: {e}")

    logger.info("应用初始化完成")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用关闭中...")


def _register_config_listeners():
    """注册配置变更监听器"""

    # 监听器 1：更新 AI 引擎（必须先执行）
    def update_ai_engine(config):
        """更新 AI 引擎"""
        app.state.ai_engine = AIEngine(
            api_key=config.api_key,
            model_name=config.model_name or "qwen3-max"
        )

    app.state.config_context.register_listener(update_ai_engine)

    # 监听器 2：更新清理服务的笔记根目录（可以后执行）
    def update_cleanup_notes_root(config):
        """更新清理服务的笔记根目录"""
        if config.obsidian_vault_path:
            set_cleanup_notes_root(Path(config.obsidian_vault_path))

    app.state.config_context.register_listener(update_cleanup_notes_root)


# 注册路由
app.include_router(ai_router, tags=["AI"])
app.include_router(config_router, tags=["config"])
app.include_router(knowledge_router, tags=["knowledge"])



