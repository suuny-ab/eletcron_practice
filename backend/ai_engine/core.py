"""
AI引擎核心类 - 封装通义千问大模型调用
提供底层的AI能力，不包含业务逻辑
"""
from collections.abc import AsyncGenerator
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser


class AIEngine:
    """AI 引擎类，封装通义千问大模型调用"""

    def __init__(self, api_key: str, model_name: str = "qwen3-max"):
        """
        初始化 AI 引擎

        Args:
            api_key: 通义千问 API Key
            model_name: 模型名称，默认 qwen3-max
        """
        self.chat_model: ChatTongyi = ChatTongyi(
            api_key=api_key,  # pyright: ignore[reportArgumentType]
            model=model_name
        )
        self.output_parser: StrOutputParser = StrOutputParser()

    async def stream_generate(self, messages: list[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        流式生成内容（底层AI能力）

        Args:
            messages: 消息列表，包含系统消息和用户消息

        Yields:
            str: 生成的内容片段

        Raises:
            Exception: AI流式处理失败时抛出异常（可能是网络错误、API错误等）
        """
        stream = self.chat_model | self.output_parser
        async for chunk in stream.astream(input=messages):
            if chunk:
                yield chunk
