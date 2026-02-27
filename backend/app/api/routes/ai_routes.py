"""
AI相关路由
处理AI对话和排版优化等操作
"""
from fastapi import APIRouter, Depends

from app.services import AIService
from app.dependencies import get_ai_service, get_rag_service
from app.schemas import ChatRequest, OptimizeRequest, EditRequest, RAGRequest
from utils import create_streaming_response, require_param, validate_service


# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/optimize")
async def optimize_layout(
    request: OptimizeRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    对已上传的文件进行排版优化，流式返回结果

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = require_param(request.filename, "filename")

    return create_streaming_response(
        ai_service.optimize_markdown_layout_stream,
        filename
    )


@router.post("/advise")
async def advise_document(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    接受用户问题和文件内容，返回 AI 建议

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = require_param(request.filename, "filename")
    question = require_param(request.question, "question")

    return create_streaming_response(
        ai_service.chat_suggestion_stream,
        filename,
        question
    )


@router.post("/edit")
async def edit_document(
    request: EditRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    对已上传的文件进行编辑，流式返回结果

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = require_param(request.filename, "filename")
    requirement = require_param(request.requirement, "requirement")

    return create_streaming_response(
        ai_service.edit_document_stream,
        filename,
        requirement
    )


@router.post("/rag")
async def rag_answer(
    request: RAGRequest,
    ai_service: AIService = Depends(get_ai_service),
    rag_service = Depends(get_rag_service)
):
    """
    知识库问答接口（RAG 检索 + AI 问答）
    """
    question = require_param(request.question, "question")
    validate_service(rag_service, "RAG")

    return create_streaming_response(
        ai_service.rag_answer_stream,
        rag_service,
        question,
        request.top_k
    )
