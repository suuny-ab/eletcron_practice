"""
AI相关路由
处理统一 Agent 和 RAG 调试接口
"""
from fastapi import APIRouter, Depends

from app.dependencies import get_rag_service, get_chat_model_service, get_llm_task_service
from app.schemas import RAGRequest, UnifiedAgentRequest, DataResponse, RAGDebugInfo
from utils import create_streaming_response, require_param, validate_service


# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/rag/debug", response_model=DataResponse[RAGDebugInfo])
async def rag_debug(
    request: RAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    RAG 调试接口 - 返回详细的检索步骤信息

    用于可视化展示 RAG 检索流程：
    1. 向量检索结果（距离、相似度、归一化得分）
    2. BM25检索结果（分词、原始得分、归一化得分）
    3. 混合候选（来源标记、混合得分计算）
    4. LLM重排序结果（排名变化、是否选中）
    5. 各阶段耗时统计
    """
    question = require_param(request.question, "question")
    validate_service(rag_service, "RAG")

    debug_info = rag_service.retrieve_sources_debug(question, request.top_k)

    return DataResponse(
        data=RAGDebugInfo(**debug_info),
        message="RAG 调试信息获取成功"
    )


@router.post("/agent")
async def unified_agent(
    request: UnifiedAgentRequest,
    rag_service = Depends(get_rag_service),
    chat_model_service = Depends(get_chat_model_service),
    llm_task_service = Depends(get_llm_task_service),
):
    """
    统一 Agent 接口
    
    整合所有 AI 功能的统一入口：
    - 闲聊对话 (chitchat)
    - RAG 知识检索 (rag_query)
    - 文档建议 (doc_advise)
    - 文档编辑 (doc_edit) - 需要 editor 权限
    - 文档格式化 (doc_format) - 需要 editor 权限
    
    流式响应格式（NDJSON）：
    - {"type": "status", ...}    状态更新
    - {"type": "thinking", ...}  思考过程
    - {"type": "sources", ...}   检索来源
    - {"type": "chunk", ...}     文本输出
    - {"type": "diff", ...}      文档修改 (Diff 格式)
    - {"type": "prompt", ...}    提示消息 (需选择文档/切换权限)
    - {"type": "error", ...}     错误信息
    - {"type": "complete", ...}  完成
    """
    user_input = require_param(request.user_input, "user_input")
    
    from domain.ai.agent import UnifiedAgent
    
    # 获取检索服务（RAG 可能不可用，但不阻塞非 RAG 请求）
    retrieval_service = None
    if rag_service:
        retrieval_service = rag_service._retrieval_service
    
    agent = UnifiedAgent(
        chat_model=chat_model_service.chat_model,
        retrieval_service=retrieval_service,
        llm_task_service=llm_task_service,
    )
    
    return create_streaming_response(
        agent.astream,
        user_input=user_input,
        session_id=request.session_id,
        permission_mode=request.permission_mode,
        document_content=request.document_content,
        document_name=request.document_name,
        top_k=request.top_k,
        max_rounds=request.max_rounds,
    )
