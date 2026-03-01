"""
查询重构节点
负责基于评估结果重新构造检索查询
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from ..state import UnifiedAgentState, OutputMessage
from ..prompts import QUERY_REWRITE_PROMPT
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def rewrite_query(
    state: UnifiedAgentState,
    chat_model,
) -> dict:
    """
    查询重构节点
    
    基于评估结果重新构造检索查询词
    
    Args:
        state: Agent 状态
        chat_model: 聊天模型实例
        
    Returns:
        更新后的状态字段
    """
    question = state["user_input"]
    all_sources = state.get("all_sources", [])
    evaluation = state.get("evaluation", {})
    missing_aspects = evaluation.get("missing_aspects", [])
    
    # 发送状态消息
    output_messages: list[OutputMessage] = [
        {
            "type": "status",
            "content": "正在优化检索策略...",
            "data": {"stage": "rewriting"}
        }
    ]
    
    try:
        # 构建已检索内容摘要
        retrieved_summary = "\n".join([
            f"- {s['filename']}: {s['content'][:200]}..."
            for s in all_sources[:5]
        ]) if all_sources else "无"
        
        # 构建 prompt
        prompt = ChatPromptTemplate.from_template(QUERY_REWRITE_PROMPT)
        chain = prompt | chat_model
        
        # 调用 LLM
        response = await chain.ainvoke({
            "question": question,
            "retrieved_summary": retrieved_summary,
            "missing_aspects": ", ".join(missing_aspects) if missing_aspects else "未明确"
        })
        
        # 解析响应
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取 JSON
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
            
        rewrite_result = json.loads(json_str.strip())
        new_query = rewrite_result.get("new_query", question)
        
        # 发送思考消息
        output_messages.append({
            "type": "thinking",
            "content": f"重构查询: {rewrite_result.get('reasoning', '')}",
            "data": None
        })
        
        logger.info(
            f"[RAG Agent] 查询重构完成: strategy={rewrite_result.get('strategy')}, "
            f"new_query={new_query}"
        )
        
        return {
            "current_query": new_query,
            "output_messages": state.get("output_messages", []) + output_messages
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[RAG Agent] 查询重构 JSON 解析失败: {e}")
        # 降级处理：使用缺失方面作为新查询
        fallback_query = " ".join(missing_aspects) if missing_aspects else question
        return {
            "current_query": fallback_query,
            "output_messages": state.get("output_messages", []) + output_messages
        }
    except Exception as e:
        logger.error(f"[RAG Agent] 查询重构失败: {e}")
        raise
