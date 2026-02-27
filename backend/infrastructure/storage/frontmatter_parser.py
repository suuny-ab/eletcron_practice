"""
Frontmatter 解析器
负责提取和解析 Obsidian/YAML frontmatter
"""
import re
from typing import Any

JsonDict = dict[str, Any]


class FrontmatterParser:
    """Frontmatter 解析器"""

    @staticmethod
    def parse(content: str) -> tuple[str, JsonDict]:
        """
        提取并剥离 Obsidian Frontmatter

        Args:
            content: 原始文档内容

        Returns:
            tuple[str, JsonDict]: (清理后的内容, 元数据字典)
        """
        if not content.startswith("---"):
            return content, {}

        lines = content.splitlines()
        if len(lines) < 3 or lines[0].strip() != "---":
            return content, {}

        end_index = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_index = idx
                break

        if end_index is None:
            return content, {}

        frontmatter_lines = lines[1:end_index]
        rest_content = "\n".join(lines[end_index + 1:]).lstrip("\n")
        metadata: JsonDict = {}

        current_key = None
        for raw_line in frontmatter_lines:
            line = raw_line.rstrip()
            if not line:
                continue

            stripped_line = line.lstrip()
            if stripped_line.startswith("-") and current_key:
                value = stripped_line.lstrip("- ").strip()
                existing = metadata.get(current_key)
                if existing is None:
                    metadata[current_key] = [value]
                elif isinstance(existing, list):
                    existing.append(value)
                else:
                    metadata[current_key] = [existing, value]
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                current_key = key

                if value.startswith("[") and value.endswith("]"):
                    items = [item.strip() for item in value[1:-1].split(",") if item.strip()]
                    if items:  # 只有非空列表才添加
                        metadata[key] = items
                elif value:
                    metadata[key] = value
                # 空值不添加到 metadata
                continue

        # 提取 tags 到顶层（如果存在）
        tags = metadata.get("tags") or metadata.get("tag")
        if isinstance(tags, list):
            metadata["tags"] = tags
        elif isinstance(tags, str):
            metadata["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

        # 过滤掉空列表和 None 值（ChromaDB 不接受）
        metadata = {k: v for k, v in metadata.items() if v is not None and v != []}

        return rest_content, metadata
