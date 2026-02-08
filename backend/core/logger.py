"""
日志配置模块 - 统一日志管理
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


# 日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logging():
    """
    配置全局日志系统

    功能：
    - 同时输出到控制台和文件
    - 不同级别日志分文件存储
    - 日志文件按日期滚动
    - 格式化日志输出
    """
    # 创建日志格式
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 1. 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # 2. 文件处理器 - 所有日志
    today = datetime.now().strftime("%Y-%m-%d")
    all_log_file = LOG_DIR / f"all_{today}.log"
    file_handler = logging.FileHandler(
        all_log_file,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # 3. 文件处理器 - 错误日志
    error_log_file = LOG_DIR / f"error_{today}.log"
    error_handler = logging.FileHandler(
        error_log_file,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)

    # 4. 配置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("langchain").setLevel(logging.WARNING)

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


# 在模块导入时自动配置日志
setup_logging()
