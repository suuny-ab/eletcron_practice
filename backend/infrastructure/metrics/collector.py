"""
指标收集器
收集系统运行时的关键指标
"""
import time
from threading import Lock
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CounterMetric:
    """计数器指标"""
    value: int = 0
    last_updated: float = 0.0


@dataclass
class HistogramMetric:
    """直方图指标（记录耗时分布）"""
    count: int = 0
    total: float = 0.0
    min_value: float = float('inf')
    max_value: float = 0.0
    last_updated: float = 0.0

    @property
    def avg(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total / self.count


class MetricsCollector:
    """
    指标收集器（线程安全）

    支持的指标类型：
    - Counter: 计数器，用于统计次数（如请求次数、错误次数）
    - Histogram: 直方图，用于统计分布（如耗时分布）

    使用示例：
        metrics = get_metrics()

        # 计数器
        metrics.increment("rag.index.files_indexed", 10)
        metrics.increment("llm.calls", 1)

        # 直方图（耗时）
        with metrics.timer("rag.index.duration"):
            # ... 执行操作
            pass

        # 获取指标快照
        snapshot = metrics.get_snapshot()
    """

    def __init__(self):
        self._counters: dict[str, CounterMetric] = defaultdict(CounterMetric)
        self._histograms: dict[str, HistogramMetric] = defaultdict(HistogramMetric)
        self._lock = Lock()
        self._start_time = time.time()

    def increment(self, name: str, value: int = 1, labels: dict = None) -> None:
        """
        增加计数器

        Args:
            name: 指标名称（如 "rag.index.files_indexed"）
            value: 增量值
            labels: 可选标签（暂未实现，预留扩展）
        """
        with self._lock:
            counter = self._counters[name]
            counter.value += value
            counter.last_updated = time.time()

    def observe(self, name: str, value: float, labels: dict = None) -> None:
        """
        记录观察值（用于直方图）

        Args:
            name: 指标名称（如 "rag.retrieval.duration"）
            value: 观察值（如耗时）
            labels: 可选标签（暂未实现，预留扩展）
        """
        with self._lock:
            hist = self._histograms[name]
            hist.count += 1
            hist.total += value
            hist.min_value = min(hist.min_value, value)
            hist.max_value = max(hist.max_value, value)
            hist.last_updated = time.time()

    def timer(self, name: str):
        """
        计时器上下文管理器

        使用示例：
            with metrics.timer("operation.duration"):
                # ... 执行操作
                pass
        """
        return _TimerContext(self, name)

    def get_counter(self, name: str) -> Optional[int]:
        """获取计数器值"""
        with self._lock:
            if name in self._counters:
                return self._counters[name].value
            return None

    def get_histogram(self, name: str) -> Optional[dict]:
        """获取直方图统计"""
        with self._lock:
            if name in self._histograms:
                hist = self._histograms[name]
                return {
                    "count": hist.count,
                    "total": hist.total,
                    "avg": hist.avg,
                    "min": hist.min_value if hist.count > 0 else 0,
                    "max": hist.max_value if hist.count > 0 else 0,
                }
            return None

    def get_snapshot(self) -> dict:
        """
        获取所有指标的快照

        Returns:
            包含所有指标的字典
        """
        with self._lock:
            counters = {
                name: {
                    "value": counter.value,
                    "last_updated": counter.last_updated,
                }
                for name, counter in self._counters.items()
            }

            histograms = {
                name: {
                    "count": hist.count,
                    "total": round(hist.total, 3),
                    "avg": round(hist.avg, 3),
                    "min": round(hist.min_value, 3) if hist.count > 0 else 0,
                    "max": round(hist.max_value, 3) if hist.count > 0 else 0,
                }
                for name, hist in self._histograms.items()
            }

        return {
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "counters": counters,
            "histograms": histograms,
        }

    def reset(self) -> None:
        """重置所有指标（用于测试）"""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._start_time = time.time()


class _TimerContext:
    """计时器上下文管理器"""

    def __init__(self, collector: MetricsCollector, name: str):
        self._collector = collector
        self._name = name
        self._start_time = None

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self._start_time
        self._collector.observe(self._name, elapsed)
        return False


# 全局指标收集器实例
_metrics_instance: Optional[MetricsCollector] = None
_metrics_lock = Lock()


def get_metrics() -> MetricsCollector:
    """
    获取全局指标收集器实例（单例）
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = MetricsCollector()
    return _metrics_instance
