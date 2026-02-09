"""
Pydantic 模型定义
定义API请求和响应的数据模型
"""

from .requests import ChatRequest, SaveRequest, OptimizeRequest, EditRequest, FileUpdateRequest
from .responses import (
    BaseResponse,
    DataResponse,
    ErrorResponse,
    FileUploadData,
    FileSaveData,
    FileDeleteData,
    FileListData,
    FileListItemData,
    # 旧模型（保留供参考）
    FileUploadResponse,
    FileContentResponse,
    FileSaveResponse,
    FileDeleteResponse,
    FileListItem,
    FileListResponse
)
from .stream_models import StreamChunk, StreamComplete, StreamError

__all__ = [
    'ChatRequest',
    'SaveRequest',
    'OptimizeRequest',
    'EditRequest',
    'FileUpdateRequest',
    # 新的统一响应模型
    'BaseResponse',
    'DataResponse',
    'ErrorResponse',
    # 数据模型
    'FileUploadData',
    'FileSaveData',
    'FileDeleteData',
    'FileListData',
    'FileListItemData',
    # 流式模型
    'StreamChunk',
    'StreamComplete',
    'StreamError',
    # 旧模型（保留供参考，未来将删除）
    'FileUploadResponse',
    'FileContentResponse',
    'FileSaveResponse',
    'FileDeleteResponse',
    'FileListItem',
    'FileListResponse'
]