"""
API响应模型 - 定义API接口的响应数据结构
"""
from pydantic import BaseModel
from typing import Generic, TypeVar
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
    error_code: str | None = None
    timestamp: str = datetime.now().isoformat()


# ==================== 数据模型（只定义数据部分）====================

class FileReadResult(BaseModel):
    """文件读取结果"""
    success: bool
    filename: str
    file_size: int
    file_path: str
    content: str


class FileWriteResult(BaseModel):
    """文件写入结果"""
    success: bool
    filename: str
    file_size: int
    file_path: str


class ConfigData(BaseModel):
    """配置数据"""
    obsidian_vault_path: str
    api_key: str
    model_name: str


class FileTreeNode(BaseModel):
    """文件树节点"""
    key: str
    title: str
    is_leaf: bool
    children: list['FileTreeNode'] | None = None


class FileTreeData(BaseModel):
    """文件树数据"""
    tree: list[FileTreeNode]

