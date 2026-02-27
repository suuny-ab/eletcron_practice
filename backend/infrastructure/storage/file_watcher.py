"""
文件监听器
使用watchdog监听文件系统变化，自动更新向量索引
"""
import time
from pathlib import Path
from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent
from domain.knowledge.rag.config import WATCHDOG_DEBOUNCE_MS, SUPPORTED_EXTENSIONS

from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


# 启动静默期（秒），用于忽略启动时的假阳性事件
STARTUP_SILENCE_PERIOD = 3.0


class FileWatcherHandler(FileSystemEventHandler):
    """文件系统事件处理器"""

    def __init__(self, on_change_callback, silence_period: float = STARTUP_SILENCE_PERIOD):
        """
        初始化处理器

        Args:
            on_change_callback: 文件变化回调函数，参数为文件路径和事件类型
            silence_period: 启动静默期（秒），在此期间忽略所有事件
        """
        super().__init__()
        self.on_change_callback = on_change_callback
        self._debounce_timers = {}  # 文件路径 -> 防抖定时器
        self._silence_mode = True  # 默认开启静默模式
        self._silence_period = silence_period
        self._silence_timer: Timer | None = None

    def _should_process_file(self, file_path: str) -> bool:
        """判断是否应该处理该文件"""
        return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _debounce(self, file_path: str, event_type: str):
        """防抖处理"""
        # 静默期内忽略所有事件
        if self._silence_mode:
            return

        # 取消之前的定时器
        if file_path in self._debounce_timers:
            self._debounce_timers[file_path].cancel()

        def _run_callback():
            try:
                self.on_change_callback(file_path, event_type)
            finally:
                self._debounce_timers.pop(file_path, None)

        # 创建新的定时器
        timer = Timer(
            WATCHDOG_DEBOUNCE_MS / 1000.0,
            _run_callback
        )
        self._debounce_timers[file_path] = timer
        timer.start()

    def start_listening(self):
        """结束静默期，开始监听事件"""
        def _end_silence():
            self._silence_mode = False
            logger.info(f"[FileWatcher] 静默期结束，开始监听文件变化")

        self._silence_timer = Timer(self._silence_period, _end_silence)
        self._silence_timer.start()
        logger.info(f"[FileWatcher] 启动静默期 {self._silence_period}s，忽略初始事件")

    def clear_debounce_timers(self):
        """清理所有防抖定时器"""
        for timer in self._debounce_timers.values():
            timer.cancel()
        self._debounce_timers.clear()

        # 清理静默期定时器
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None

    def on_created(self, event: FileCreatedEvent):
        """文件创建事件"""
        if not event.is_directory and self._should_process_file(event.src_path):
            self._debounce(event.src_path, "created")

    def on_modified(self, event: FileModifiedEvent):
        """文件修改事件"""
        if not event.is_directory and self._should_process_file(event.src_path):
            self._debounce(event.src_path, "modified")

    def on_deleted(self, event: FileDeletedEvent):
        """文件删除事件"""
        if not event.is_directory and self._should_process_file(event.src_path):
            self._debounce(event.src_path, "deleted")


class FileWatcher:
    """文件监听器"""

    def __init__(self, on_change_callback, silence_period: float = STARTUP_SILENCE_PERIOD):
        """
        初始化文件监听器

        Args:
            on_change_callback: 文件变化回调函数，参数为文件路径和事件类型
            silence_period: 启动静默期（秒），在此期间忽略所有事件
        """
        self.observer = Observer()
        self.handler = FileWatcherHandler(on_change_callback, silence_period)

    def start(self, watch_path: str):
        """开始监听指定路径"""
        self.observer.schedule(self.handler, watch_path, recursive=True)
        self.observer.start()
        # 启动静默期计时器
        self.handler.start_listening()

    def stop(self):
        """停止监听"""
        self.handler.clear_debounce_timers()
        self.observer.stop()
        self.observer.join()
