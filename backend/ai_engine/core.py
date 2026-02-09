"""
AI引擎核心类 - 封装通义千问大模型调用
提供底层的AI能力，不包含业务逻辑
"""
from collections.abc import AsyncGenerator
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from ..core.exceptions import ExternalServiceException
from ..utils.config_manager import config_manager


class AIEngine:
    """AI 引擎类，封装通义千问大模型调用 - 单例模式"""
    
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        初始化 AI 引擎
        从配置文件获取API Key和模型名称
        """
        if self._initialized:  # 避免重复初始化
            return
            
        # 从配置文件读取配置
        config = config_manager.read_config()
        if not config:
            raise ExternalServiceException("配置文件不存在，请先配置系统")

        api_key = config.api_key
        model_name = config.model_name or "qwen3-max"

        if not api_key:
            raise ExternalServiceException("API密钥不能为空")

        # noinspection PyTypeChecker
        self.chat_model: ChatTongyi = ChatTongyi(
            api_key=api_key,  # pyright: ignore[reportArgumentType]
            model=model_name
        )

        # 初始化输出解析器
        self.output_parser: StrOutputParser = StrOutputParser()
        
        self._initialized = True

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
