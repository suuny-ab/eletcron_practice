"""
权限检查节点
检查当前权限模式是否满足操作需求
"""
from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

# 各意图所需的最低权限
INTENT_PERMISSION_MAP = {
    "chitchat": "assistant",
    "rag_query": "assistant",
    "doc_advise": "assistant",
    "doc_edit": "editor",
    "doc_format": "editor",
}


async def check_permission(
    state: UnifiedAgentState,
) -> dict:
    """
    权限检查节点
    
    检查当前权限模式是否满足意图需求
    
    Args:
        state: Agent 状态
        
    Returns:
        更新后的状态字段: should_end, end_reason
    """
    intent_type = state.get("intent_type", "chitchat")
    permission_mode = state.get("permission_mode", "assistant")
    
    required_permission = INTENT_PERMISSION_MAP.get(intent_type, "assistant")
    
    # assistant < editor
    permission_levels = {"assistant": 0, "editor": 1}
    current_level = permission_levels.get(permission_mode, 0)
    required_level = permission_levels.get(required_permission, 0)
    
    if current_level >= required_level:
        logger.info(
            f"[Unified Agent] 权限检查通过: intent={intent_type}, "
            f"mode={permission_mode}"
        )
        return {
            "should_end": False,
            "output_messages": state.get("output_messages", [])
        }
    else:
        logger.info(
            f"[Unified Agent] 权限不足: intent={intent_type}, "
            f"mode={permission_mode}, required={required_permission}"
        )
        return {
            "should_end": True,
            "end_reason": "suggest_mode",
            "output_messages": state.get("output_messages", [])
        }


async def suggest_mode_switch(
    state: UnifiedAgentState,
) -> dict:
    """
    权限切换提示节点
    
    当权限不足时，提示用户切换到编辑模式
    
    Args:
        state: Agent 状态
        
    Returns:
        更新后的状态字段
    """
    intent_type = state.get("intent_type", "doc_edit")
    
    intent_labels = {
        "doc_edit": "编辑文档",
        "doc_format": "格式化文档"
    }
    
    label = intent_labels.get(intent_type, "执行此操作")
    
    suggest_message = (
        f"您的请求需要{label}，这需要编辑权限。\n\n"
        "请切换到编辑模式后再试。"
    )
    
    output_messages: list[OutputMessage] = [
        {
            "type": "prompt",
            "content": suggest_message,
            "data": {
                "reason": "permission_denied",
                "current_mode": state.get("permission_mode", "assistant"),
                "required_mode": "editor",
                "intent_type": intent_type
            }
        }
    ]
    
    logger.info(f"[Unified Agent] 提示切换到编辑模式")
    
    return {
        "final_output": suggest_message,
        "output_messages": state.get("output_messages", []) + output_messages
    }
