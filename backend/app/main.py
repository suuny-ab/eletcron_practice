"""
FastAPI 主应用 - 应用初始化和路由注册
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pathlib import Path

# 导入路由模块
from .api.routes import ai_router, config_router, knowledge_router


# 导入全局异常处理器
from core import register_exception_handlers
from infrastructure.logging.logger import get_logger
from infrastructure.config.config_context import ConfigContext

# 导入配置管理器
from infrastructure.config.config_manager import config_manager

# 导入模型提供者
from domain.ai.models.model_provider import ModelProvider

# 导入 AI 服务
from .services.ai_service import AIService
from .dependencies import ServiceFactory


# 导入清理服务
from .services.cleanup_service import SessionCleanupService



logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")

    # 初始化清理服务单例
    app.state.cleanup_service = SessionCleanupService()

    # 初始化服务工厂
    app.state.service_factory = ServiceFactory()

    # 创建配置上下文
    app.state.config_context = ConfigContext()
    app.state.service_factory.set_config_context(app.state.config_context)


    # 注册配置变更监听器

    _register_config_listeners(app)

    # 尝试从配置文件加载配置
    try:
        config = config_manager.read_config()
        if config:
            logger.info(f"已加载配置: Obsidian Vault={config.obsidian_vault_path}, 模型={config.model_name}")

            # 更新配置上下文（自动触发所有监听器，创建 ModelProvider、AIService、RAGService）
            app.state.config_context.update(config)

            # 启动时自动清理孤儿会话
            if config.obsidian_vault_path:
                cleaned_count = await app.state.cleanup_service.cleanup_orphaned_sessions()
                if cleaned_count > 0:
                    logger.info(f"启动时清理了 {cleaned_count} 个孤儿会话")
        else:
            logger.warning("未找到配置文件，请在界面中配置")
            app.state.model_provider = None
            app.state.ai_service = None
    except Exception as e:
        logger.error(f"加载配置失败: {e}")

    logger.info("应用初始化完成")

    yield  # 应用运行中

    # 关闭时执行
    logger.info("应用关闭中...")

    # 停止RAG服务文件监听器
    if hasattr(app.state, "rag_service") and app.state.rag_service:
        app.state.rag_service.stop_watcher()
        logger.info("RAG服务文件监听器已停止")


# 创建 FastAPI 应用并使用 lifespan
app = FastAPI(lifespan=lifespan)

# 注册全局异常处理器
register_exception_handlers(app)


def _register_config_listeners(app: FastAPI):
    """注册配置变更监听器"""

    # 监听器 1：创建/更新 ModelProvider（必须最先执行）
    def configure_models(config):
        """创建/更新模型提供者"""
        previous_factory_snapshot = app.state.service_factory.snapshot()
        previous_ai_service = getattr(app.state, "ai_service", None)

        app.state.service_factory.set_model_provider(
            ModelProvider(
                api_key=config.api_key,
                model_name=config.model_name or "qwen-max"
            )
        )

        def rollback():
            app.state.service_factory.restore(previous_factory_snapshot)
            app.state.ai_service = previous_ai_service

        return rollback


    app.state.config_context.register_listener(configure_models)

    # 监听器 2：更新提示词配置
    def update_prompts(config):
        """更新提示词配置"""
        from ..prompts.prompt_config import PromptConfigFactory
        previous_custom_prompts = PromptConfigFactory.snapshot_custom_configs()

        if hasattr(config, 'prompts') and config.prompts:
            PromptConfigFactory.update_configs(config.prompts)

        def rollback():
            PromptConfigFactory.restore_custom_configs(previous_custom_prompts)

        return rollback

    app.state.config_context.register_listener(update_prompts)

    # 监听器 3：创建/更新 ChatModelService 和 AIService
    def update_ai_service(_config):
        """更新 AI 服务"""
        previous_ai_service = getattr(app.state, "ai_service", None)
        app.state.ai_service = app.state.service_factory.get_ai_service()

        def rollback():
            app.state.ai_service = previous_ai_service

        return rollback


    app.state.config_context.register_listener(update_ai_service)

    # 监听器 4：更新清理服务的笔记根目录
    def update_cleanup_notes_root(config):
        """更新清理服务的笔记根目录"""
        previous_notes_root = getattr(app.state.cleanup_service, "notes_root", None)
        if config.obsidian_vault_path:
            app.state.cleanup_service.notes_root = Path(config.obsidian_vault_path)

        def rollback():
            app.state.cleanup_service.notes_root = previous_notes_root

        return rollback

    app.state.config_context.register_listener(update_cleanup_notes_root)

    # 监听器 5：更新 RAG 服务


    def update_rag_service(config):
        """更新 RAG 服务"""
        from ..domain.knowledge.rag import RAGService

        previous_rag_service = getattr(app.state, "rag_service", None)

        # 停止旧的RAG服务
        if previous_rag_service:
            previous_rag_service.stop_watcher()

        # 创建新的RAG服务
        if config.obsidian_vault_path and config.api_key:
            try:
                app.state.rag_service = RAGService(
                    model_provider=app.state.service_factory.get_model_provider(),
                    notes_root=config.obsidian_vault_path,
                    llm_task_service=app.state.service_factory.get_llm_task_service()
                )




                app.state.rag_service.start_watcher()
                app.state.rag_service.start_indexing()
                logger.info("RAG服务已初始化并启动文件监听")

            except Exception as e:
                logger.error(f"RAG服务初始化失败: {e}")
                app.state.rag_service = None
        else:
            app.state.rag_service = None

        def rollback():
            current_service = getattr(app.state, "rag_service", None)
            if current_service and current_service is not previous_rag_service:
                current_service.stop_watcher()
            app.state.rag_service = previous_rag_service
            if previous_rag_service:
                previous_rag_service.start_watcher()

        return rollback

    app.state.config_context.register_listener(update_rag_service)



# 注册路由
app.include_router(ai_router, tags=["AI"])
app.include_router(config_router, tags=["config"])
app.include_router(knowledge_router, tags=["knowledge"])




