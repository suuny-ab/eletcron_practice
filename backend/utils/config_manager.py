"""
配置管理模块
负责配置文件的读取、写入和验证
"""
import json
from pathlib import Path
from pydantic import BaseModel, ValidationError

from ..core.exceptions import ConfigError


class ConfigModel(BaseModel):
    """配置数据模型"""
    obsidian_vault_path: str
    api_key: str
    model_name: str


class ConfigManager:
    """配置管理器"""
    
    CONFIG_DIR_NAME = ".myapp"
    CONFIG_FILE_NAME = "config.json"
    
    def __init__(self):
        self.config_dir = Path.home() / self.CONFIG_DIR_NAME
        self.config_file = self.config_dir / self.CONFIG_FILE_NAME
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
    
    def read_config(self) -> ConfigModel | None:
        """
        读取配置文件

        Returns:
            ConfigModel: 配置对象，如果文件不存在则返回 None

        Raises:
            ConfigError: 文件读取失败或配置格式错误时抛出
        """
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ConfigModel(**data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except ValidationError as e:
            raise ConfigError(f"配置数据验证失败: {e}")
        except Exception as e:
            raise ConfigError(f"读取配置文件失败: {e}")
    
    def write_config(self, obsidian_vault_path: str, api_key: str, model_name: str) -> ConfigModel:
        """
        写入配置文件

        Args:
            obsidian_vault_path: Obsidian Vault 绝对路径
            api_key: API密钥
            model_name: 模型名称

        Returns:
            ConfigModel: 保存后的配置对象

        Raises:
            ConfigError: 配置写入失败时抛出
        """
        self._ensure_config_dir()

        try:
            config = ConfigModel(
                obsidian_vault_path=obsidian_vault_path,
                api_key=api_key,
                model_name=model_name
            )
        except ValidationError as e:
            raise ConfigError(f"配置数据验证失败: {e}")

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ConfigError(f"写入配置文件失败: {e}")

        return config
    
    def delete_config(self) -> bool:
        """
        删除配置文件

        Returns:
            bool: 删除是否成功（文件不存在返回False）

        Raises:
            ConfigError: 删除失败时抛出（如权限不足）
        """
        if not self.config_file.exists():
            return False

        try:
            self.config_file.unlink()
            return True
        except Exception as e:
            raise ConfigError(f"删除配置文件失败: {e}")


# 全局配置管理器实例
config_manager = ConfigManager()
