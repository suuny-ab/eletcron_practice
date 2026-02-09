"""
AI相关路由
处理AI对话和排版优化等操作
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..services import get_ai_service
from ..schemas import ChatRequest, OptimizeRequest, EditRequest
from ..utils import create_json_stream
from ..core.exceptions import ValidationException

# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI"])

# 初始化服务层
ai_service = get_ai_service()


@router.post("/optimize")
async def optimize_layout(request: OptimizeRequest) -> StreamingResponse:
    """
    对已上传的文件进行排版优化，流式返回结果

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    filename = request.filename

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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@router.post("/advise")
async def advise_document(request: ChatRequest) -> StreamingResponse:
    """
    接受用户问题和文件内容，返回 AI 建议

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    # 使用工具层包装服务层输出，完成JSON序列化
    generate = create_json_stream(
        ai_service.chat_suggestion_stream,
        request.filename,
        request.question
    )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@router.post("/edit")
async def edit_document(request: EditRequest) -> StreamingResponse:
    """
    对已上传的文件进行编辑，流式返回结果

    路由层职责：
    1. 校验请求数据（Pydantic自动验证）
    2. 调用工具层包装服务层输出
    3. 返回StreamingResponse
    """
    if not request.filename:
        raise ValidationException("必须提供 filename 参数")

    if not request.requirement:
        raise ValidationException("必须提供 requirement 参数")

    # 使用工具层包装服务层输出，完成JSON序列化
    generate = create_json_stream(
        ai_service.edit_document_stream,
        request.filename,
        request.requirement
    )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )