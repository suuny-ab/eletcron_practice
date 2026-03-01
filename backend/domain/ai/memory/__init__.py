"""会话历史存储模块"""
from .chat_history import FileChatMessageHistory
from .session_resolver import SessionResolver
from .models import ConversationTurn, HistorySummary
from .unified_memory import UnifiedMemoryManager
from .unified_summarizer import UnifiedSummarizer
from .session_metadata_manager import SessionMetadataManager, SessionMetadata

__all__ = [
    # 旧模块（保留兼容）
    'FileChatMessageHistory',
    'SessionResolver',
    # 新统一记忆模块
    'ConversationTurn',
    'HistorySummary',
    'UnifiedMemoryManager',
    'UnifiedSummarizer',
    # 会话元数据管理
    'SessionMetadataManager',
    'SessionMetadata',
]
