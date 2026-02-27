"""
标题树构建器
负责构建 Markdown 标题层级结构
"""
import re
from collections.abc import Iterable
from typing import Any

JsonDict = dict[str, Any]
HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")


def _join_texts(first: str, second: str) -> str:
    """用双换行拼接两个文本块"""
    if not first:
        return second
    if not second:
        return first
    return f"{first}\n\n{second}"


class HeaderNode:
    """标题树节点，用于描述 Markdown 标题层级结构"""

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


class HeaderTreeBuilder:
    """标题树构建器"""

    @staticmethod
    def build(text: str) -> HeaderNode:
        """
        构建标题树，保留每个标题下的原始内容行

        Args:
            text: Markdown 文本

        Returns:
            HeaderNode: 根节点
        """
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

        HeaderTreeBuilder._materialize_intro_nodes(root)
        return root

    @staticmethod
    def _materialize_intro_nodes(node: HeaderNode) -> None:
        """把标题前的导语内容变为 (intro) 叶子节点"""
        if node.children and node.content_lines:
            intro_text = "\n".join(node.content_lines).strip()
            if intro_text:
                intro_node = HeaderNode(level=node.level + 1, title="", parent=node)
                intro_node.content_lines = [intro_text]
                node.children.insert(0, intro_node)
            node.content_lines = []

        for child in node.children:
            HeaderTreeBuilder._materialize_intro_nodes(child)

    @staticmethod
    def get_subtree_text(node: HeaderNode) -> str:
        """获取节点子树的完整文本"""
        parts: list[str] = []
        text = "\n".join(node.content_lines).strip()
        if text:
            parts.append(text)
        for child in node.children:
            child_text = HeaderTreeBuilder.get_subtree_text(child)
            if child_text:
                parts.append(child_text)
        return "\n\n".join(parts).strip()

    @staticmethod
    def collapse_small_sections(node: HeaderNode, max_len: int) -> None:
        """将小于阈值的子树折叠为单个叶子块"""
        if node.is_leaf:
            return

        subtree_text = HeaderTreeBuilder.get_subtree_text(node)
        if len(subtree_text) <= max_len:
            node.children = []
            node.content_lines = [subtree_text]
            return

        for child in node.children:
            HeaderTreeBuilder.collapse_small_sections(child, max_len)

    @staticmethod
    def create_merged_leaf(parent: HeaderNode, text: str) -> HeaderNode:
        """创建合并后的虚拟叶子节点"""
        merged = HeaderNode(level=parent.level + 1, title="", parent=parent)
        merged.content_lines = [text]
        return merged

    @staticmethod
    def merge_leaf_siblings(node: HeaderNode, max_len: int) -> None:
        """合并相邻小叶子，减少碎片化"""
        for child in node.children:
            if not child.is_leaf:
                HeaderTreeBuilder.merge_leaf_siblings(child, max_len)

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

            child_text = HeaderTreeBuilder.get_subtree_text(child).strip()
            if not child_text:
                continue

            if buffer_node is None:
                buffer_node = child
                buffer_text = child_text
                continue

            combined_text = _join_texts(buffer_text, child_text)
            if len(combined_text) <= max_len:
                buffer_text = combined_text
                buffer_node = HeaderTreeBuilder.create_merged_leaf(node, buffer_text)
            else:
                new_children.append(buffer_node)
                buffer_node = child
                buffer_text = child_text

        if buffer_node:
            new_children.append(buffer_node)

        node.children = new_children

    @staticmethod
    def iter_leaves_in_order(node: HeaderNode) -> Iterable[HeaderNode]:
        """按文档顺序遍历叶子节点"""
        if node.is_leaf:
            yield node
            return
        for child in node.children:
            yield from HeaderTreeBuilder.iter_leaves_in_order(child)

    @staticmethod
    def build_header_metadata(
        node: HeaderNode,
        headers_to_split_on: list[tuple[str, str]]
    ) -> JsonDict:
        """根据节点路径生成标题层级元数据"""
        level_to_header = {
            len(prefix): header_key for prefix, header_key in headers_to_split_on
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
