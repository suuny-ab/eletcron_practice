"""
RAG 配置文件
定义RAG技术参数
"""
from pathlib import Path

# ==================== 向量数据库配置 ====================
VECTOR_DB_PATH = Path(".data/chroma_db")  # 向量数据库存储路径，对用户透明

# ==================== 文档切分配置 ====================
CHUNK_SIZE = 500  # 文档块大小
CHUNK_OVERLAP = 100  # 文档块重叠大小

# ==================== Markdown标题切分配置 ====================
MARKDOWN_HEADERS_TO_SPLIT_ON = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
]

# ==================== 文件监听配置 ====================
WATCHDOG_DEBOUNCE_MS = 500  # 文件变化防抖延迟（毫秒）
SUPPORTED_EXTENSIONS = {".md", ".markdown"}  # 支持的文件扩展名
