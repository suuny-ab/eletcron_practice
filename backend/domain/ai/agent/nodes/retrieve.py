"""
检索执行节点
负责调用 RAG 检索服务
"""
from ..state import UnifiedAgentState, SourceItem, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def execute_retrieval(
    state: UnifiedAgentState,
    retrieval_service,
) -> dict:
    """
    检索执行节点
    
    调用现有 RetrievalService 执行检索
    
    Args:
        state: Agent 状态
        retrieval_service: 检索服务实例
        
    Returns:
        更新后的状态字段
    """
    current_query = state.get("current_query", state["user_input"])
    current_round = state.get("current_round", 0) + 1
    max_rounds = state.get("max_rounds", 3)
    top_k = state.get("top_k", 3)
    all_sources = state.get("all_sources", [])
    
    # 发送状态消息
    output_messages: list[OutputMessage] = [
        {
            "type": "status",
            "content": f"正在检索知识库...",
            "data": {"stage": "retrieving", "round": current_round, "max_rounds": max_rounds}
        }
    ]
    
    try:
        # 调用检索服务
        sources = retrieval_service.retrieve_sources(
            question=current_query,
            top_k=top_k
        )
        
        # 转换为 SourceItem 格式并去重
        existing_filenames = {s["filename"] + s["content"][:100] for s in all_sources}
        new_sources: list[SourceItem] = []
        
        for source in sources:
            key = source["filename"] + source["content"][:100]
            if key not in existing_filenames:
                new_sources.append({
                    "filename": source["filename"],
                    "content": source["content"],
                    "score": source.get("score", 0.0)
                })
                existing_filenames.add(key)
        
        # 合并来源
        updated_sources = all_sources + new_sources
        
        logger.info(
            f"[RAG Agent] 检索完成: round={current_round}, "
            f"new_sources={len(new_sources)}, total={len(updated_sources)}"
        )
        
        return {
            "current_round": current_round,
            "all_sources": updated_sources,
            "output_messages": state.get("output_messages", []) + output_messages
        }
        
    except Exception as e:
        logger.error(f"[RAG Agent] 检索失败: {e}")
        raise
