"""
轻量级依赖注入容器
提供服务的注册、解析和生命周期管理
"""
from typing import TypeVar, Type, Callable, Any, Dict, Optional, Set
from enum import Enum, auto
import threading
from infrastructure.logging.logger import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


class Lifetime(Enum):
    """服务生命周期"""
    TRANSIENT = auto()  # 每次解析创建新实例
    SCOPED = auto()     # 同一作用域内共享实例
    SINGLETON = auto()  # 全局单例


class ServiceDescriptor:
    """服务描述符"""
    
    def __init__(
        self,
        interface: Type,
        implementation: Type | Callable,
        lifetime: Lifetime = Lifetime.TRANSIENT
    ):
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.instance: Any = None  # 用于单例和作用域实例


class Container:
    """
    依赖注入容器（线程安全）
    
    示例:
        container = Container()
        
        # 注册服务
        container.register(ConfigContext, ConfigContext, Lifetime.SINGLETON)
        container.register(ModelProvider, ModelProvider, Lifetime.SINGLETON)
        container.register(ChatModelService, ChatModelService, Lifetime.SINGLETON)
        
        # 解析服务
        config = container.resolve(ConfigContext)
        model = container.resolve(ModelProvider)
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singleton_instances: Dict[Type, Any] = {}
        self._instance_lock = threading.Lock()  # 保护单例实例创建
        self._registration_lock = threading.Lock()  # 保护服务注册
    
    def register(
        self,
        interface: Type[T],
        implementation: Type[T] | Callable[..., T],
        lifetime: Lifetime = Lifetime.TRANSIENT
    ) -> "Container":
        """
        注册服务（线程安全）

        Args:
            interface: 服务接口（可以是抽象类或协议）
            implementation: 实现类或工厂函数
            lifetime: 生命周期

        Returns:
            self，支持链式调用
        """
        with self._registration_lock:
            self._services[interface] = ServiceDescriptor(
                interface, implementation, lifetime
            )
        return self
    
    def register_instance(self, interface: Type[T], instance: T) -> "Container":
        """
        注册已有实例（用于单例，线程安全）

        Args:
            interface: 服务接口
            instance: 实例对象
        """
        with self._registration_lock:
            descriptor = ServiceDescriptor(interface, lambda: instance, Lifetime.SINGLETON)
            descriptor.instance = instance
            self._services[interface] = descriptor
            self._singleton_instances[interface] = instance
        return self
    
    def resolve(self, interface: Type[T]) -> T:
        """
        解析服务（线程安全）

        Args:
            interface: 服务接口

        Returns:
            服务实例

        Raises:
            KeyError: 服务未注册
        """
        if interface not in self._services:
            raise KeyError(f"服务未注册: {interface.__name__}")

        descriptor = self._services[interface]

        # 单例模式（线程安全）
        if descriptor.lifetime == Lifetime.SINGLETON:
            # 使用双重检查锁定模式
            if descriptor.instance is None:
                with self._instance_lock:
                    if descriptor.instance is None:
                        descriptor.instance = self._create_instance(descriptor)
                        self._singleton_instances[interface] = descriptor.instance
            return descriptor.instance

        # 瞬态模式（每次创建新实例）
        return self._create_instance(descriptor)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建实例，自动注入依赖"""
        implementation = descriptor.implementation
        
        # 如果是工厂函数，直接调用
        if callable(implementation) and not isinstance(implementation, type):
            return implementation()
        
        # 如果是类，尝试自动注入构造函数参数
        import inspect
        sig = inspect.signature(implementation.__init__)
        params = list(sig.parameters.items())[1:]  # 排除 self
        
        kwargs = {}
        for name, param in params:
            if param.annotation != inspect.Parameter.empty:
                # 根据类型注解解析依赖
                try:
                    kwargs[name] = self.resolve(param.annotation)
                except KeyError:
                    if param.default != inspect.Parameter.empty:
                        kwargs[name] = param.default
                    else:
                        raise
        
        return implementation(**kwargs)
    
    def is_registered(self, interface: Type) -> bool:
        """检查服务是否已注册"""
        return interface in self._services

    def invalidate(self, interface: Type[T]) -> bool:
        """
        使服务的单例缓存失效（线程安全）

        用于配置更新时清除依赖服务的缓存，强制下次解析时重新创建实例。

        Args:
            interface: 服务接口

        Returns:
            bool: 是否成功失效（如果服务不存在返回 False）
        """
        with self._instance_lock:
            if interface not in self._services:
                return False

            descriptor = self._services[interface]

            # 清除单例缓存
            if descriptor.instance is not None:
                logger.debug(f"失效单例缓存: {interface.__name__}")
                descriptor.instance = None

            if interface in self._singleton_instances:
                del self._singleton_instances[interface]

            return True

    def invalidate_all(self) -> None:
        """
        使所有单例缓存失效（线程安全）

        用于应用关闭或完全重置容器时清理所有实例。
        """
        with self._instance_lock:
            logger.debug("失效所有单例缓存")
            for descriptor in self._services.values():
                descriptor.instance = None
            self._singleton_instances.clear()

    def create_scope(self) -> "Scope":
        """创建作用域（用于 Scoped 生命周期）"""
        return Scope(self)


class Scope:
    """作用域 - 管理 Scoped 生命周期的服务"""
    
    def __init__(self, container: Container):
        self._container = container
        self._scoped_instances: Dict[Type, Any] = {}
    
    def resolve(self, interface: Type[T]) -> T:
        """在作用域内解析服务"""
        descriptor = self._container._services.get(interface)
        
        if descriptor is None:
            raise KeyError(f"服务未注册: {interface.__name__}")
        
        if descriptor.lifetime == Lifetime.SCOPED:
            if interface not in self._scoped_instances:
                self._scoped_instances[interface] = self._container._create_instance(descriptor)
            return self._scoped_instances[interface]
        
        # 其他生命周期委托给容器
        return self._container.resolve(interface)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出作用域时清理"""
        self._scoped_instances.clear()


# 全局容器实例（线程安全）
_default_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """
    获取默认容器（线程安全）

    使用双重检查锁定模式确保多线程环境下只创建一个容器实例。

    Returns:
        Container: 默认容器实例
    """
    global _default_container
    if _default_container is None:
        with _container_lock:
            if _default_container is None:
                logger.debug("创建默认容器实例")
                _default_container = Container()
    return _default_container


def set_container(container: Container) -> None:
    """
    设置默认容器（线程安全）

    Args:
        container: 要设置的容器实例
    """
    global _default_container
    with _container_lock:
        logger.debug("设置新的默认容器实例")
        _default_container = container


def reset_container() -> None:
    """
    重置默认容器（线程安全）

    用于测试环境清理，使全局容器失效并创建新容器。
    """
    global _default_container
    with _container_lock:
        if _default_container is not None:
            logger.debug("重置默认容器")
            _default_container.invalidate_all()
        _default_container = None
