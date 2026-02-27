"""
配置上下文管理器
负责配置的生命周期管理和监听器通知
"""
from typing import Callable

from ..logging.logger import get_logger
from core.exceptions import ConfigError

logger = get_logger(__name__)


class ConfigContext:
    """配置上下文管理器"""

    def __init__(self):
        self._config: object | None = None
        self._listeners: list[Callable[[object], None]] = []
        self._updating = False

    @property
    def config(self) -> object:
        """获取当前配置"""
        if not self._config:
            raise ConfigError("配置未初始化")
        return self._config

    def update(self, new_config: object) -> None:
        """
        更新配置并通知所有监听器

        Args:
            new_config: 新的配置对象

        Raises:
            ConfigError: 监听器执行失败或检测到循环依赖时抛出
        """
        # 防止在监听器中递归更新配置
        if self._updating:
            raise ConfigError("不允许在监听器中更新配置（防止循环依赖）")

        vault_path = getattr(new_config, 'obsidian_vault_path', '')
        model_name = getattr(new_config, 'model_name', '')
        logger.info(f"开始更新配置: obsidian_vault_path={vault_path}, model_name={model_name}")

        self._updating = True
        rollback_actions: list[tuple[str, Callable[[], None]]] = []
        old_config = self._config

        try:
            for idx, listener in enumerate(self._listeners):
                listener_name = self._get_listener_name(listener)
                logger.info(f"执行监听器 {idx + 1}/{len(self._listeners)}: {listener_name}")

                rollback = listener(new_config)
                if callable(rollback):
                    rollback_actions.append((listener_name, rollback))

                logger.info(f"监听器 {listener_name} 执行成功")

            self._config = new_config
            logger.info("配置更新完成")
        except Exception as e:
            logger.error(f"配置更新失败: {e}，开始回滚")

            for listener_name, rollback in reversed(rollback_actions):
                try:
                    rollback()
                    logger.info(f"回滚成功: {listener_name}")
                except Exception as rollback_error:
                    logger.error(f"回滚失败: {listener_name} - {rollback_error}")

            self._config = old_config

            if isinstance(e, ConfigError):
                raise
            raise ConfigError(f"监听器执行失败: {e}") from e
        finally:
            self._updating = False

    def register_listener(self, listener: Callable[[object], None]) -> None:
        """
        注册配置变更监听器

        Args:
            listener: 监听器函数，接收配置对象参数

        Raises:
            ConfigError: 监听器已注册时抛出
        """
        if listener in self._listeners:
            listener_name = self._get_listener_name(listener)
            logger.warning(f"监听器 {listener_name} 已存在，跳过注册")
            return

        self._listeners.append(listener)
        logger.info(f"已注册监听器: {self._get_listener_name(listener)}")

    def _get_listener_name(self, listener: Callable[[object], None]) -> str:
        """获取监听器名称（用于日志）"""
        if hasattr(listener, '__name__'):
            return listener.__name__
        elif hasattr(listener, 'func'):  # lambda 或 partial
            return listener.func.__name__
        else:
            return type(listener).__name__
