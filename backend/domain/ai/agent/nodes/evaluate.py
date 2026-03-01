"""
结果评估节点
负责评估检索结果是否足够回答问题
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from ..state import UnifiedAgentState, EvaluationResult, OutputMessage
from ..prompts import RETRIEVAL_EVALUATE_PROMPT
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def evaluate_results(
    state: UnifiedAgentState,
    chat_model,
) -> dict:
    """
    结果评估节点
    
    评估检索结果是否足够回答问题
    
    Args:
        state: Agent 状态
        chat_model: 聊天模型实例
        
    Returns:
        更新后的状态字段
    """
    question = state["user_input"]
    current_round = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 3)
    all_sources = state.get("all_sources", [])
    
    # 发送状态消息
    output_messages: list[OutputMessage] = [
        {
            "type": "status",
            "content": "正在评估检索结果...",
            "data": {"stage": "evaluating"}
        }
    ]
    
    # 如果没有检索结果
    if not all_sources:
        evaluation: EvaluationResult = {
            "is_sufficient": False,
            "confidence": 0.0,
            "reasoning": "未检索到任何相关内容",
            "missing_aspects": ["所有相关内容"],
            "suggestion": "retry" if current_round < max_rounds else "give_up"
        }
        output_messages.append({
            "type": "thinking",
            "content": "未检索到相关内容",
            "data": None
        })
        return {
            "evaluation": evaluation,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    
    try:
        # 构建检索内容摘要
        retrieved_content = "\n\n".join([
            f"【来源: {s['filename']}】\n{s['content'][:500]}..."
            if len(s['content']) > 500 else f"【来源: {s['filename']}】\n{s['content']}"
            for s in all_sources
        ])
        
        # 构建 prompt
        prompt = ChatPromptTemplate.from_template(RETRIEVAL_EVALUATE_PROMPT)
        chain = prompt | chat_model
        
        # 调用 LLM
        response = await chain.ainvoke({
            "question": question,
            "current_round": current_round,
            "max_rounds": max_rounds,
            "retrieved_content": retrieved_content[:3000]  # 限制长度
        })
        
        # 解析响应
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取 JSON
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
            
        evaluation: EvaluationResult = json.loads(json_str.strip())
        
        # 如果已达到最大轮次，强制调整建议
        if current_round >= max_rounds and evaluation.get("suggestion") == "retry":
            evaluation["suggestion"] = "give_up"
        
        # 发送思考消息
        output_messages.append({
            "type": "thinking",
            "content": evaluation.get("reasoning", ""),
            "data": None
        })
        
        logger.info(
            f"[RAG Agent] 评估完成: is_sufficient={evaluation.get('is_sufficient')}, "
            f"suggestion={evaluation.get('suggestion')}"
        )
        
        return {
            "evaluation": evaluation,
            "output_messages": state.get("output_messages", []) + output_messages
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[RAG Agent] 评估 JSON 解析失败: {e}")
        # 降级处理：继续生成答案
        fallback_evaluation: EvaluationResult = {
            "is_sufficient": True,
            "confidence": 0.5,
            "reasoning": "JSON解析失败，默认继续生成答案",
            "missing_aspects": [],
            "suggestion": "proceed"
        }
        return {
            "evaluation": fallback_evaluation,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    except Exception as e:
        logger.error(f"[RAG Agent] 评估失败: {e}")
        fallback_evaluation: EvaluationResult = {
            "is_sufficient": True,
            "confidence": 0.3,
            "reasoning": f"评估异常: {e}",
            "missing_aspects": [],
            "suggestion": "proceed"
        }
        return {
            "evaluation": fallback_evaluation,
            "output_messages": state.get("output_messages", []) + output_messages
        }
