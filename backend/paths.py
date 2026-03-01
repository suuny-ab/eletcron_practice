"""
全局路径定义
所有需要引用项目目录的模块统一从此处导入，避免依赖文件相对位置
"""
from pathlib import Path

# backend 根目录（paths.py 所在目录）
BACKEND_DIR = Path(__file__).resolve().parent

# 数据存储根目录
DATA_DIR = BACKEND_DIR / ".data"

# 会话数据目录
SESSIONS_DIR = DATA_DIR / "ai_sessions"

# 向量数据库目录
VECTOR_DB_DIR = DATA_DIR / "chroma_db"

# 指标持久化文件
METRICS_FILE = DATA_DIR / "metrics.jsonl"
