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


class RAGRequest(BaseModel):
    """RAG 问答请求模型"""
    question: str
    top_k: int = 3  # 返回的最相关文档数量


class RAGAgentRequest(BaseModel):
    """RAG Agent 请求模型（已废弃，使用 UnifiedAgentRequest）"""
    question: str
    top_k: int = 3  # 检索数量
    max_rounds: int = 3  # 最大检索轮次
    note_context: str | None = None  # 当前笔记上下文（可选）


class UnifiedAgentRequest(BaseModel):
    """统一 Agent 请求模型"""
    user_input: str                          # 用户输入
    session_id: str = ""                     # 会话 ID
    permission_mode: str = "assistant"       # 权限模式: assistant / editor
    document_content: str | None = None      # 文档内容（可选）
    document_name: str | None = None         # 文档名称（可选）
    top_k: int = 3                           # RAG 检索 fallback 数量（仅在 rerank 失败时使用）
    max_rounds: int = 3                      # RAG 最大检索轮次
