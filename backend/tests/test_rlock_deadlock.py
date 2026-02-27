"""
测试可重入锁解决死锁问题
"""
import sys
import threading
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.container import Container, Lifetime


def test_nested_resolve_no_deadlock():
        """测试嵌套解析不会死锁"""
        container = Container()

        class ServiceA:
            def __init__(self):
                self.name = "A"

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a
                self.name = "B"

        class ServiceC:
            def __init__(self, b: ServiceB):
                self.b = b
                self.name = "C"

        # 注册服务（都是单例）
        container.register(ServiceA, ServiceA, Lifetime.SINGLETON)
        container.register(ServiceB, ServiceB, Lifetime.SINGLETON)
        container.register(ServiceC, ServiceC, Lifetime.SINGLETON)

        # 解析 ServiceC（会递归解析 ServiceB -> ServiceA）
        # 如果使用 Lock() 会死锁，使用 RLock() 不会
        c = container.resolve(ServiceC)

        assert c.name == "C"
        assert c.b.name == "B"
        assert c.b.a.name == "A"

        # 验证单例
        a = container.resolve(ServiceA)
        assert a is c.b.a

def test_invalidate_and_resolve_no_deadlock():
        """测试失效后重新解析不会死锁"""
        container = Container()

        class Service:
            def __init__(self):
                self.value = "initial"

        container.register(Service, Service, Lifetime.SINGLETON)

        # 首次解析
        s1 = container.resolve(Service)
        assert s1.value == "initial"

        # 失效缓存（会获取 RLock）
        container.invalidate(Service)

        # 重新解析（也会获取 RLock，不会死锁）
        s2 = container.resolve(Service)
        assert s2.value == "initial"
        assert s2 is not s1  # 应该是新实例

def test_concurrent_invalidate_and_resolve():
        """测试并发失效和解析不会死锁"""
        container = Container()

        class Service:
            def __init__(self):
                self.id = id(self)

        container.register(Service, Service, Lifetime.SINGLETON)

        results = []
        lock = threading.Lock()

        def resolve_service():
            try:
                s = container.resolve(Service)
                with lock:
                    results.append(("resolve", s.id))
            except Exception as e:
                with lock:
                    results.append(("error", str(e)))

        def invalidate_service():
            try:
                container.invalidate(Service)
                with lock:
                    results.append(("invalidate", None))
            except Exception as e:
                with lock:
                    results.append(("error", str(e)))

        # 创建多个线程并发执行
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=resolve_service))
            threads.append(threading.Thread(target=invalidate_service))

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成（如果死锁会一直等待）
        for t in threads:
            t.join(timeout=2.0)  # 2秒超时
            assert not t.is_alive(), "线程超时，可能发生死锁"

        # 验证没有错误
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"出现错误: {errors}"



if __name__ == "__main__":
    print("测试 1: 嵌套解析不会死锁")
    test_nested_resolve_no_deadlock()
    print("✓ 通过")

    print("\n测试 2: 失效后重新解析不会死锁")
    test_invalidate_and_resolve_no_deadlock()
    print("✓ 通过")

    print("\n测试 3: 并发失效和解析不会死锁")
    test_concurrent_invalidate_and_resolve()
    print("✓ 通过")

    print("\n所有测试通过！")

