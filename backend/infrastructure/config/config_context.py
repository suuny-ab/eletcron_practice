"""
配置模块
包含配置数据模型和配置上下文管理器
"""
import json
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field, ValidationError

from ..logging.logger import get_logger
from core.exceptions import ConfigError

logger = get_logger(__name__)


class ConfigModel(BaseModel):
    """配置数据模型"""
    obsidian_vault_path: str
    api_key: str
    model_name: str
    prompts: dict[str, dict[str, str]] = Field(default_factory=dict)  # 提示词配置 {task_type: {system, human}}


class ConfigContext:
    """
    配置上下文管理器
    
    统一管理配置的运行时状态、监听器通知和持久化
    """

    CONFIG_DIR_NAME = ".myapp"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self):
        self._config: object | None = None
        self._listeners: dict[str, Callable[[object], None]] = {}
        self._updating = False
        
        # 配置文件路径
        self._config_dir = Path.home() / self.CONFIG_DIR_NAME
        self._config_file = self._config_dir / self.CONFIG_FILE_NAME
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        if not self._config_dir.exists():
            self._config_dir.mkdir(parents=True)

    @property
    def config(self) -> object:
        """获取当前配置"""
        if not self._config:
            raise ConfigError("配置未初始化")
        return self._config

    def update(self, new_config: object, persist: bool = True) -> None:
        """
        更新配置并通知所有监听器

        Args:
            new_config: 新的配置对象
            persist: 是否持久化到磁盘（默认 True）

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
        old_config_persisted = False

        try:
            # 如果需要持久化，先保存到磁盘
            if persist:
                old_config_persisted = self._config_file.exists()
                self._save_to_disk(new_config)

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

            # 回滚持久化
            if persist:
                try:
                    if old_config_persisted and old_config:
                        self._save_to_disk(old_config)
                    elif self._config_file.exists():
                        self._config_file.unlink()
                except Exception as persist_error:
                    logger.error(f"回滚持久化失败: {persist_error}")

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

    def read_config(self, config_class: type) -> object | None:
        """
        从磁盘读取配置

        Args:
            config_class: 配置类（Pydantic Model）

        Returns:
            配置对象，如果文件不存在则返回 None

        Raises:
            ConfigError: 文件读取失败或配置格式错误时抛出
        """
        if not self._config_file.exists():
            return None

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return config_class(**data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except ValidationError as e:
            raise ConfigError(f"配置数据验证失败: {e}")
        except Exception as e:
            raise ConfigError(f"读取配置文件失败: {e}")

    def build_config(
        self,
        config_class: type,
        obsidian_vault_path: str,
        api_key: str,
        model_name: str,
        prompts: dict | None = None
    ) -> object:
        """
        构建配置对象（不写入磁盘）

        Args:
            config_class: 配置类（Pydantic Model）
            obsidian_vault_path: Obsidian Vault 路径
            api_key: API 密钥
            model_name: 模型名称
            prompts: 提示词配置（可选）

        Returns:
            配置对象

        Raises:
            ConfigError: 配置数据验证失败时抛出
        """
        try:
            config_data = {
                "obsidian_vault_path": obsidian_vault_path,
                "api_key": api_key,
                "model_name": model_name
            }
            if prompts is not None:
                config_data["prompts"] = prompts
            return config_class(**config_data)
        except ValidationError as e:
            raise ConfigError(f"配置数据验证失败: {e}")

    def delete_config(self) -> bool:
        """
        删除配置文件

        Returns:
            bool: 是否成功删除（文件不存在返回 False）
        """
        if not self._config_file.exists():
            return False

        try:
            self._config_file.unlink()
            self._config = None
            return True
        except Exception as e:
            raise ConfigError(f"删除配置文件失败: {e}")

    def _save_to_disk(self, config: object) -> None:
        """保存配置到磁盘"""
        self._ensure_config_dir()

        try:
            if hasattr(config, 'model_dump'):
                data = config.model_dump()
            elif hasattr(config, 'dict'):
                data = config.dict()
            else:
                data = config.__dict__

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ConfigError(f"写入配置文件失败: {e}")

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
