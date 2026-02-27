"""
AI服务层 - 编排排版优化、AI建议等业务逻辑
"""
from pathlib import Path

from core.interfaces import ILLMTaskService, IKnowledgeRepository



class AIService:
    """AI服务类，处理排版优化和AI对话的业务逻辑"""

    def __init__(self, llm_task_service: ILLMTaskService, knowledge_repository: IKnowledgeRepository):
        """
        初始化 AI 服务

        Args:
            llm_task_service: 统一LLM任务服务实例
            knowledge_repository: 知识库仓储实例
        """
        self._llm_task_service = llm_task_service
        self._knowledge_repository = knowledge_repository

    async def optimize_markdown_layout_stream(self, filename: str):
        """
        流式优化 Markdown 排版格式（业务编排）

        Args:
            filename: 文件名

        Yields:
            优化结果的纯文本片段
        """
        file_info = self._knowledge_repository.read_file(filename)
        content = file_info.content

        async for chunk in self._llm_task_service.stream(
            task_type="optimize",
            content=content
        ):
            yield chunk

    async def chat_suggestion_stream(self, filename: str, question: str):
        """
        流式生成 AI 建议（业务编排）

        Args:
            filename: 文件名
            question: 用户问题

        Yields:
            AI建议的纯文本片段
        """
        file_info = self._knowledge_repository.read_file(filename)
        content = file_info.content
        session_id = Path(filename).name

        async for chunk in self._llm_task_service.stream(
            task_type="advise",
            session_id=session_id,
            use_history=True,
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
        file_info = self._knowledge_repository.read_file(filename)
        content = file_info.content
        session_id = Path(filename).name

        async for chunk in self._llm_task_service.stream(
            task_type="edit",
            session_id=session_id,
            use_history=True,
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

        async for chunk in self._llm_task_service.stream(
            task_type="rag_qa",
            context=context,
            question=question
        ):
            yield {"type": "chunk", "content": chunk}

        for source in sources:
            yield {"type": "source", "data": source}

        yield {"type": "complete"}







