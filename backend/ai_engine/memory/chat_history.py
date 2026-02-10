"""
文件会话历史存储（LangChain 版）
负责 jsonl 持久化 + 摘要滚动
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, SystemMessage, message_to_dict, messages_from_dict

SUMMARY_PREFIX = "历史摘要：\n"


class FileChatMessageHistory(BaseChatMessageHistory):
    """基于 jsonl 的会话历史存储"""

    def __init__(
        self,
        session_id: str,
        base_dir: Path | None = None,
        max_history_rounds: int = 20,
        trim_rounds: int = 6,
        summarizer: Callable[[str | None, list[BaseMessage]], Awaitable[str]] | None = None
    ):
        self.session_id = session_id
        backend_dir = Path(__file__).resolve().parents[1]
        self.base_dir = base_dir or (backend_dir / "data" / "ai_sessions")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_history_rounds = max_history_rounds
        self.trim_rounds = trim_rounds
        self.summarizer = summarizer

    @property
    def messages(self) -> list[BaseMessage]:
        summary, history = self._load()
        if summary:
            return [SystemMessage(content=f"{SUMMARY_PREFIX}{summary}")] + history
        return history

    def clear(self) -> None:
        session_path = self._get_session_path()
        session_path.parent.mkdir(parents=True, exist_ok=True)
        with open(session_path, "w", encoding="utf-8") as f:
            f.write("")

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        summary, history = self._load()
        history.extend(messages)

        if self.summarizer:
            summary, history = await self._rollup_summary(summary, history)

        self._save(summary, history)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        # 兜底同步写入（不做摘要滚动）
        summary, history = self._load()
        history.extend(messages)
        self._save(summary, history)

    def _get_session_path(self) -> Path:
        return self.base_dir / f"{self.session_id}.jsonl"

    def _load(self) -> tuple[str | None, list[BaseMessage]]:
        session_path = self._get_session_path()
        if not session_path.exists():
            return None, []

        summary: str | None = None
        history: list[BaseMessage] = []

        with open(session_path, "r", encoding="utf-8") as f:
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
                    summary = record.get("content")
                elif record_type == "message":
                    msg_dict = record.get("message")
                    if msg_dict:
                        history.extend(messages_from_dict([msg_dict]))

        return summary, history

    def _save(self, summary: str | None, history: list[BaseMessage]) -> None:
        session_path = self._get_session_path()
        session_path.parent.mkdir(parents=True, exist_ok=True)

        with open(session_path, "w", encoding="utf-8") as f:
            if summary:
                f.write(json.dumps(self._build_summary_record(summary), ensure_ascii=False) + "\n")

            for msg in history:
                record = self._build_message_record(msg)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def _rollup_summary(
        self,
        summary: str | None,
        history: list[BaseMessage]
    ) -> tuple[str | None, list[BaseMessage]]:
        rounds = self._count_rounds(history)
        if rounds <= self.max_history_rounds:
            return summary, history

        while rounds > self.max_history_rounds:
            old_part, history = self._trim_by_rounds(history)
            if not old_part:
                break
            summary = await self.summarizer(summary, old_part)  # type: ignore[arg-type]
            rounds = self._count_rounds(history)

        return summary, history

    def _trim_by_rounds(self, history: list[BaseMessage]) -> tuple[list[BaseMessage], list[BaseMessage]]:
        rounds = 0
        cutoff_index = 0
        for index, msg in enumerate(history):
            if msg.type == "ai":
                rounds += 1
                if rounds >= self.trim_rounds:
                    cutoff_index = index + 1
                    break

        if cutoff_index == 0:
            return [], history

        return history[:cutoff_index], history[cutoff_index:]

    @staticmethod
    def _count_rounds(history: list[BaseMessage]) -> int:
        return sum(1 for msg in history if msg.type == "ai")

    @staticmethod
    def _build_summary_record(summary: str) -> dict:
        return {
            "type": "summary",
            "content": summary,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def _build_message_record(message: BaseMessage) -> dict:
        return {
            "type": "message",
            "message": message_to_dict(message),
            "timestamp": datetime.now().isoformat()
        }
