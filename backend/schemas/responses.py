"""
API响应模型 - 定义API接口的响应数据结构
"""
from pydantic import BaseModel
from typing import Any, Generic, Optional, TypeVar
from datetime import datetime


# ==================== Generic 类型变量 ====================
T = TypeVar('T')


# ==================== 基础响应模型 ====================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    timestamp: str = datetime.now().isoformat()


class DataResponse(BaseModel, Generic[T]):
    """
    带数据的统一响应模型（使用 Generic）
    
    用于包装任意类型的响应数据，提供统一的响应格式。
    
    Type Parameters:
        T: 数据类型（可以是 dict、list、或其他 BaseModel）
    
    Attributes:
        success: 操作是否成功，默认 true
        message: 提示信息，默认"操作成功"
        data: 响应数据，类型为 T
        timestamp: 时间戳

    """
    success: bool = True
    message: str = "操作成功"
    data: T
    timestamp: str = datetime.now().isoformat()


class ErrorResponse(BaseModel):
    """统一错误响应模型"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    timestamp: str = datetime.now().isoformat()


# ==================== 数据模型（只定义数据部分）====================

class FileUploadData(BaseModel):
    """文件上传数据"""
    filename: str
    file_size: int
    file_path: str


class FileSaveData(BaseModel):
    """文件保存数据"""
    filename: str
    file_size: int
    file_path: str


class FileDeleteData(BaseModel):
    """文件删除数据"""
    filename: str
    file_path: str


class FileListItemData(BaseModel):
    """文件列表项数据"""
    filename: str
    file_size: int
    file_path: str
    modified_time: float


class FileListData(BaseModel):
    """文件列表数据"""
    files: list[FileListItemData]


class ConfigData(BaseModel):
    """配置数据"""
    obsidian_vault_path: str
    api_key: str
    model_name: str


# ==================== 旧模型（保留供参考）====================
# 以下模型已弃用，请使用 DataResponse[T] + Data
# 未来版本将删除

class FileUploadResponse(BaseModel):
    """文件上传响应（已弃用，请使用 DataResponse[FileUploadData]）"""
    filename: str
    file_size: int
    file_path: str


class FileContentResponse(BaseModel):
    """包含文件内容的响应（已弃用）"""
    filename: str
    file_size: int
    file_path: str
    content: str


class FileSaveResponse(BaseModel):
    """文件保存响应（已弃用，请使用 DataResponse[FileSaveData]）"""
    message: str
    filename: str
    file_size: int
    file_path: str


class FileDeleteResponse(BaseModel):
    """文件删除响应（已弃用，请使用 DataResponse[FileDeleteData]）"""
    message: str
    filename: str
    file_path: str


class FileListItem(BaseModel):
    """文件列表项（已弃用，请使用 FileListItemData）"""
    filename: str
    file_size: int
    file_path: str
    modified_time: float


class FileListResponse(BaseModel):
    """文件列表响应（已弃用，请使用 DataResponse[FileListData]）"""
    files: list[FileListItem]
