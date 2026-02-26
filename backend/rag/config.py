"""
RAG 配置文件
定义RAG技术参数
"""
from pathlib import Path

# ==================== 向量数据库配置 ====================
VECTOR_DB_PATH = (Path(__file__).resolve().parent.parent / ".data" / "chroma_db")  # 向量数据库存储路径，对用户透明
INDEX_MARKER_PATH = VECTOR_DB_PATH / "rag_index.done"  # 索引完成标记文件

# ==================== 文档切分配置 ====================
CHUNK_SIZE = 500  # 文档块最大长度
CHUNK_OVERLAP = 100  # 文档块重叠长度（用于超长块二次切分）
MIN_CHUNK_SIZE = 80  # 文档块最小长度（用于合并过短块）

# ==================== Markdown标题切分配置 ====================
MARKDOWN_HEADERS_TO_SPLIT_ON = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
    ("#####", "Header 5"),
    ("######", "Header 6"),
]

# ==================== 文件监听配置 ====================
WATCHDOG_DEBOUNCE_MS = 500  # 文件变化防抖延迟（毫秒）
SUPPORTED_EXTENSIONS = {".md", ".markdown"}  # 支持的文件扩展名
