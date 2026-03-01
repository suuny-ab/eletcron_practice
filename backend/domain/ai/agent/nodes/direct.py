"""
直接回答节点
处理不需要检索的情况
"""
from collections.abc import AsyncGenerator

from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def direct_answer(
    state: UnifiedAgentState,
    chat_model,
) -> AsyncGenerator[dict, None]:
    """
    直接回答节点
    
    用于闲聊类问题，不需要检索知识库
    
    Args:
        state: Agent 状态
        chat_model: 聊天模型实例
        
    Yields:
        流式输出消息
    """
    question = state["user_input"]
    
    # 发送状态消息
    yield {
        "type": "status",
        "content": "正在生成回答...",
        "data": {"stage": "generating"}
    }
    
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="你是一个友好的AI助手。请简洁、友好地回答用户的问题。"),
            HumanMessage(content=question)
        ]
        
        # 流式生成
        async for chunk in chat_model.astream(messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                yield {
                    "type": "chunk",
                    "content": content,
                    "data": None
                }
        
        logger.info(f"[RAG Agent] 直接回答完成")
        
    except Exception as e:
        logger.error(f"[RAG Agent] 直接回答失败: {e}")
        yield {
            "type": "error",
            "content": f"回答生成失败: {str(e)}",
            "data": None
        }


async def ask_clarification(
    state: UnifiedAgentState,
) -> dict:
    """
    追问澄清节点
    
    当问题不够清晰时，请求用户澄清
    
    Args:
        state: Agent 状态
        
    Returns:
        更新后的状态字段
    """
    analysis = state.get("analysis", {})
    reasoning = analysis.get("reasoning", "")
    
    clarification_message = (
        "您的问题不够清晰，我需要更多信息才能准确回答。"
        f"\n\n{reasoning}"
        "\n\n请您补充更多细节，例如：\n"
        "- 您具体想了解哪个方面？\n"
        "- 是否可以提供更多上下文？"
    )
    
    output_messages: list[OutputMessage] = [
        {
            "type": "chunk",
            "content": clarification_message,
            "data": None
        }
    ]
    
    logger.info(f"[RAG Agent] 请求用户澄清")
    
    return {
        "final_answer": clarification_message,
        "output_messages": state.get("output_messages", []) + output_messages
    }
