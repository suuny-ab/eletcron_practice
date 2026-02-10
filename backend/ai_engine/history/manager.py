"""
对话历史管理器
负责会话历史的创建和获取
"""
from importlib import import_module

from ..memory.chat_history import FileChatMessageHistory
from ..memory.summarizer import Summarizer


class HistoryManager:
    """对话历史管理器"""

    def __init__(self, ai_engine):
        """初始化历史管理器

        Args:
            ai_engine: AI引擎实例，用于摘要生成
        """
        self.ai_engine = ai_engine
        self.summarizer = Summarizer()

    def get_session_history(self, session_id: str) -> FileChatMessageHistory:
        """获取指定会话的历史记录

        Args:
            session_id: 会话ID

        Returns:
            FileChatMessageHistory实例
        """
        summarizer_callable = self.summarizer.to_callable(self.ai_engine)
        return FileChatMessageHistory(
            session_id=session_id,
            summarizer=summarizer_callable
        )

    def create_chain_with_history(self, base_chain, history_input_key: str):
        """创建带历史记录的链

        Args:
            base_chain: 基础链
            history_input_key: 历史消息输入键

        Returns:
            RunnableWithMessageHistory实例
        """
        runnables_history = import_module("langchain_core.runnables.history")
        runnable_with_history = getattr(runnables_history, "RunnableWithMessageHistory")

        return runnable_with_history(
            base_chain,
            self.get_session_history,
            input_messages_key=history_input_key,
            history_messages_key="history"
        )
