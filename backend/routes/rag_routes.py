"""
RAG 路由
提供RAG问答API
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from ..schemas.requests import RAGRequest
from ..schemas.responses import DataResponse, RAGAnswer
from ..services.dependencies import get_rag_service
from ..core import get_logger
import json

logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


async def stream_rag_response(rag_service, question: str, top_k: int):
    """
    流式RAG响应生成器

    Args:
        rag_service: RAG服务
        question: 问题
        top_k: 返回的文档数量
    """
    try:
        async for chunk in rag_service.ask(question=question, top_k=top_k):
            yield json.dumps(chunk, ensure_ascii=False) + "\n"
    except Exception as e:
        logger.error(f"RAG流式问答失败: {e}")
        yield json.dumps({
            "type": "error",
            "content": str(e)
        }, ensure_ascii=False) + "\n"


@router.post("/ask")
async def ask_question(
    request: RAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    RAG问答接口

    Args:
        request: RAG请求，包含问题和top_k参数
        rag_service: RAG服务依赖

    Returns:
        包含回答和来源文档的响应
    """
    try:
        if not rag_service:
            raise HTTPException(status_code=400, detail="RAG服务未初始化，请先配置API密钥和模型")

        if request.stream:
            # 流式响应
            return StreamingResponse(
                stream_rag_response(rag_service, request.question, request.top_k),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应：收集所有内容后返回
            answer_parts = []
            sources = []

            async for chunk in rag_service.ask(question=request.question, top_k=request.top_k):
                if chunk["type"] == "answer":
                    answer_parts.append(chunk["content"])
                elif chunk["type"] == "source":
                    sources.append(chunk["data"])
                elif chunk["type"] == "error":
                    raise HTTPException(status_code=500, detail=chunk["content"])

            # 构建响应数据
            from ..schemas.responses import RAGSource
            rag_sources = [
                RAGSource(filename=s["filename"], content=s["content"], score=s["score"])
                for s in sources
            ]

            rag_answer = RAGAnswer(answer="".join(answer_parts), sources=rag_sources)

            return DataResponse(
                success=True,
                message="问答成功",
                data=rag_answer
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG问答失败: {e}")
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")
