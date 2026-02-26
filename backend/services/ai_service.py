"""
AI服务层 - 编排排版优化、AI建议等业务逻辑
"""
from ..llm.chat_model import ChatModelService
from ..processors.base_processor import BaseProcessor
from ..repositories.knowledge_repository import KnowledgeRepository



class AIService:
    """AI服务类，处理排版优化和AI对话的业务逻辑"""

    def __init__(self, chat_model_service: ChatModelService, knowledge_repository: KnowledgeRepository):
        """
        初始化 AI 服务

        Args:
            chat_model_service: 聊天模型服务实例
            knowledge_repository: 知识库仓储实例
        """
        self._knowledge_repository = knowledge_repository
        self.optimizer: BaseProcessor = BaseProcessor("optimize", chat_model_service)
        self.advisor: BaseProcessor = BaseProcessor("advise", chat_model_service)
        self.editor: BaseProcessor = BaseProcessor("edit", chat_model_service)
        self.rag_qa: BaseProcessor = BaseProcessor("rag_qa", chat_model_service)



    async def optimize_markdown_layout_stream(self, filename: str):
        """
        流式优化 Markdown 排版格式（业务编排）

        Args:
            filename: 文件名

        Yields:
            优化结果的纯文本片段
        """
        # 读取文件内容（会抛出 NotFoundException）
        file_info = self._knowledge_repository.read_file(filename)
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
        file_info = self._knowledge_repository.read_file(filename)
        content = file_info.content

        # session_id 由 BaseProcessor 内部解析，业务层无需传递
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
        file_info = self._knowledge_repository.read_file(filename)
        content = file_info.content

        # session_id 由 BaseProcessor 内部解析，业务层无需传递
        async for chunk in self.editor.process_stream_with_history(
            filename=filename,
            content=content,
            requirement=requirement
        ):
            yield chunk

    async def rag_answer_stream(self, rag_service, question: str, top_k: int = 3):
        """
        流式知识库问答（业务编排）

        Args:
            rag_service: RAG 检索服务
            question: 用户问题
            top_k: 返回的最相关文档数量

        Yields:
            事件对象（answer/source/complete）
        """
        context, sources = rag_service.retrieve_context(question=question, top_k=top_k)

        async for chunk in self.rag_qa.process_stream(
            context=context,
            question=question
        ):
            yield {"type": "chunk", "content": chunk}


        for source in sources:
            yield {"type": "source", "data": source}

        yield {"type": "complete"}






