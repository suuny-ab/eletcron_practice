"""
保护块解析器
负责解析代码块、表格、引用等需要保护的结构
"""
import re
from typing import Literal, TypedDict

CODE_FENCE_PATTERN = re.compile(r"^(```|~~~)")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]*$")


class SplitBlock(TypedDict):
    """切分中间结构单元，用于标识保护块/普通文本"""
    type: Literal["normal", "protected"]
    kind: Literal["normal", "code", "table", "quote"]
    text: str


class ProtectedBlockParser:
    """保护块解析器"""

    @staticmethod
    def parse(text: str) -> list[SplitBlock]:
        """
        解析保护块（代码/表格/引用），保证二次切分不破坏结构

        Args:
            text: 输入文本

        Returns:
            list[SplitBlock]: 解析后的块列表
        """
        lines = text.splitlines()
        blocks: list[SplitBlock] = []
        normal_buffer: list[str] = []
        idx = 0

        def flush_normal() -> None:
            if normal_buffer:
                content = "\n".join(normal_buffer).strip()
                if content:
                    blocks.append({"type": "normal", "kind": "normal", "text": content})
                normal_buffer.clear()

        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()

            fence_match = CODE_FENCE_PATTERN.match(stripped)
            if fence_match:
                flush_normal()
                fence = fence_match.group(1)
                code_lines = [line]
                idx += 1
                while idx < len(lines):
                    code_lines.append(lines[idx])
                    if lines[idx].strip().startswith(fence):
                        idx += 1
                        break
                    idx += 1
                code_text = "\n".join(code_lines).strip()
                if code_text:
                    blocks.append({"type": "protected", "kind": "code", "text": code_text})
                continue

            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                has_pipe = "|" in line
                is_table_header = TABLE_ROW_PATTERN.match(line) or has_pipe
                if is_table_header and TABLE_SEPARATOR_PATTERN.match(next_line):
                    flush_normal()
                    table_lines = [line, next_line]
                    idx += 2
                    while idx < len(lines) and (TABLE_ROW_PATTERN.match(lines[idx]) or "|" in lines[idx]):
                        table_lines.append(lines[idx])
                        idx += 1
                    table_text = "\n".join(table_lines).strip()
                    if table_text:
                        blocks.append({"type": "protected", "kind": "table", "text": table_text})
                    continue

            if line.lstrip().startswith(">"):
                flush_normal()
                quote_lines = [line]
                idx += 1
                while idx < len(lines):
                    next_raw = lines[idx]
                    if next_raw.lstrip().startswith(">"):
                        quote_lines.append(next_raw)
                        idx += 1
                        continue
                    if next_raw.strip() == "" and idx + 1 < len(lines) and lines[idx + 1].lstrip().startswith(">"):
                        quote_lines.append(next_raw)
                        idx += 1
                        continue
                    break
                quote_text = "\n".join(quote_lines).strip()
                if quote_text:
                    blocks.append({"type": "protected", "kind": "quote", "text": quote_text})
                continue

            normal_buffer.append(line)
            idx += 1

        flush_normal()
        return blocks
