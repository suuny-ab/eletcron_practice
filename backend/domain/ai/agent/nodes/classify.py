"""
意图分类节点
负责识别用户意图，决定后续流程分支
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from ..state import UnifiedAgentState, OutputMessage
from ..prompts.classify_prompt import CLASSIFY_INTENT_PROMPT
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def classify_intent(
    state: UnifiedAgentState,
    chat_model,
) -> dict:
    """
    意图分类节点
    
    分析用户输入，判断意图类型和所需资源
    
    Args:
        state: Agent 状态
        chat_model: 聊天模型实例
        
    Returns:
        更新后的状态字段: intent_type, needs_rag, needs_doc
    """
    user_input = state["user_input"]
    document_name = state.get("document_name") or "无"
    history_summary = state.get("history_summary") or "无"
    
    # 发送状态消息
    output_messages: list[OutputMessage] = [
        {"type": "status", "content": "正在分析意图...", "data": {"stage": "classifying"}}
    ]
    
    try:
        # 构建 prompt
        prompt = ChatPromptTemplate.from_template(CLASSIFY_INTENT_PROMPT)
        chain = prompt | chat_model
        
        # 调用 LLM
        response = await chain.ainvoke({
            "user_input": user_input,
            "document_name": document_name,
            "history_summary": history_summary[:500] if history_summary else "无"
        })
        
        # 解析响应
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取 JSON
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        
        result = json.loads(json_str.strip())
        
        intent_type = result.get("intent_type", "chitchat")
        needs_rag = result.get("needs_rag", False)
        needs_doc = result.get("needs_doc", False)
        reasoning = result.get("reasoning", "")
        
        # 发送思考消息
        output_messages.append({
            "type": "thinking",
            "content": f"意图识别: {intent_type}。{reasoning}",
            "data": None
        })
        
        logger.info(
            f"[Unified Agent] 意图分类完成: intent={intent_type}, "
            f"needs_rag={needs_rag}, needs_doc={needs_doc}"
        )
        
        return {
            "intent_type": intent_type,
            "needs_rag": needs_rag,
            "needs_doc": needs_doc,
            "output_messages": state.get("output_messages", []) + output_messages
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[Unified Agent] 意图分类 JSON 解析失败: {e}")
        # 降级处理：根据是否有文档判断
        has_doc = bool(state.get("document_content"))
        fallback_intent = "doc_advise" if has_doc else "rag_query"
        
        output_messages.append({
            "type": "thinking",
            "content": f"意图解析异常，默认为 {fallback_intent}",
            "data": None
        })
        
        return {
            "intent_type": fallback_intent,
            "needs_rag": not has_doc,
            "needs_doc": has_doc,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    except Exception as e:
        logger.error(f"[Unified Agent] 意图分类失败: {e}")
        raise
