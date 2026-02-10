"""
AI处理器基类 - 统一处理所有AI功能
职责：
1. 参数验证
2. 流式响应生成
3. 会话ID解析
"""
from typing import final
from collections.abc import AsyncGenerator

from .core import AIEngine
from .config import PromptConfigFactory
from .memory.session_resolver import SessionResolver
from .template import TemplateBuilder
from .history import HistoryManager


@final
class AIProcessor:
    """通用AI处理器 - 通过任务类型处理不同功能"""

    def __init__(self, task_type: str, ai_engine: AIEngine):
        """
        初始化处理器

        Args:
            task_type: 任务类型 ('optimize', 'advise', 'edit')
            ai_engine: AI 引擎实例
        """
        self.task_type = task_type
        self.ai_engine = ai_engine
        self.config = PromptConfigFactory.get_config(task_type)
        self.template_builder = TemplateBuilder()
        self.session_resolver = SessionResolver()
        self.template = self.template_builder.build(
            system_prompt=self.config.system,
            human_prompt=self.config.human,
            need_history=(task_type in {"advise", "edit"})
        )

        # 历史记录相关配置
        self.history_input_key = None
        self.history_manager = None

        if task_type == "advise":
            self.history_input_key = "question"
            self.history_manager = HistoryManager(self.ai_engine)
        elif task_type == "edit":
            self.history_input_key = "requirement"
            self.history_manager = HistoryManager(self.ai_engine)

    async def process_stream(self, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式处理（所有任务通用）

        Args:
            **kwargs: 根据任务类型需要的参数
                     - optimize: content
                     - advise: content, question
                     - edit: content, requirement

        Yields:
            AI生成的响应片段

        Raises:
            ValueError: 缺少必需参数
        """
        # 验证必需参数
        for param in self.config.params:
            if param not in kwargs:
                raise ValueError(f"缺少必需参数: {param}")

        # 生成消息
        messages = self.template.format_messages(**kwargs)

        # 流式生成
        async for chunk in self.ai_engine.stream_generate(messages):
            yield chunk

    async def process_stream_with_history(self, **kwargs) -> AsyncGenerator[str, None]:
        """
        带历史记忆的流式处理（适用于 advise/edit）

        注意：session_id 由内部解析，业务层无需传递
        """
        if not self.history_manager:
            raise ValueError("当前任务类型不支持历史记忆")

        # 内部解析 session_id
        session_id = self.session_resolver.resolve(self.task_type, **kwargs)

        # 验证必需参数
        for param in self.config.params:
            if param not in kwargs:
                raise ValueError(f"缺少必需参数: {param}")

        # 构建基础链
        base_chain = self.template | self.ai_engine.chat_model | self.ai_engine.output_parser

        # 创建带历史的链
        chain_with_history = self.history_manager.create_chain_with_history(
            base_chain,
            self.history_input_key  # type: ignore[arg-type]
        )

        config = {"configurable": {"session_id": session_id}}
        async for chunk in chain_with_history.astream(kwargs, config=config):
            yield chunk
