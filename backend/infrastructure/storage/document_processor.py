"""
文档处理器
负责将Markdown文档切分成适合向量化的文本块
"""
import re
from collections.abc import Iterable
from typing import Any, Literal, TypedDict, cast
from ...domain.knowledge.rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MARKDOWN_HEADERS_TO_SPLIT_ON,
)

HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
CODE_FENCE_PATTERN = re.compile(r"^(```|~~~)")
LIST_ITEM_PATTERN = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]*$")

JsonDict = dict[str, Any]


class SplitBlock(TypedDict):
    """切分中间结构单元，用于标识保护块/普通文本。"""

    type: Literal["normal", "protected"]
    kind: Literal["normal", "code", "table", "quote"]
    text: str


class HeaderNode:
    """标题树节点，用于描述 Markdown 标题层级结构。"""

    level: int
    title: str
    parent: "HeaderNode | None"
    children: list["HeaderNode"]
    content_lines: list[str]

    def __init__(self, level: int, title: str, parent: "HeaderNode | None" = None):
        self.level = level
        self.title = title
        self.parent = parent
        self.children = []
        self.content_lines = []

    @property
    def is_leaf(self) -> bool:
        return not self.children


class DocumentProcessor:
    """文档处理器，负责文档切分"""

    def __init__(self):
        """初始化文档处理器"""
        pass

    def _parse_frontmatter(self, content: str) -> tuple[str, JsonDict]:
        """提取并剥离 Obsidian Frontmatter"""
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
        metadata: JsonDict = {"frontmatter": {}}

        current_key = None
        for raw_line in frontmatter_lines:
            line = raw_line.rstrip()
            if not line:
                continue

            stripped_line = line.lstrip()
            if stripped_line.startswith("-") and current_key:
                value = stripped_line.lstrip("- ").strip()
                existing = metadata["frontmatter"].get(current_key)
                if existing is None:
                    metadata["frontmatter"][current_key] = [value]
                elif isinstance(existing, list):
                    existing.append(value)
                else:
                    metadata["frontmatter"][current_key] = [existing, value]
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                current_key = key

                if value.startswith("[") and value.endswith("]"):
                    items = [item.strip() for item in value[1:-1].split(",") if item.strip()]
                    metadata["frontmatter"][key] = items
                elif value:
                    metadata["frontmatter"][key] = value
                else:
                    metadata["frontmatter"].setdefault(key, [])
                continue

        tags = metadata["frontmatter"].get("tags") or metadata["frontmatter"].get("tag")
        if isinstance(tags, list):
            metadata["tags"] = tags
        elif isinstance(tags, str):
            metadata["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

        return rest_content, metadata

    def _build_header_tree(self, text: str) -> HeaderNode:
        """构建标题树，保留每个标题下的原始内容行。"""
        root = HeaderNode(level=0, title="")
        stack: list[HeaderNode] = [root]

        for line in text.splitlines():
            match = HEADER_PATTERN.match(line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                while stack and stack[-1].level >= level:
                    _ = stack.pop()
                parent = stack[-1] if stack else root
                node = HeaderNode(level=level, title=title, parent=parent)
                parent.children.append(node)
                stack.append(node)
            else:
                stack[-1].content_lines.append(line)

        self._materialize_intro_nodes(root)
        return root

    def _materialize_intro_nodes(self, node: HeaderNode) -> None:
        """把标题前的导语内容变为 (intro) 叶子节点。"""
        if node.children and node.content_lines:
            intro_text = "\n".join(node.content_lines).strip()
            if intro_text:
                intro_node = HeaderNode(level=node.level + 1, title="", parent=node)
                intro_node.content_lines = [intro_text]
                node.children.insert(0, intro_node)
            node.content_lines = []

        for child in node.children:
            self._materialize_intro_nodes(child)

    def _join_texts(self, first: str, second: str) -> str:
        """用双换行拼接两个文本块，避免语义粘连。"""
        if not first:
            return second
        if not second:
            return first
        return f"{first}\n\n{second}"

    def _parse_protected_blocks(self, text: str) -> list[SplitBlock]:
        """解析保护块（代码/表格/引用），保证二次切分不破坏结构。"""
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

    def _split_paragraphs(self, text: str) -> list[str]:
        """按空行切分段落并去除空白。"""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return paragraphs

    def _is_list_block(self, paragraph: str) -> bool:
        """判断段落是否包含列表结构。"""
        for line in paragraph.splitlines():
            if LIST_ITEM_PATTERN.match(line):
                return True
        return False

    def _split_list_items(self, paragraph: str) -> list[str]:
        """按列表项切分段落，保留多行条目的完整性。"""
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

    def _split_by_length(self, text: str, max_len: int) -> list[str]:
        """按固定长度切分文本。"""
        return [text[i:i + max_len] for i in range(0, len(text), max_len) if text[i:i + max_len]]

    def _split_by_sentences(self, text: str, max_len: int) -> list[str]:
        """按中英标点切句并尽量控制最大长度。"""
        sentences = [s.strip() for s in re.split(r"(?<=[。！？；.!?;])\s+", text) if s.strip()]
        if not sentences:
            return []

        parts: list[str] = []
        buffer = ""
        for sentence in sentences:
            if not buffer:
                buffer = sentence
                if len(buffer) > max_len:
                    parts.extend(self._split_by_length(buffer, max_len))
                    buffer = ""
                continue

            candidate = f"{buffer} {sentence}".strip()
            if len(candidate) <= max_len:
                buffer = candidate
            else:
                parts.append(buffer)
                buffer = sentence
                if len(buffer) > max_len:
                    parts.extend(self._split_by_length(buffer, max_len))
                    buffer = ""

        if buffer:
            parts.append(buffer)

        return parts

    def _apply_overlap(self, chunks: list[str], overlap_len: int) -> list[str]:
        """为相邻块添加重叠上下文。"""
        if overlap_len <= 0 or len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]
        for idx in range(1, len(chunks)):
            prev = chunks[idx - 1]
            overlap_text = prev[-overlap_len:] if len(prev) > overlap_len else prev
            if overlap_text:
                merged = self._join_texts(overlap_text, chunks[idx])
            else:
                merged = chunks[idx]
            overlapped.append(merged)
        return overlapped

    def _split_overlong_text(self, text: str, max_len: int, overlap_len: int) -> list[str]:
        """对超长文本进行二次切分，并按需增加重叠。"""
        blocks = self._parse_protected_blocks(text)
        units: list[SplitBlock] = []
        for block in blocks:
            if block["type"] == "protected":
                units.append(block)
                continue

            for paragraph in self._split_paragraphs(block["text"]):
                if self._is_list_block(paragraph):
                    for item in self._split_list_items(paragraph):
                        units.append({"type": "normal", "kind": "normal", "text": item})
                else:
                    units.append({"type": "normal", "kind": "normal", "text": paragraph})

        expanded: list[SplitBlock] = []
        for unit in units:
            unit_text = unit["text"]
            if unit["type"] == "normal" and len(unit_text) > max_len:
                for piece in self._split_by_sentences(unit_text, max_len):
                    expanded.append({"type": "normal", "kind": "normal", "text": piece})
            else:
                expanded.append(unit)

        chunks: list[str] = []
        buffer = ""
        for unit in expanded:
            unit_text = unit["text"]
            if not buffer:
                buffer = unit_text
                continue

            candidate = self._join_texts(buffer, unit_text)
            if len(candidate) <= max_len:
                buffer = candidate
            else:
                chunks.append(buffer)
                buffer = unit_text

        if buffer:
            chunks.append(buffer)

        if not chunks:
            return []

        return self._apply_overlap(chunks, overlap_len)

    def _get_subtree_text(self, node: HeaderNode) -> str:
        """获取节点子树的完整文本。"""
        parts: list[str] = []
        text = "\n".join(node.content_lines).strip()
        if text:
            parts.append(text)
        for child in node.children:
            child_text = self._get_subtree_text(child)
            if child_text:
                parts.append(child_text)
        return "\n\n".join(parts).strip()

    def _collapse_small_sections(self, node: HeaderNode, max_len: int) -> None:
        """将小于阈值的子树折叠为单个叶子块。"""
        if node.is_leaf:
            return

        subtree_text = self._get_subtree_text(node)
        if len(subtree_text) <= max_len:
            node.children = []
            node.content_lines = [subtree_text]
            return

        for child in node.children:
            self._collapse_small_sections(child, max_len)

    def _create_merged_leaf(self, parent: HeaderNode, text: str) -> HeaderNode:
        """创建合并后的虚拟叶子节点。"""
        merged = HeaderNode(level=parent.level + 1, title="", parent=parent)
        merged.content_lines = [text]
        return merged

    def _merge_leaf_siblings(self, node: HeaderNode, max_len: int) -> None:
        """合并相邻小叶子，减少碎片化。"""
        for child in node.children:
            if not child.is_leaf:
                self._merge_leaf_siblings(child, max_len)

        if not node.children:
            return

        new_children: list[HeaderNode] = []
        buffer_node: HeaderNode | None = None
        buffer_text = ""

        for child in node.children:
            if not child.is_leaf:
                if buffer_node:
                    new_children.append(buffer_node)
                    buffer_node = None
                    buffer_text = ""
                new_children.append(child)
                continue

            child_text = self._get_subtree_text(child).strip()
            if not child_text:
                continue

            if buffer_node is None:
                buffer_node = child
                buffer_text = child_text
                continue

            combined_text = self._join_texts(buffer_text, child_text)
            if len(combined_text) <= max_len:
                buffer_text = combined_text
                buffer_node = self._create_merged_leaf(node, buffer_text)
            else:
                new_children.append(buffer_node)
                buffer_node = child
                buffer_text = child_text

        if buffer_node:
            new_children.append(buffer_node)

        node.children = new_children

    def _iter_leaves_in_order(self, node: HeaderNode) -> Iterable[HeaderNode]:
        """按文档顺序遍历叶子节点。"""
        if node.is_leaf:
            yield node
            return
        for child in node.children:
            yield from self._iter_leaves_in_order(child)

    def _build_header_metadata(self, node: HeaderNode) -> JsonDict:
        """根据节点路径生成标题层级元数据。"""
        level_to_header = {
            len(prefix): header_key for prefix, header_key in MARKDOWN_HEADERS_TO_SPLIT_ON
        }
        metadata: JsonDict = {}
        path: list[HeaderNode] = []
        current = node
        while current:
            if current.title:
                path.append(current)
            current = current.parent
        for item in reversed(path):
            header_key = level_to_header.get(item.level)
            if header_key:
                metadata[header_key] = item.title
        return metadata

    def _split_by_headers(self, text: str, base_metadata: JsonDict) -> list[JsonDict]:
        """按标题层级切分 + 合并策略"""
        root = self._build_header_tree(text)

        self._collapse_small_sections(root, CHUNK_SIZE)
        self._merge_leaf_siblings(root, CHUNK_SIZE)

        chunks: list[JsonDict] = []
        for leaf in self._iter_leaves_in_order(root):
            leaf_text = self._get_subtree_text(leaf).strip()
            if not leaf_text:
                continue
            metadata = base_metadata.copy()
            metadata.update(self._build_header_metadata(leaf))
            chunks.append({"content": leaf_text, "metadata": metadata})

        return chunks

    def split_documents(self, filename: str, content: str) -> list[JsonDict]:
        """
        切分文档

        Args:
            filename: 文件名
            content: 文档内容

        Returns:
            切分后的文档块列表，每个块包含：
            - content: 文本内容
            - metadata: 元数据（包含文件名）
        """
        if not content or not content.strip():
            return []

        cleaned_content, fm_metadata = self._parse_frontmatter(content)
        base_metadata = {"filename": filename, **fm_metadata}
        raw_chunks = self._split_by_headers(cleaned_content, base_metadata)

        chunks = []
        for i, raw in enumerate(raw_chunks):
            raw_content = cast(str, raw["content"])
            text = raw_content.strip()
            if not text:
                continue

            sub_texts = [text]
            if len(text) > CHUNK_SIZE:
                sub_texts = self._split_overlong_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
                if not sub_texts:
                    sub_texts = [text]

            for sub_index, sub_text in enumerate(sub_texts):
                raw_metadata = cast(JsonDict, raw["metadata"])
                metadata = raw_metadata.copy()

                if len(sub_texts) > 1:
                    metadata["sub_chunk_index"] = sub_index
                    metadata["sub_chunk_total"] = len(sub_texts)
                    metadata["chunk_id"] = f"{filename}_chunk_{i}_{sub_index}"
                else:
                    metadata["chunk_id"] = f"{filename}_chunk_{i}"

                metadata["chunk_length"] = len(sub_text)

                chunks.append({
                    "content": sub_text,
                    "metadata": metadata
                })

        return chunks
