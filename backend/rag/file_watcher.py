"""
文件监听器
使用watchdog监听文件系统变化，自动更新向量索引
"""
from pathlib import Path
from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent
from .config import WATCHDOG_DEBOUNCE_MS, SUPPORTED_EXTENSIONS


class FileWatcherHandler(FileSystemEventHandler):
    """文件系统事件处理器"""

    def __init__(self, on_change_callback):
        """
        初始化处理器

        Args:
            on_change_callback: 文件变化回调函数，参数为文件路径和事件类型
        """
        super().__init__()
        self.on_change_callback = on_change_callback
        self._debounce_timers = {}  # 文件路径 -> 防抖定时器

    def _should_process_file(self, file_path: str) -> bool:
        """判断是否应该处理该文件"""
        return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _debounce(self, file_path: str, event_type: str):
        """防抖处理"""
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

    def clear_debounce_timers(self):
        """清理所有防抖定时器"""
        for timer in self._debounce_timers.values():
            timer.cancel()
        self._debounce_timers.clear()

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

    def __init__(self, on_change_callback):
        """
        初始化文件监听器

        Args:
            on_change_callback: 文件变化回调函数，参数为文件路径和事件类型
        """
        self.observer = Observer()
        self.handler = FileWatcherHandler(on_change_callback)

    def start(self, watch_path: str):
        """开始监听指定路径"""
        self.observer.schedule(self.handler, watch_path, recursive=True)
        self.observer.start()

    def stop(self):
        """停止监听"""
        self.handler.clear_debounce_timers()
        self.observer.stop()
        self.observer.join()
