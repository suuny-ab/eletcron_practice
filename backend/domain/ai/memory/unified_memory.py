"""
统一记忆管理器
负责全局对话历史的存储、读取和摘要滚动
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Awaitable, Callable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .models import ConversationTurn, HistorySummary

SUMMARY_PREFIX = "历史摘要：\n"


class UnifiedMemoryManager:
    """统一记忆管理器
    
    特性:
    - 全局共享历史（跨文档、跨操作类型）
    - 仅存储元数据（问答 + 操作类型 + 文档引用）
    - 20 轮对话后触发摘要滚动
    - 细粒度摘要生成
    """
    
    def __init__(
        self,
        session_id: str = "default",
        base_dir: Path | None = None,
        max_history_rounds: int = 20,
        trim_rounds: int = 6,
        summarizer: Callable[[str | None, list[ConversationTurn]], Awaitable[str]] | None = None
    ):
        """初始化记忆管理器
        
        Args:
            session_id: 会话标识，用于隔离不同会话的历史
            base_dir: 存储目录，默认为 .data/ai_sessions/
            max_history_rounds: 最大历史轮数，超过后触发摘要
            trim_rounds: 每次摘要压缩的轮数
            summarizer: 摘要生成函数
        """
        self.session_id = session_id
        backend_dir = Path(__file__).resolve().parents[3]
        self.base_dir = base_dir or (backend_dir / ".data" / "ai_sessions")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 按 session_id 隔离历史文件
        safe_id = session_id.replace("/", "_").replace("\\", "_") if session_id else "default"
        self.history_file = self.base_dir / f"{safe_id}.jsonl"
        self.max_history_rounds = max_history_rounds
        self.trim_rounds = trim_rounds
        self.summarizer = summarizer
    
    async def get_history(self) -> tuple[HistorySummary | None, list[ConversationTurn]]:
        """获取历史记录
        
        Returns:
            (摘要, 近期轮次列表)
        """
        return self._load()
    
    async def add_turn(self, turn: ConversationTurn) -> None:
        """添加新轮次
        
        自动检查是否需要触发摘要滚动
        
        Args:
            turn: 新的对话轮次
        """
        summary, turns = self._load()
        turns.append(turn)
        
        # 检查是否需要摘要滚动
        if self.summarizer and len(turns) > self.max_history_rounds:
            summary, turns = await self._rollup_summary(summary, turns)
        
        self._save(summary, turns)
    
    def get_history_sync(self) -> tuple[HistorySummary | None, list[ConversationTurn]]:
        """同步获取历史记录（用于非异步场景）"""
        return self._load()
    
    def add_turn_sync(self, turn: ConversationTurn) -> None:
        """同步添加轮次（不触发摘要滚动）"""
        summary, turns = self._load()
        turns.append(turn)
        self._save(summary, turns)
    
    def clear(self) -> None:
        """清空历史记录"""
        if self.history_file.exists():
            self.history_file.unlink()
    
    def format_for_langchain(
        self,
        summary: HistorySummary | None,
        turns: list[ConversationTurn]
    ) -> list[BaseMessage]:
        """格式化为 LangChain 消息列表
        
        Args:
            summary: 历史摘要
            turns: 近期轮次
            
        Returns:
            LangChain BaseMessage 列表
        """
        messages: list[BaseMessage] = []
        
        # 添加摘要作为系统消息
        if summary:
            messages.append(SystemMessage(content=f"{SUMMARY_PREFIX}{summary.content}"))
        
        # 添加近期轮次
        for turn in turns:
            # 构建带元数据的用户消息
            user_content = turn.user_input
            if turn.document_ref:
                user_content = f"[文档: {turn.document_ref}] {user_content}"
            
            messages.append(HumanMessage(content=user_content))
            messages.append(AIMessage(content=turn.assistant_output))
        
        return messages
    
    def format_for_prompt(
        self,
        summary: HistorySummary | None,
        turns: list[ConversationTurn]
    ) -> str:
        """格式化为纯文本提示词
        
        Args:
            summary: 历史摘要
            turns: 近期轮次
            
        Returns:
            格式化的历史文本
        """
        parts: list[str] = []
        
        if summary:
            parts.append(f"## 历史摘要\n{summary.content}")
        
        if turns:
            recent_parts = ["## 近期对话"]
            for turn in turns:
                meta = f"[{turn.intent_type}]"
                if turn.document_ref:
                    meta += f" 文档: {turn.document_ref}"
                recent_parts.append(f"{meta}\nUser: {turn.user_input}\nAssistant: {turn.assistant_output}")
            parts.append("\n\n".join(recent_parts))
        
        return "\n\n".join(parts) if parts else ""
    
    def _load(self) -> tuple[HistorySummary | None, list[ConversationTurn]]:
        """从文件加载历史"""
        if not self.history_file.exists():
            return None, []
        
        summary: HistorySummary | None = None
        turns: list[ConversationTurn] = []
        
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                record_type = record.get("type")
                if record_type == "summary":
                    summary = HistorySummary.from_dict(record)
                elif record_type == "turn":
                    turns.append(ConversationTurn.from_dict(record))
        
        return summary, turns
    
    def _save(self, summary: HistorySummary | None, turns: list[ConversationTurn]) -> None:
        """保存历史到文件"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.history_file, "w", encoding="utf-8") as f:
            # 先写摘要
            if summary:
                f.write(json.dumps(summary.to_dict(), ensure_ascii=False) + "\n")
            
            # 再写轮次
            for turn in turns:
                f.write(json.dumps(turn.to_dict(), ensure_ascii=False) + "\n")
    
    async def _rollup_summary(
        self,
        existing_summary: HistorySummary | None,
        turns: list[ConversationTurn]
    ) -> tuple[HistorySummary | None, list[ConversationTurn]]:
        """执行摘要滚动
        
        当历史轮数超过 max_history_rounds 时，
        将最早的 trim_rounds 轮压缩为摘要
        """
        while len(turns) > self.max_history_rounds:
            # 取出最早的 trim_rounds 轮
            old_turns = turns[:self.trim_rounds]
            turns = turns[self.trim_rounds:]
            
            if not old_turns:
                break
            
            # 提取涉及的主题/文档
            topics = set()
            if existing_summary:
                topics.update(existing_summary.topics)
            for turn in old_turns:
                if turn.document_ref:
                    topics.add(turn.document_ref)
                topics.add(turn.intent_type)
            
            # 生成新摘要
            existing_content = existing_summary.content if existing_summary else None
            new_summary_content = await self.summarizer(existing_content, old_turns)
            
            # 计算覆盖的总轮数
            covered = (existing_summary.covered_turns if existing_summary else 0) + len(old_turns)
            
            existing_summary = HistorySummary(
                content=new_summary_content,
                covered_turns=covered,
                topics=list(topics)
            )
        
        return existing_summary, turns
