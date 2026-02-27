"""
流式响应数据模型
定义流式输出的数据结构和JSON格式
"""
from pydantic import BaseModel
from typing import Literal


class StreamChunk(BaseModel):
    """流式内容片段模型
    
    用于包装AI生成的文本片段
    
    Attributes:
        type: 固定为"chunk"，表示这是内容片段
        content: 文本内容
    """
    type: Literal["chunk"] = "chunk"
    content: str


class StreamComplete(BaseModel):
    """流式完成状态模型
    
    表示流式输出已完成
    
    Attributes:
        type: 固定为"complete"，表示完成状态
        status: 状态，默认为"done"
    """
    type: Literal["complete"] = "complete"
    status: str = "done"


class StreamError(BaseModel):
    """流式错误信息模型
    
    用于包装流式输出过程中的错误信息
    
    Attributes:
        type: 固定为"error"，表示错误信息
        message: 错误消息
    """
    type: Literal["error"] = "error"
    message: str
