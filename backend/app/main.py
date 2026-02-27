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

# 导入配置管理器
from infrastructure.config.config_manager import config_manager

# 导入模型提供者（具体实现）
from domain.ai.models.model_provider import ModelProvider

# 导入 AI 服务
from .services.ai_service import AIService


# 导入清理服务
from .services.cleanup_service import SessionCleanupService


# 导入容器配置
from .container_config import configure_container
from core.container import get_container
from core.interfaces import (
    IConfigContext, 
    IModelProvider, 
    IChatModelService,
    ILLMTaskService
)


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")
    
    # 初始化 DI 容器
    configure_container()
    container = get_container()

    # 获取清理服务
    app.state.cleanup_service = container.resolve(SessionCleanupService)

    # 获取配置上下文
    app.state.config_context = container.resolve(IConfigContext)
    
    # 注册配置变更监听器
    _register_config_listeners(app)
    
    # 尝试从配置文件加载配置
    try:
        config = config_manager.read_config()
        if config:
            logger.info(f"已加载配置: Obsidian Vault={config.obsidian_vault_path}, 模型={config.model_name}")
            
            # 更新配置上下文（自动触发所有监听器）
            app.state.config_context.update(config)
            
            # 启动时自动清理孤儿会话
            if config.obsidian_vault_path:
                cleaned_count = await app.state.cleanup_service.cleanup_orphaned_sessions()
                if cleaned_count > 0:
                    logger.info(f"启动时清理了 {cleaned_count} 个孤儿会话")
        else:
            logger.warning("未找到配置文件，请在界面中配置")
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
    
    logger.info("应用初始化完成")
    
    yield  # 应用运行中
    
    # 关闭时执行
    logger.info("应用关闭中...")


# 创建 FastAPI 应用并使用 lifespan
app = FastAPI(lifespan=lifespan)

# 注册全局异常处理器
register_exception_handlers(app)


def _register_config_listeners(app: FastAPI):
    """注册配置变更监听器"""
    container = get_container()
    
    # 监听器 1：创建/更新 ModelProvider（必须最先执行）
    def configure_models(config):
        """创建/更新模型提供者"""
        # 重新注册 ModelProvider 实例
        model_provider = ModelProvider(
            api_key=config.api_key,
            model_name=config.model_name or "qwen-max"
        )
        container.register_instance(IModelProvider, model_provider)

        # 级联失效依赖 ModelProvider 的服务
        # 确保下次解析时创建新实例，使用新的 ModelProvider
        container.invalidate(IChatModelService)
        container.invalidate(ILLMTaskService)
        logger.info("已失效依赖 ModelProvider 的服务缓存")

        return lambda: None  # 简单的回滚函数

    app.state.config_context.register_listener(configure_models)
    
    # 监听器 2：更新提示词配置
    def update_prompts(config):
        """更新提示词配置"""
        from prompts.prompt_config import PromptConfigFactory
        previous_custom_prompts = PromptConfigFactory.snapshot_custom_configs()
        
        if hasattr(config, 'prompts') and config.prompts:
            PromptConfigFactory.update_configs(config.prompts)
        
        def rollback():
            PromptConfigFactory.restore_custom_configs(previous_custom_prompts)
        
        return rollback
    
    app.state.config_context.register_listener(update_prompts)
    
    # 监听器 3：更新 AI 服务
    def update_ai_service(_config):
        """更新 AI 服务"""
        # 从容器获取最新的 AI 服务
        app.state.ai_service = container.resolve(AIService)
        return lambda: None
    
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
    
    # 监听器 5：初始化 RAG 服务
    def init_rag_service(config):
        """初始化 RAG 服务"""
        from domain.knowledge.rag.rag_service import RAGService
        from infrastructure.storage.file_watcher import FileWatcher

        previous_rag_service = getattr(app.state, "rag_service", None)

        if config.obsidian_vault_path:
            vault_path = Path(config.obsidian_vault_path)
            file_watcher = FileWatcher(vault_path)

            app.state.rag_service = RAGService(
                model_provider=container.resolve(IModelProvider),
                notes_root=str(vault_path),
                llm_task_service=container.resolve(ILLMTaskService),
            )

            # 启动文件监听器
            app.state.rag_service.start_watcher()
            logger.info(f"RAG服务已初始化: {vault_path}")

        def rollback():
            if app.state.rag_service:
                app.state.rag_service.stop_watcher()
            app.state.rag_service = previous_rag_service

        return rollback

    app.state.config_context.register_listener(init_rag_service)


# 注册路由
app.include_router(ai_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}
