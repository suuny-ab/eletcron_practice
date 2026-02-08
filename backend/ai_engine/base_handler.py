"""
AI处理器基类 - 统一处理所有AI功能
使用配置驱动的方式管理不同任务的提示词
"""
from typing import final, AsyncGenerator
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from .core import get_ai_engine
from .config import PromptConfigFactory


@final
class AIProcessor:
    """通用AI处理器 - 通过任务类型处理不同功能"""

    def __init__(self, task_type: str):
        """
        初始化处理器

        Args:
            task_type: 任务类型 ('optimize', 'advise', 'edit')
        """
        self.task_type = task_type
        self.ai_engine = get_ai_engine()
        self.config = PromptConfigFactory.get_config(task_type)
        self.template = self._build_template()

    def _build_template(self) -> ChatPromptTemplate:
        """根据任务类型构建提示词模板"""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self.config.system),
            HumanMessagePromptTemplate.from_template(self.config.human)
        ])

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
