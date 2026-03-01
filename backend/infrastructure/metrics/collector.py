"""
指标收集器
收集系统运行时的关键指标，支持时序数据存储和持久化
"""
import json
import time
import threading
from threading import Lock
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict, deque
from pathlib import Path

from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

# 时序配置
SNAPSHOT_INTERVAL_SECONDS = 10   # 快照间隔
BUFFER_SIZE = 360                # 缓冲区大小（10s * 360 = 1小时）
PERSISTENCE_BATCH_SIZE = 10      # 每批持久化数据点数
DATA_RETENTION_DAYS = 7          # 数据保留天数


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
    - TimeSeries: 时序数据，环形缓冲区存储快照

    使用示例：
        metrics = get_metrics()

        # 计数器
        metrics.increment("rag.index.files_indexed", 10)

        # 直方图（耗时）
        with metrics.timer("rag.index.duration"):
            # ... 执行操作
            pass

        # 获取时序数据
        data_points = metrics.get_timeseries(minutes=30)
    """

    def __init__(self, persistence_path: Path | None = None):
        self._counters: dict[str, CounterMetric] = defaultdict(CounterMetric)
        self._histograms: dict[str, HistogramMetric] = defaultdict(HistogramMetric)
        self._lock = Lock()
        self._start_time = time.time()

        # 时序数据
        self._timeseries_buffer: deque[dict] = deque(maxlen=BUFFER_SIZE)
        self._timeseries_lock = Lock()
        self._persistence_path = persistence_path
        self._pending_writes: list[dict] = []

        # 从磁盘加载历史数据
        if self._persistence_path:
            self._load_from_disk()

        # 启动快照线程
        self._snapshot_thread = threading.Thread(
            target=self._snapshot_worker, daemon=True, name="metrics-snapshot"
        )
        self._snapshot_thread.start()

    def increment(self, name: str, value: int = 1, labels: dict = None) -> None:
        """增加计数器"""
        with self._lock:
            counter = self._counters[name]
            counter.value += value
            counter.last_updated = time.time()

    def observe(self, name: str, value: float, labels: dict = None) -> None:
        """记录观察值（用于直方图）"""
        with self._lock:
            hist = self._histograms[name]
            hist.count += 1
            hist.total += value
            hist.min_value = min(hist.min_value, value)
            hist.max_value = max(hist.max_value, value)
            hist.last_updated = time.time()

    def timer(self, name: str):
        """计时器上下文管理器"""
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
        """获取所有指标的快照"""
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

    def get_timeseries(self, minutes: int = 60) -> list[dict]:
        """
        获取时序数据

        Args:
            minutes: 返回最近 N 分钟的数据

        Returns:
            时序数据点列表，按时间升序
        """
        cutoff = time.time() - minutes * 60
        with self._timeseries_lock:
            return [
                dp for dp in self._timeseries_buffer
                if dp["timestamp"] >= cutoff
            ]

    def reset(self) -> None:
        """重置所有指标（用于测试）"""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._start_time = time.time()
        with self._timeseries_lock:
            self._timeseries_buffer.clear()
            self._pending_writes.clear()

    # ===== 时序数据内部方法 =====

    def _create_timeseries_point(self) -> dict:
        """创建一个时序数据点（当前指标快照的精简版）"""
        with self._lock:
            counters = {
                name: counter.value
                for name, counter in self._counters.items()
            }
            histograms = {
                name: {
                    "count": hist.count,
                    "avg": round(hist.avg, 4),
                    "min": round(hist.min_value, 4) if hist.count > 0 else 0,
                    "max": round(hist.max_value, 4) if hist.count > 0 else 0,
                }
                for name, hist in self._histograms.items()
            }
        return {
            "timestamp": round(time.time(), 1),
            "counters": counters,
            "histograms": histograms,
        }

    def _snapshot_worker(self) -> None:
        """后台线程：定期创建快照并持久化"""
        while True:
            time.sleep(SNAPSHOT_INTERVAL_SECONDS)
            try:
                point = self._create_timeseries_point()
                with self._timeseries_lock:
                    self._timeseries_buffer.append(point)
                    self._pending_writes.append(point)

                    if len(self._pending_writes) >= PERSISTENCE_BATCH_SIZE:
                        self._flush_to_disk()
            except Exception as e:
                logger.error(f"指标快照失败: {e}")

    def _flush_to_disk(self) -> None:
        """将待写入数据刷入磁盘（调用时已持有 _timeseries_lock）"""
        if not self._persistence_path or not self._pending_writes:
            return
        try:
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                for point in self._pending_writes:
                    f.write(json.dumps(point, ensure_ascii=False) + "\n")
            self._pending_writes.clear()
        except Exception as e:
            logger.error(f"指标持久化失败: {e}")

    def _load_from_disk(self) -> None:
        """启动时从磁盘加载最近 1 小时数据"""
        if not self._persistence_path or not self._persistence_path.exists():
            return

        cutoff = time.time() - 3600  # 最近 1 小时
        retention_cutoff = time.time() - DATA_RETENTION_DAYS * 86400
        loaded = 0
        retained_lines: list[str] = []
        needs_cleanup = False

        try:
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        point = json.loads(line)
                        ts = point.get("timestamp", 0)

                        # 超过保留期的数据需要清理
                        if ts < retention_cutoff:
                            needs_cleanup = True
                            continue

                        retained_lines.append(line)

                        if ts >= cutoff:
                            self._timeseries_buffer.append(point)
                            loaded += 1
                    except json.JSONDecodeError:
                        needs_cleanup = True
                        continue

            # 清理过期数据：重写文件
            if needs_cleanup:
                temp_file = self._persistence_path.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    for line in retained_lines:
                        f.write(line + "\n")
                temp_file.replace(self._persistence_path)
                logger.info(f"指标数据清理完成，保留 {len(retained_lines)} 条记录")

            if loaded > 0:
                logger.info(f"从磁盘加载 {loaded} 个指标数据点")
        except Exception as e:
            logger.error(f"加载指标历史失败: {e}")


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
    """获取全局指标收集器实例（单例）"""
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                try:
                    from paths import DATA_DIR
                    persistence_path = DATA_DIR / "metrics.jsonl"
                except ImportError:
                    persistence_path = None
                _metrics_instance = MetricsCollector(persistence_path=persistence_path)
    return _metrics_instance
