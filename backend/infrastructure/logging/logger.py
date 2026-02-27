"""
日志配置模块 - 统一日志管理

功能：
- 结构化日志输出（可配置 JSON 格式）
- 上下文信息追踪（请求ID、操作类型、耗时）
- 日志文件按日期滚动
- 不同级别日志分文件存储
"""
import logging
import sys
import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextvars import ContextVar
from dataclasses import dataclass, field


# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 上下文变量（用于请求追踪）
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> None:
    """设置当前请求ID"""
    _request_id.set(request_id)


def get_request_id() -> Optional[str]:
    """获取当前请求ID"""
    return _request_id.get()


@dataclass
class LogContext:
    """日志上下文"""
    operation: Optional[str] = None
    duration_ms: Optional[float] = None
    extra: dict = field(default_factory=dict)


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式器

    支持两种格式：
    - text: 人类可读的文本格式（默认）
    - json: JSON 格式（便于日志系统解析）
    """

    def __init__(self, format_type: str = "text"):
        super().__init__()
        self.format_type = format_type

    def format(self, record: logging.LogRecord) -> str:
        # 基础信息
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加请求ID
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        # 添加上下文信息（如果有）
        if hasattr(record, "context") and record.context:
            ctx: LogContext = record.context
            if ctx.operation:
                log_data["operation"] = ctx.operation
            if ctx.duration_ms is not None:
                log_data["duration_ms"] = round(ctx.duration_ms, 2)
            if ctx.extra:
                log_data["extra"] = ctx.extra

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 输出格式
        if self.format_type == "json":
            return json.dumps(log_data, ensure_ascii=False)
        else:
            return self._format_text(log_data)

    def _format_text(self, data: dict) -> str:
        """格式化为可读文本"""
        parts = [
            data["timestamp"][:19],  # 截取到秒
            f"| {data['level']:<8}",
            f"| {data['logger']}",
        ]

        if "request_id" in data:
            parts.append(f"| [{data['request_id'][:8]}]")

        parts.append(f"| {data['message']}")

        if "operation" in data:
            parts.append(f"| op={data['operation']}")

        if "duration_ms" in data:
            parts.append(f"| {data['duration_ms']}ms")

        if "extra" in data:
            extra_str = " ".join(f"{k}={v}" for k, v in data["extra"].items())
            parts.append(f"| {extra_str}")

        result = " ".join(parts)

        if "exception" in data:
            result += f"\n{data['exception']}"

        return result


class ContextLogger(logging.LoggerAdapter):
    """
    支持上下文的日志适配器

    使用示例：
        logger = get_logger(__name__)
        logger.info("操作完成", extra={"context": LogContext(
            operation="rag.index",
            duration_ms=123.45
        )})
    """

    def process(self, msg, kwargs):
        # 将 context 从 extra 移动到 record
        if "extra" in kwargs and "context" in kwargs["extra"]:
            # 已经有 context，直接使用
            pass
        return msg, kwargs


def setup_logging(json_format: bool = False):
    """
    配置全局日志系统

    Args:
        json_format: 是否使用 JSON 格式输出（默认 False，使用文本格式）
    """
    format_type = "json" if json_format else "text"
    formatter = StructuredFormatter(format_type)

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 1. 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. 文件处理器 - 所有日志
    today = datetime.now().strftime("%Y-%m-%d")
    all_log_file = LOG_DIR / f"all_{today}.log"
    file_handler = logging.FileHandler(
        all_log_file,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 3. 文件处理器 - 错误日志
    error_log_file = LOG_DIR / f"error_{today}.log"
    error_handler = logging.FileHandler(
        error_log_file,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 4. 配置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器

    Args:
        name: 日志器名称（通常使用 __name__）

    Returns:
        Logger: 日志器实例
    """
    return logging.getLogger(name)


class LogTimer:
    """
    日志计时器

    自动记录操作耗时

    使用示例：
        with LogTimer(logger, "rag.index", "索引完成"):
            # ... 执行操作
            pass
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        success_msg: str = "操作完成",
        error_msg: str = "操作失败"
    ):
        self._logger = logger
        self._operation = operation
        self._success_msg = success_msg
        self._error_msg = error_msg
        self._start_time = None

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self._start_time) * 1000

        if exc_type is None:
            self._logger.info(
                self._success_msg,
                extra={"context": LogContext(
                    operation=self._operation,
                    duration_ms=duration_ms
                )}
            )
        else:
            self._logger.error(
                self._error_msg,
                extra={"context": LogContext(
                    operation=self._operation,
                    duration_ms=duration_ms
                )},
                exc_info=True
            )
        return False


# 根据环境变量决定是否使用 JSON 格式
_use_json = os.environ.get("LOG_FORMAT", "text").lower() == "json"

# 在模块导入时自动配置日志
setup_logging(json_format=_use_json)
