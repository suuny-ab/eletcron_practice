"""
聊天模型服务 - 封装模型调用
"""
from collections.abc import AsyncGenerator
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser

from ..core.model_provider import ModelProvider


class ChatModelService:
    """聊天模型服务 - 封装模型调用逻辑"""

    def __init__(self, model_provider: ModelProvider):
        """
        初始化聊天模型服务

        Args:
            model_provider: 模型提供者实例
        """
        self._model_provider = model_provider
        self._output_parser = StrOutputParser()

    @property
    def chat_model(self):
        """获取聊天模型（从注入的 ModelProvider）"""
        return self._model_provider.chat_model

    @property
    def output_parser(self):
        """获取输出解析器"""
        return self._output_parser

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
        stream = self.chat_model | self._output_parser
        async for chunk in stream.astream(input=messages):
            if chunk:
                yield chunk
