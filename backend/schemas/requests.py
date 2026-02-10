"""
Pydantic 模型定义
定义API请求和响应的数据模型
"""
from pydantic import BaseModel


class OptimizeRequest(BaseModel):
    """AI 排版优化请求模型"""
    filename: str


class ChatRequest(BaseModel):
    """AI 聊天请求模型"""
    filename: str
    question: str


class EditRequest(BaseModel):
    """AI 文档编辑请求模型"""
    filename: str
    requirement: str


class SaveRequest(BaseModel):
    """保存文件请求模型"""
    filename: str
    content: str


class UpdateConfigRequest(BaseModel):
    """配置更新请求模型"""
    obsidian_vault_path: str
    api_key: str
    model_name: str
    prompts: dict[str, dict[str, str]] | None = None  # 可选的提示词配置


class FileUpdateRequest(BaseModel):
    """文件更新请求模型"""
    content: str