"""
文档编辑节点
生成文档编辑 Diff
"""
from collections.abc import AsyncGenerator

from ..state import UnifiedAgentState, OutputMessage
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


async def edit_document(
    state: UnifiedAgentState,
    llm_task_service,
) -> AsyncGenerator[dict, None]:
    """
    文档编辑节点
    
    根据用户要求编辑文档，输出 Diff 格式
    
    Args:
        state: Agent 状态
        llm_task_service: LLM 任务服务实例
        
    Yields:
        流式输出消息
    """
    user_input = state["user_input"]
    document_content = state.get("document_content", "")
    
    # 发送状态消息
    yield {
        "type": "status",
        "content": "正在编辑文档...",
        "data": {"stage": "editing"}
    }
    
    try:
        # 调用 edit 任务
        chunks: list[str] = []
        async for chunk in llm_task_service.stream(
            task_type="edit",
            content=document_content,
            requirement=user_input
        ):
            chunks.append(chunk)
            yield {
                "type": "chunk",
                "content": chunk,
                "data": None
            }
        
        # 生成 Diff
        edited_content = "".join(chunks)
        diff_output = _generate_diff(document_content, edited_content)
        
        yield {
            "type": "diff",
            "content": diff_output,
            "data": {
                "format": "unified_diff",
                "original_length": len(document_content),
                "edited_length": len(edited_content),
                "edited_content": edited_content
            }
        }
        
        logger.info("[Unified Agent] 文档编辑完成")
        
    except Exception as e:
        logger.error(f"[Unified Agent] 文档编辑失败: {e}")
        yield {
            "type": "error",
            "content": f"编辑失败: {str(e)}",
            "data": None
        }


def _generate_diff(original: str, edited: str) -> str:
    """生成 unified diff 格式"""
    import difflib
    
    original_lines = original.splitlines(keepends=True)
    edited_lines = edited.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        edited_lines,
        fromfile="原文档",
        tofile="修改后",
        lineterm=""
    )
    
    return "\n".join(diff)
