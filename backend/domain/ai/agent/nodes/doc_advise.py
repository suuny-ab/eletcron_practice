"""
文档建议节点
生成文档分析建议
"""
from collections.abc import AsyncGenerator

from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def advise_document(
    state: UnifiedAgentState,
    llm_task_service,
) -> AsyncGenerator[dict, None]:
    """
    文档建议节点
    
    基于文档内容（可结合 RAG 上下文）生成建议
    
    Args:
        state: Agent 状态
        llm_task_service: LLM 任务服务实例
        
    Yields:
        流式输出消息
    """
    user_input = state["user_input"]
    document_content = state.get("document_content", "")
    all_sources = state.get("all_sources", [])
    
    # 发送状态消息
    yield {
        "type": "status",
        "content": "正在分析文档并生成建议...",
        "data": {"stage": "advising"}
    }
    
    try:
        # 如果有 RAG 上下文，拼接到问题中
        question = user_input
        if all_sources:
            rag_context = "\n\n".join([
                f"参考资料（{s['filename']}）：\n{s['content']}"
                for s in all_sources
            ])
            question = f"{user_input}\n\n以下是从知识库检索到的参考资料：\n{rag_context}"
        
        # 如果有 RAG 来源，先发送
        if all_sources:
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
        
        # 调用 advise 任务
        chunks: list[str] = []
        async for chunk in llm_task_service.stream(
            task_type="advise",
            content=document_content,
            question=question
        ):
            chunks.append(chunk)
            yield {
                "type": "chunk",
                "content": chunk,
                "data": None
            }
        
        logger.info("[Unified Agent] 文档建议生成完成")
        
    except Exception as e:
        logger.error(f"[Unified Agent] 文档建议生成失败: {e}")
        yield {
            "type": "error",
            "content": f"建议生成失败: {str(e)}",
            "data": None
        }
