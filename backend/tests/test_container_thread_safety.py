"""
容器线程安全测试
"""
import threading
import pytest
from core.container import (
    Container, 
    get_container, 
    set_container, 
    reset_container,
    Lifetime
)
from core.interfaces import IModelProvider


class TestContainerThreadSafety:
    """容器线程安全测试"""

    def setup_method(self):
        """每个测试方法前重置容器"""
        reset_container()

    def teardown_method(self):
        """每个测试方法后清理容器"""
        reset_container()

    def test_singleton_creation_thread_safety(self):
        """测试单例创建的线程安全性"""
        container = Container()
        call_count = 0
        call_lock = threading.Lock()

        class TestService:
            def __init__(self):
                nonlocal call_count
                with call_lock:
                    call_count += 1

        container.register(TestService, TestService, Lifetime.SINGLETON)

        # 创建多个线程同时解析服务
        threads = []
        instances = []
        instances_lock = threading.Lock()

        def resolve_service():
            instance = container.resolve(TestService)
            with instances_lock:
                instances.append(instance)

        # 启动 10 个线程同时解析
        for _ in range(10):
            thread = threading.Thread(target=resolve_service)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证只创建了一个实例
        assert call_count == 1, f"应该只创建一个实例，但创建了 {call_count} 个"
        assert len(instances) == 10
        assert all(instance is instances[0] for instance in instances), "所有实例应该是同一个对象"

    def test_get_container_thread_safety(self):
        """测试全局容器获取的线程安全性"""
        containers = []
        containers_lock = threading.Lock()

        def get_container_instance():
            container = get_container()
            with containers_lock:
                containers.append(container)

        # 启动 10 个线程同时获取容器
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_container_instance)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有线程获取到同一个容器实例
        assert len(containers) == 10
        assert all(container is containers[0] for container in containers), "所有线程应该获取同一个容器实例"

    def test_invalidate_method(self):
        """测试单例缓存失效方法"""
        container = Container()
        create_count = 0
        create_lock = threading.Lock()

        class TestService:
            def __init__(self):
                nonlocal create_count
                with create_lock:
                    create_count += 1

        container.register(TestService, TestService, Lifetime.SINGLETON)

        # 第一次解析
        instance1 = container.resolve(TestService)
        assert create_count == 1

        # 第二次解析（应该返回缓存）
        instance2 = container.resolve(TestService)
        assert create_count == 1
        assert instance1 is instance2

        # 失效缓存
        result = container.invalidate(TestService)
        assert result is True

        # 第三次解析（应该创建新实例）
        instance3 = container.resolve(TestService)
        assert create_count == 2
        assert instance3 is not instance1

    def test_invalidate_all_method(self):
        """测试失效所有单例缓存"""
        container = Container()

        class ServiceA:
            pass

        class ServiceB:
            pass

        container.register(ServiceA, ServiceA, Lifetime.SINGLETON)
        container.register(ServiceB, ServiceB, Lifetime.SINGLETON)

        # 解析服务
        a1 = container.resolve(ServiceA)
        b1 = container.resolve(ServiceB)

        # 失效所有
        container.invalidate_all()

        # 再次解析应该创建新实例
        a2 = container.resolve(ServiceA)
        b2 = container.resolve(ServiceB)

        assert a2 is not a1
        assert b2 is not b1

    def test_invalidate_non_existent_service(self):
        """测试失效不存在的服务"""
        container = Container()
        result = container.invalidate(object)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
