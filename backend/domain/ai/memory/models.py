"""
统一记忆模块数据模型
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConversationTurn:
    """单轮对话记录"""
    
    # 对话内容
    user_input: str
    assistant_output: str
    
    # 元数据
    intent_type: str  # rag_query / doc_advise / doc_edit / doc_format / chitchat
    permission_mode: str  # assistant / editor
    document_ref: str | None = None  # 文档引用 (文件名)
    
    # 扩展信息
    tool_calls: list[str] = field(default_factory=list)
    retrieval_sources: list[str] = field(default_factory=list)  # RAG 检索来源
    
    # 标识信息
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式用于存储"""
        return {
            "type": "turn",
            "turn_id": self.turn_id,
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "assistant_output": self.assistant_output,
            "intent_type": self.intent_type,
            "permission_mode": self.permission_mode,
            "document_ref": self.document_ref,
            "tool_calls": self.tool_calls,
            "retrieval_sources": self.retrieval_sources,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationTurn:
        """从字典格式恢复"""
        return cls(
            turn_id=data.get("turn_id", str(uuid.uuid4())[:8]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            user_input=data["user_input"],
            assistant_output=data["assistant_output"],
            intent_type=data.get("intent_type", "chitchat"),
            permission_mode=data.get("permission_mode", "assistant"),
            document_ref=data.get("document_ref"),
            tool_calls=data.get("tool_calls", []),
            retrieval_sources=data.get("retrieval_sources", []),
        )
    
    def format_for_display(self) -> str:
        """格式化为可读字符串"""
        meta_parts = [f"[{self.intent_type}]"]
        if self.document_ref:
            meta_parts.append(f"文档: {self.document_ref}")
        meta = " ".join(meta_parts)
        return f"{meta}\nUser: {self.user_input}\nAssistant: {self.assistant_output}"


@dataclass
class HistorySummary:
    """历史摘要"""
    
    content: str  # 摘要内容
    covered_turns: int  # 覆盖的轮次数
    topics: list[str] = field(default_factory=list)  # 涉及的主题/文档
    
    # 标识信息
    summary_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式用于存储"""
        return {
            "type": "summary",
            "summary_id": self.summary_id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "covered_turns": self.covered_turns,
            "topics": self.topics,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistorySummary:
        """从字典格式恢复"""
        return cls(
            summary_id=data.get("summary_id", str(uuid.uuid4())[:8]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            content=data["content"],
            covered_turns=data.get("covered_turns", 0),
            topics=data.get("topics", []),
        )
