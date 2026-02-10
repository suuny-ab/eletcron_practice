"""
AI相关路由
处理AI对话和排版优化等操作
"""
from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from ..services import AIService
from ..services.dependencies import get_ai_service
from ..schemas import ChatRequest, OptimizeRequest, EditRequest
from ..utils import create_json_stream
from ..core.exceptions import ValidationException

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/optimize")
async def optimize_layout(
    request: OptimizeRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> StreamingResponse:
    """
    对已上传的文件进行排版优化，流式返回结果

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = request.filename.strip() if request.filename else ""

    if not filename:
        raise ValidationException("必须提供 filename 参数")

    # 使用工具层包装服务层输出，完成JSON序列化
    generate = create_json_stream(
        ai_service.optimize_markdown_layout_stream,
        filename
    )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS
    )



@router.post("/advise")
async def advise_document(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> StreamingResponse:
    """
    接受用户问题和文件内容，返回 AI 建议

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = request.filename.strip() if request.filename else ""
    question = request.question.strip() if request.question else ""

    if not filename:
        raise ValidationException("必须提供 filename 参数")

    if not question:
        raise ValidationException("必须提供 question 参数")

    # 使用工具层包装服务层输出，完成JSON序列化
    generate = create_json_stream(
        ai_service.chat_suggestion_stream,
        filename,
        question
    )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS
    )



@router.post("/edit")
async def edit_document(
    request: EditRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> StreamingResponse:
    """
    对已上传的文件进行编辑，流式返回结果

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = request.filename.strip() if request.filename else ""
    requirement = request.requirement.strip() if request.requirement else ""

    if not filename:
        raise ValidationException("必须提供 filename 参数")

    if not requirement:
        raise ValidationException("必须提供 requirement 参数")

    # 使用工具层包装服务层输出，完成JSON序列化
    generate = create_json_stream(
        ai_service.edit_document_stream,
        filename,
        requirement
    )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS
    )
