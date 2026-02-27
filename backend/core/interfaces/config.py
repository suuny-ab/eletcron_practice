"""
配置相关接口定义
"""
from typing import Protocol, Callable, Any, runtime_checkable


@runtime_checkable
class IConfigContext(Protocol):
    """配置上下文接口"""

    @property
    def config(self) -> Any:
        """获取当前配置"""
        ...

    def update(self, new_config: Any, persist: bool = True) -> None:
        """更新配置（默认持久化）"""
        ...

    def read_config(self, config_class: type) -> Any:
        """从磁盘读取配置"""
        ...

    def build_config(
        self,
        config_class: type,
        obsidian_vault_path: str,
        api_key: str,
        model_name: str,
        prompts: dict | None = None
    ) -> Any:
        """构建配置对象"""
        ...

    def delete_config(self) -> bool:
        """删除配置文件"""
        ...

    def register_listener(
        self,
        listener: Callable[[Any], Callable[[], None]],
        name: str | None = None
    ) -> str:
        """注册配置变更监听器，返回监听器名称"""
        ...

    def unregister_listener(self, name: str) -> bool:
        """取消注册监听器"""
        ...
