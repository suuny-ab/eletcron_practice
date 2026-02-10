"""
摘要生成器
负责对话历史的摘要生成
"""
from typing import Awaitable, Callable

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from ..config.prompt_config import PromptConfigFactory


class Summarizer:
    """对话摘要生成器"""

    def __init__(self):
        """初始化摘要生成器"""
        self.config = PromptConfigFactory.get_config('summary')

    def format_input(self, old_summary: str | None, old_messages: list[BaseMessage]) -> str:
        """格式化摘要输入

        Args:
            old_summary: 旧摘要
            old_messages: 旧消息列表

        Returns:
            格式化后的对话字符串
        """
        lines: list[str] = []
        if old_summary:
            lines.append(f"已有摘要：\n{old_summary}")
        lines.append("对话内容：")
        for msg in old_messages:
            if msg.type == "human":
                role = "用户"
            elif msg.type == "ai":
                role = "助手"
            else:
                role = "系统"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def format_messages(self, old_summary: str | None, old_messages: list[BaseMessage]) -> list[BaseMessage]:
        """格式化为LangChain消息

        Args:
            old_summary: 旧摘要
            old_messages: 旧消息列表

        Returns:
            消息列表
        """
        conversation = self.format_input(old_summary, old_messages)
        messages = [
            SystemMessage(content=self.config.system),
            HumanMessage(content=self.config.human.format(conversation=conversation))
        ]
        return messages

    def to_callable(self, ai_engine) -> Callable[[str | None, list[BaseMessage]], Awaitable[str]]:
        """转换为可调用函数

        Args:
            ai_engine: AI引擎实例

        Returns:
            异步摘要生成函数
        """
        async def summarize(old_summary: str | None, old_messages: list[BaseMessage]) -> str:
            """执行摘要生成"""
            messages = self.format_messages(old_summary, old_messages)
            chunks: list[str] = []
            async for chunk in ai_engine.stream_generate(messages):
                chunks.append(chunk)
            return "".join(chunks).strip()

        return summarize
