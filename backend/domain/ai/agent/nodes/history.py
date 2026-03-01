"""
历史管理节点
负责加载和保存对话历史
"""
from ..state import UnifiedAgentState
from ...memory import UnifiedMemoryManager, UnifiedSummarizer, ConversationTurn
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def load_history(
    state: UnifiedAgentState,
    memory_manager: UnifiedMemoryManager,
) -> dict:
    """
    加载历史节点
    
    从 UnifiedMemoryManager 加载会话历史
    
    Args:
        state: Agent 状态
        memory_manager: 记忆管理器实例
        
    Returns:
        更新后的状态字段: history_summary, recent_turns
    """
    try:
        summary, turns = await memory_manager.get_history()
        
        summary_str = summary.content if summary else None
        turns_dicts = [t.to_dict() for t in turns]
        
        logger.info(
            f"[Unified Agent] 历史加载: summary={'有' if summary else '无'}, "
            f"turns={len(turns)}"
        )
        
        return {
            "history_summary": summary_str,
            "recent_turns": turns_dicts,
            "output_messages": state.get("output_messages", [])
        }
        
    except Exception as e:
        logger.error(f"[Unified Agent] 历史加载失败: {e}")
        return {
            "history_summary": None,
            "recent_turns": [],
            "output_messages": state.get("output_messages", [])
        }


async def save_history(
    state: UnifiedAgentState,
    memory_manager: UnifiedMemoryManager,
) -> dict:
    """
    保存历史节点
    
    将当前对话轮次保存到 UnifiedMemoryManager
    
    Args:
        state: Agent 状态
        memory_manager: 记忆管理器实例
        
    Returns:
        空字典（终端节点）
    """
    try:
        final_output = state.get("final_output", "")
        if not final_output:
            return {}
        
        # 收集 RAG 检索来源
        retrieval_sources = [
            s["filename"] for s in state.get("all_sources", [])
        ]
        
        turn = ConversationTurn(
            user_input=state["user_input"],
            assistant_output=final_output,
            intent_type=state.get("intent_type", "chitchat"),
            permission_mode=state.get("permission_mode", "assistant"),
            document_ref=state.get("document_name"),
            retrieval_sources=retrieval_sources,
        )
        
        await memory_manager.add_turn(turn)
        
        logger.info(
            f"[Unified Agent] 历史保存: intent={turn.intent_type}, "
            f"doc={turn.document_ref}"
        )
        
    except Exception as e:
        logger.error(f"[Unified Agent] 历史保存失败: {e}")
    
    return {}
