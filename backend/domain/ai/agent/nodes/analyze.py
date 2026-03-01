"""
问题分析节点
负责分析用户问题类型，决定后续流程
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from ..state import UnifiedAgentState, AnalysisResult, OutputMessage
from ..prompts import QUESTION_ANALYZE_PROMPT
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def analyze_question(
    state: UnifiedAgentState,
    chat_model,
) -> dict:
    """
    问题分析节点
    
    分析用户问题类型，判断是否需要检索
    
    Args:
        state: Agent 状态
        chat_model: 聊天模型实例
        
    Returns:
        更新后的状态字段
    """
    question = state["user_input"]
    note_context = state.get("document_content") or "无"
    
    # 发送状态消息
    output_messages: list[OutputMessage] = [
        {"type": "status", "content": "正在分析问题...", "data": {"stage": "analyzing"}}
    ]
    
    try:
        # 构建 prompt
        prompt = ChatPromptTemplate.from_template(QUESTION_ANALYZE_PROMPT)
        chain = prompt | chat_model
        
        # 调用 LLM
        response = await chain.ainvoke({
            "question": question,
            "note_context": note_context[:1000] if note_context else "无"
        })
        
        # 解析响应
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取 JSON
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
            
        analysis: AnalysisResult = json.loads(json_str.strip())
        
        # 发送思考消息
        output_messages.append({
            "type": "thinking",
            "content": analysis.get("reasoning", ""),
            "data": None
        })
        
        logger.info(
            f"[RAG Agent] 问题分析完成: type={analysis.get('question_type')}, "
            f"should_retrieve={analysis.get('should_retrieve')}"
        )
        
        return {
            "analysis": analysis,
            "current_query": analysis.get("initial_query", question),
            "output_messages": state.get("output_messages", []) + output_messages
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[RAG Agent] 问题分析 JSON 解析失败: {e}")
        # 降级处理：默认为知识查询
        fallback_analysis: AnalysisResult = {
            "question_type": "knowledge_query",
            "reasoning": "JSON解析失败，默认为知识查询",
            "should_retrieve": True,
            "key_entities": [],
            "initial_query": question
        }
        output_messages.append({
            "type": "thinking",
            "content": "分析结果解析异常，默认进行知识检索",
            "data": None
        })
        return {
            "analysis": fallback_analysis,
            "current_query": question,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    except Exception as e:
        logger.error(f"[RAG Agent] 问题分析失败: {e}")
        fallback_analysis: AnalysisResult = {
            "question_type": "knowledge_query",
            "reasoning": f"分析异常: {e}",
            "should_retrieve": True,
            "key_entities": [],
            "initial_query": question
        }
        output_messages.append({
            "type": "thinking",
            "content": "问题分析异常，默认进行知识检索",
            "data": None
        })
        return {
            "analysis": fallback_analysis,
            "current_query": question,
            "output_messages": state.get("output_messages", []) + output_messages
        }
