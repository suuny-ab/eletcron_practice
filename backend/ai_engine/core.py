"""
AI引擎核心类 - 封装通义千问大模型调用
提供底层的AI能力，不包含业务逻辑
"""
from collections.abc import AsyncGenerator
from pathlib import Path
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from ..core.exceptions import ExternalServiceException
from ..core import get_logger


class AIEngine:
    """AI 引擎类，封装通义千问大模型调用"""

    def __init__(self):
        """
        初始化 AI 引擎
        从环境变量自动获取API Key
        """
        import os
        from dotenv import load_dotenv

        # 加载 .env 文件（从ai_engine目录向上两级到backend目录）
        env_path = Path(__file__).resolve().parent.parent / ".env"
        _ = load_dotenv(env_path)

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ExternalServiceException("请设置 DASHSCOPE_API_KEY 环境变量")

        # noinspection PyTypeChecker
        self.chat_model: ChatTongyi = ChatTongyi(
            api_key=api_key,  # pyright: ignore[reportArgumentType]
            model="qwen3-max"  # 使用通义千问最新模型
        )

        # 初始化输出解析器
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

        Note:
            此方法不捕获异常，底层 LangChain 抛出的任何异常都会透传。
            可能的异常类型：
            - ConnectionError: 网络连接失败
            - TimeoutError: 请求超时
            - ValueError: 参数错误
            - RuntimeError: 运行时错误
            - 其他 langchain 相关异常
        """
        # 创建流式处理链，使用输出解析器
        stream = self.chat_model | self.output_parser
        async for chunk in stream.astream(input=messages):
            # 使用输出解析器后，chunk已经是字符串类型
            if chunk:
                yield chunk


# 创建全局 AI 引擎实例
_ai_engine = None


def get_ai_engine() -> AIEngine:
    """
    获取 AI 引擎实例（单例模式）

    Returns:
        AIEngine 实例
    """
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine()
    return _ai_engine


def create_ai_engine() -> AIEngine:
    """
    创建新的 AI 引擎实例

    Returns:
        AIEngine 实例
    """
    return AIEngine()