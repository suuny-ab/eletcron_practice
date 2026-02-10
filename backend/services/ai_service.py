"""
AI服务层 - 编排排版优化、AI建议等业务逻辑
"""
from ..ai_engine import AIProcessor, AIEngine
from ..utils.knowledge_utils import read_file


class AIService:
    """AI服务类，处理排版优化和AI对话的业务逻辑"""

    def __init__(self, ai_engine: AIEngine):
        """
        初始化 AI 服务

        Args:
            ai_engine: AI 引擎实例
        """
        self.ai_engine = ai_engine
        self.optimizer: AIProcessor = AIProcessor('optimize', ai_engine)
        self.advisor: AIProcessor = AIProcessor('advise', ai_engine)
        self.editor: AIProcessor = AIProcessor('edit', ai_engine)

    async def optimize_markdown_layout_stream(self, filename: str):
        """
        流式优化 Markdown 排版格式（业务编排）

        Args:
            filename: 文件名

        Yields:
            优化结果的纯文本片段
        """
        # 读取文件内容（会抛出 NotFoundException）
        file_info = read_file(filename)
        content = file_info.content

        # 调用优化器进行流式处理
        async for chunk in self.optimizer.process_stream(content=content):
            yield chunk  # 返回纯文本，不关心JSON格式

    async def chat_suggestion_stream(self, filename: str, question: str):
        """
        流式生成 AI 建议（业务编排）

        Args:
            filename: 文件名
            question: 用户问题

        Yields:
            AI建议的纯文本片段
        """
        # 读取文件内容（会抛出 NotFoundException）
        file_info = read_file(filename)
        content = file_info.content

        # session_id 由 AIProcessor 内部解析，业务层无需传递
        async for chunk in self.advisor.process_stream_with_history(
            filename=filename,
            content=content,
            question=question
        ):
            yield chunk

    async def edit_document_stream(self, filename: str, requirement: str):
        """
        流式编辑文档（业务编排）

        Args:
            filename: 文件名
            requirement: 用户编辑要求

        Yields:
            编辑后的文档片段
        """
        # 读取文件内容（会抛出 NotFoundException）
        file_info = read_file(filename)
        content = file_info.content

        # session_id 由 AIProcessor 内部解析，业务层无需传递
        async for chunk in self.editor.process_stream_with_history(
            filename=filename,
            content=content,
            requirement=requirement
        ):
            yield chunk
