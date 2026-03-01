"""
AI相关路由
处理统一 Agent、RAG 调试和会话管理接口
"""
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_rag_service, get_chat_model_service, get_llm_task_service
from app.schemas import (
    RAGRequest, UnifiedAgentRequest, DataResponse, RAGDebugInfo,
    SessionRenameRequest, SessionMetadataResponse, BaseResponse,
)
from utils import create_streaming_response, require_param, validate_service, validate_session_id
from domain.ai.memory import SessionMetadataManager, UnifiedMemoryManager


# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI"])


# ==================== 会话管理路由 ====================

def get_session_metadata_manager() -> SessionMetadataManager:
    """获取会话元数据管理器"""
    return SessionMetadataManager()


@router.get("/sessions", response_model=DataResponse[list[SessionMetadataResponse]])
async def get_sessions(
    sort_by: str = "updated_at",
    manager: SessionMetadataManager = Depends(get_session_metadata_manager)
):
    """
    获取会话列表
    
    Args:
        sort_by: 排序字段，支持 "created_at" 或 "updated_at"
    
    Returns:
        会话元数据列表，按时间倒序排列
    """
    sessions = manager.get_all_sessions(sort_by=sort_by)
    
    return DataResponse(
        data=[
            SessionMetadataResponse(
                session_id=s.session_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                turn_count=s.turn_count,
                last_intent=s.last_intent,
                referenced_documents=s.referenced_documents,
            )
            for s in sessions
        ],
        message="获取会话列表成功"
    )


@router.get("/sessions/{session_id}", response_model=DataResponse[SessionMetadataResponse])
async def get_session(
    session_id: str,
    manager: SessionMetadataManager = Depends(get_session_metadata_manager)
):
    """
    获取单个会话详情
    
    Args:
        session_id: 会话 ID
    
    Returns:
        会话元数据
    """
    session_id = validate_session_id(session_id)
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    
    return DataResponse(
        data=SessionMetadataResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            turn_count=session.turn_count,
            last_intent=session.last_intent,
            referenced_documents=session.referenced_documents,
        ),
        message="获取会话详情成功"
    )


@router.delete("/sessions/{session_id}", response_model=BaseResponse)
async def delete_session(
    session_id: str,
    manager: SessionMetadataManager = Depends(get_session_metadata_manager)
):
    """
    删除会话
    
    同时删除 .jsonl 文件和元数据
    
    Args:
        session_id: 会话 ID
    
    Returns:
        操作结果
    """
    session_id = validate_session_id(session_id)
    if not manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    
    return BaseResponse(message="会话已删除")


@router.put("/sessions/{session_id}/rename", response_model=BaseResponse)
async def rename_session(
    session_id: str,
    request: SessionRenameRequest,
    manager: SessionMetadataManager = Depends(get_session_metadata_manager)
):
    """
    重命名会话
    
    Args:
        session_id: 会话 ID
        request: 包含新标题的请求
    
    Returns:
        操作结果
    """
    session_id = validate_session_id(session_id)
    title = request.title.strip()
    
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    
    if len(title) > 50:
        raise HTTPException(status_code=400, detail="标题长度不能超过 50 字符")
    
    if not manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    
    manager.rename_session(session_id, title)
    
    return BaseResponse(message="会话重命名成功")


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """
    获取会话对话历史
    
    返回会话中的所有对话轮次，用于切换会话时恢复聊天界面
    
    Args:
        session_id: 会话 ID
    
    Returns:
        对话轮次列表
    """
    session_id = validate_session_id(session_id)
    memory = UnifiedMemoryManager(session_id=session_id)
    summary, turns = memory.get_history_sync()
    
    if not turns and summary is None:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    
    history = []
    for turn in turns:
        history.append({
            "role": "user",
            "content": turn.user_input,
            "timestamp": turn.timestamp.isoformat() if turn.timestamp else None,
        })
        history.append({
            "role": "assistant",
            "content": turn.assistant_output,
            "intent_type": turn.intent_type,
            "document_ref": turn.document_ref,
            "retrieval_sources": turn.retrieval_sources,
            "timestamp": turn.timestamp.isoformat() if turn.timestamp else None,
        })
    
    return DataResponse(
        data={
            "session_id": session_id,
            "summary": summary.content if summary else None,
            "messages": history,
        },
        message="获取会话历史成功"
    )


# ==================== RAG 调试路由 ====================


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
