"""
文档检查节点
检查是否有文档上下文
"""
from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def check_document(
    state: UnifiedAgentState,
) -> dict:
    """
    文档检查节点
    
    检查文档操作所需的文档是否存在
    
    Args:
        state: Agent 状态
        
    Returns:
        更新后的状态字段: should_end, end_reason
    """
    document_content = state.get("document_content")
    document_name = state.get("document_name")
    needs_doc = state.get("needs_doc", False)
    
    output_messages: list[OutputMessage] = []
    
    # 如果不需要文档，直接通过
    if not needs_doc:
        return {
            "should_end": False,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    
    # 检查文档是否存在
    has_document = bool(document_content and document_content.strip())
    
    if has_document:
        output_messages.append({
            "type": "thinking",
            "content": f"已获取文档: {document_name or '未命名文档'}",
            "data": None
        })
        logger.info(f"[Unified Agent] 文档检查通过: {document_name}")
        
        return {
            "should_end": False,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    else:
        logger.info("[Unified Agent] 文档检查: 需要文档但未提供")
        
        return {
            "should_end": True,
            "end_reason": "prompt_doc",
            "output_messages": state.get("output_messages", []) + output_messages
        }


async def prompt_document(
    state: UnifiedAgentState,
) -> dict:
    """
    提示选择文档节点
    
    当需要文档但未提供时，生成提示消息
    
    Args:
        state: Agent 状态
        
    Returns:
        更新后的状态字段
    """
    intent_type = state.get("intent_type", "doc_advise")
    
    intent_descriptions = {
        "doc_advise": "分析文档并提供建议",
        "doc_edit": "编辑文档内容",
        "doc_format": "格式化文档"
    }
    
    description = intent_descriptions.get(intent_type, "执行此操作")
    
    prompt_message = (
        f"您的请求需要{description}，但当前没有选择文档。\n\n"
        "请先打开一个文档，然后再提出您的问题。"
    )
    
    output_messages: list[OutputMessage] = [
        {
            "type": "prompt",
            "content": prompt_message,
            "data": {"reason": "no_document", "required_for": intent_type}
        }
    ]
    
    logger.info(f"[Unified Agent] 提示用户选择文档")
    
    return {
        "final_output": prompt_message,
        "output_messages": state.get("output_messages", []) + output_messages
    }
