"""
文本切分器
负责文本的各种切分策略
"""
import re
from typing import Literal, TypedDict

LIST_ITEM_PATTERN = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+")


class SplitBlock(TypedDict):
    """切分中间结构单元，用于标识保护块/普通文本"""
    type: Literal["normal", "protected"]
    kind: Literal["normal", "code", "table", "quote"]
    text: str


class TextSplitter:
    """文本切分器"""

    @staticmethod
    def join_texts(first: str, second: str) -> str:
        """用双换行拼接两个文本块，避免语义粘连"""
        if not first:
            return second
        if not second:
            return first
        return f"{first}\n\n{second}"

    @staticmethod
    def split_paragraphs(text: str) -> list[str]:
        """按空行切分段落并去除空白"""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return paragraphs

    @staticmethod
    def is_list_block(paragraph: str) -> bool:
        """判断段落是否包含列表结构"""
        for line in paragraph.splitlines():
            if LIST_ITEM_PATTERN.match(line):
                return True
        return False

    @staticmethod
    def split_list_items(paragraph: str) -> list[str]:
        """按列表项切分段落，保留多行条目的完整性"""
        lines = paragraph.splitlines()
        items: list[str] = []
        current: list[str] = []
        for line in lines:
            if LIST_ITEM_PATTERN.match(line):
                if current:
                    item_text = "\n".join(current).strip()
                    if item_text:
                        items.append(item_text)
                    current = []
                current.append(line)
            else:
                if not current:
                    current = [line]
                else:
                    current.append(line)
        if current:
            item_text = "\n".join(current).strip()
            if item_text:
                items.append(item_text)
        return items

    @staticmethod
    def split_by_length(text: str, max_len: int) -> list[str]:
        """按固定长度切分文本"""
        return [text[i:i + max_len] for i in range(0, len(text), max_len) if text[i:i + max_len]]

    @staticmethod
    def split_by_sentences(text: str, max_len: int) -> list[str]:
        """按中英标点切句并尽量控制最大长度"""
        sentences = [s.strip() for s in re.split(r"(?<=[。！？；.!?;])\s+", text) if s.strip()]
        if not sentences:
            return []

        parts: list[str] = []
        buffer = ""
        for sentence in sentences:
            if not buffer:
                buffer = sentence
                if len(buffer) > max_len:
                    parts.extend(TextSplitter.split_by_length(buffer, max_len))
                    buffer = ""
                continue

            candidate = f"{buffer} {sentence}".strip()
            if len(candidate) <= max_len:
                buffer = candidate
            else:
                parts.append(buffer)
                buffer = sentence
                if len(buffer) > max_len:
                    parts.extend(TextSplitter.split_by_length(buffer, max_len))
                    buffer = ""

        if buffer:
            parts.append(buffer)

        return parts

    @staticmethod
    def apply_overlap(chunks: list[str], overlap_len: int) -> list[str]:
        """为相邻块添加重叠上下文"""
        if overlap_len <= 0 or len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]
        for idx in range(1, len(chunks)):
            prev = chunks[idx - 1]
            overlap_text = prev[-overlap_len:] if len(prev) > overlap_len else prev
            if overlap_text:
                merged = TextSplitter.join_texts(overlap_text, chunks[idx])
            else:
                merged = chunks[idx]
            overlapped.append(merged)
        return overlapped
