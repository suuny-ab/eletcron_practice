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
    
    def update(self, new_config: Any) -> None:
        """更新配置"""
        ...
    
    def register_listener(
        self, 
        listener: Callable[[Any], Callable[[], None]]
    ) -> None:
        """注册配置变更监听器"""
        ...


@runtime_checkable
class IConfigManager(Protocol):
    """配置管理器接口"""
    
    def read_config(self):
        """读取配置"""
        ...
    
    def save_config(self, config) -> None:
        """保存配置"""
        ...
    
    def delete_config(self) -> bool:
        """删除配置"""
        ...
