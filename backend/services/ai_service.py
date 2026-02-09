"""
AI服务层 - 编排排版优化、AI建议等业务逻辑
直接使用通用AI处理器处理各类AI任务
"""

from ..ai_engine import AIProcessor
from ..utils.knowledge_utils import read_file


class AIService:
    """AI服务类，处理排版优化和AI对话的业务逻辑"""

    def __init__(self):
        """
        初始化AI服务
        从配置文件自动读取API密钥和模型名称
        """
        self.optimizer = AIProcessor('optimize')
        self.advisor = AIProcessor('advise')
        self.editor = AIProcessor('edit')

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
        content = file_info["content"]

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
        content = file_info["content"]

        # 调用建议器进行流式处理
        async for chunk in self.advisor.process_stream(content=content, question=question):
            yield chunk  # 返回纯文本，不关心JSON格式

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
        content = file_info["content"]

        # 调用编辑器进行流式处理
        async for chunk in self.editor.process_stream(requirement=requirement, content=content):
            yield chunk  # 返回纯文本，不关心JSON格式


# 创建全局AI服务实例
_ai_service = None


def get_ai_service() -> AIService:
    """
    获取AI服务实例（单例模式）

    Returns:
        AIService 实例
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def reload_ai_service() -> AIService:
    """
    重新加载AI服务实例（从配置文件读取最新配置）

    Returns:
        AIService 实例
    """
    global _ai_service
    _ai_service = AIService()
    return _ai_service
