"""
配置上下文管理器
负责配置的生命周期管理和监听器通知
"""
from typing import Callable

from .logger import get_logger
from .exceptions import ConfigError

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

        logger.info(f"开始更新配置: obsidian_vault_path={new_config.obsidian_vault_path}, model_name={new_config.model_name}")

        self._updating = True
        try:
            self._config = new_config

            for idx, listener in enumerate(self._listeners):
                listener_name = self._get_listener_name(listener)
                logger.info(f"执行监听器 {idx + 1}/{len(self._listeners)}: {listener_name}")

                listener(new_config)
                logger.info(f"监听器 {listener_name} 执行成功")

        finally:
            self._updating = False

        logger.info("配置更新完成")

    def register_listener(self, listener: Callable[[object], None]) -> None:
        """
        注册配置变更监听器

        Args:
            listener: 监听器函数，接收配置对象参数
        """
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
