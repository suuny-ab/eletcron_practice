"""
答案生成节点
负责基于检索结果生成最终答案
"""
from collections.abc import AsyncGenerator

from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def generate_answer(
    state: UnifiedAgentState,
    llm_task_service,
) -> AsyncGenerator[dict, None]:
    """
    答案生成节点
    
    基于检索结果流式生成答案
    
    Args:
        state: Agent 状态
        llm_task_service: LLM 任务服务实例
        
    Yields:
        流式输出消息
    """
    question = state["user_input"]
    all_sources = state.get("all_sources", [])
    
    # 发送来源消息（所有检索完成后统一发送）
    yield {
        "type": "sources",
        "content": None,
        "data": [
            {
                "filename": s["filename"],
                "content": s["content"][:300] + "..." if len(s["content"]) > 300 else s["content"],
                "score": s["score"]
            }
            for s in all_sources
        ]
    }
    
    # 发送状态消息
    yield {
        "type": "status",
        "content": "正在生成答案...",
        "data": {"stage": "generating"}
    }
    
    try:
        # 构建上下文
        context = "\n\n".join([
            f"参考资料 {i+1}（来自 {s['filename']}）：\n{s['content']}"
            for i, s in enumerate(all_sources)
        ]) if all_sources else ""
        
        # 调用 LLM 流式生成
        async for chunk in llm_task_service.stream(
            task_type="rag_qa",
            question=question,
            context=context
        ):
            yield {
                "type": "chunk",
                "content": chunk,
                "data": None
            }
        
        logger.info(f"[RAG Agent] 答案生成完成")
        
    except Exception as e:
        logger.error(f"[RAG Agent] 答案生成失败: {e}")
        yield {
            "type": "error",
            "content": f"答案生成失败: {str(e)}",
            "data": None
        }
