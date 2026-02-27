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
        self._listeners: dict[str, Callable[[object], None]] = {}  # 改用字典，支持按名称管理
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
            for idx, (name, listener) in enumerate(self._listeners.items()):
                logger.info(f"执行监听器 {idx + 1}/{len(self._listeners)}: {name}")

                rollback = listener(new_config)
                if callable(rollback):
                    rollback_actions.append((name, rollback))

                logger.info(f"监听器 {name} 执行成功")

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

    def register_listener(
        self,
        listener: Callable[[object], None],
        name: str | None = None
    ) -> str:
        """
        注册配置变更监听器

        Args:
            listener: 监听器函数，接收配置对象参数
            name: 监听器名称（可选，用于取消注册）

        Returns:
            str: 监听器名称

        Raises:
            ConfigError: 监听器已注册时抛出
        """
        listener_name = name or self._get_listener_name(listener)

        if listener_name in self._listeners:
            logger.warning(f"监听器 {listener_name} 已存在，将覆盖")
        else:
            logger.info(f"已注册监听器: {listener_name}")

        self._listeners[listener_name] = listener
        return listener_name

    def unregister_listener(self, name: str) -> bool:
        """
        取消注册监听器

        Args:
            name: 监听器名称

        Returns:
            bool: 是否成功取消注册
        """
        if name in self._listeners:
            del self._listeners[name]
            logger.info(f"已取消注册监听器: {name}")
            return True

        logger.warning(f"监听器 {name} 不存在")
        return False

    def _get_listener_name(self, listener: Callable[[object], None]) -> str:
        """获取监听器名称（用于日志）"""
        if hasattr(listener, '__name__'):
            return listener.__name__
        elif hasattr(listener, 'func'):  # lambda 或 partial
            return listener.func.__name__
        else:
            return type(listener).__name__
