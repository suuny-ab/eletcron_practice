"""
文档格式化节点
格式化文档排版，输出 Diff
"""
from collections.abc import AsyncGenerator

from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def format_document(
    state: UnifiedAgentState,
    llm_task_service,
) -> AsyncGenerator[dict, None]:
    """
    文档格式化节点
    
    格式化文档排版，输出 Diff 格式
    
    Args:
        state: Agent 状态
        llm_task_service: LLM 任务服务实例
        
    Yields:
        流式输出消息
    """
    document_content = state.get("document_content", "")
    
    # 发送状态消息
    yield {
        "type": "status",
        "content": "正在格式化文档...",
        "data": {"stage": "formatting"}
    }
    
    try:
        # 调用 optimize 任务
        chunks: list[str] = []
        async for chunk in llm_task_service.stream(
            task_type="optimize",
            content=document_content
        ):
            chunks.append(chunk)
            yield {
                "type": "chunk",
                "content": chunk,
                "data": None
            }
        
        # 生成 Diff
        formatted_content = "".join(chunks)
        diff_output = _generate_diff(document_content, formatted_content)
        
        yield {
            "type": "diff",
            "content": diff_output,
            "data": {
                "format": "unified_diff",
                "original_length": len(document_content),
                "formatted_length": len(formatted_content),
                "formatted_content": formatted_content
            }
        }
        
        logger.info("[Unified Agent] 文档格式化完成")
        
    except Exception as e:
        logger.error(f"[Unified Agent] 文档格式化失败: {e}")
        yield {
            "type": "error",
            "content": f"格式化失败: {str(e)}",
            "data": None
        }


def _generate_diff(original: str, formatted: str) -> str:
    """生成 unified diff 格式"""
    import difflib
    
    original_lines = original.splitlines(keepends=True)
    formatted_lines = formatted.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        formatted_lines,
        fromfile="原文档",
        tofile="格式化后",
        lineterm=""
    )
    
    return "\n".join(diff)
