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
    merged_from: list["HeaderNode"]  # 记录合并来源的节点

    def __init__(self, level: int, title: str, parent: "HeaderNode | None" = None):
        self.level = level
        self.title = title
        self.parent = parent
        self.children = []
        self.content_lines = []
        self.merged_from = []  # 初始化为空列表

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
    def get_subtree_text(node: HeaderNode, include_title: bool = True) -> str:
        """
        获取节点子树的完整文本
        
        Args:
            node: 标题树节点
            include_title: 是否包含节点标题（默认True）
        
        Returns:
            包含标题（如有）和内容的完整文本
        """
        parts: list[str] = []
        
        # 如果节点有标题且需要包含，添加标题行
        if include_title and node.title:
            header_prefix = "#" * node.level
            parts.append(f"{header_prefix} {node.title}")
        
        # 添加节点内容
        text = "\n".join(node.content_lines).strip()
        if text:
            parts.append(text)
        
        # 递归添加子节点内容（子节点总是包含自己的标题）
        for child in node.children:
            child_text = HeaderTreeBuilder.get_subtree_text(child, include_title=True)
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
    def create_merged_leaf(parent: HeaderNode, text: str, merged_nodes: list["HeaderNode"]) -> HeaderNode:
        """
        创建合并后的虚拟叶子节点
        
        Args:
            parent: 父节点
            text: 合并后的文本内容
            merged_nodes: 被合并的源节点列表，用于保留标题元数据
        
        Returns:
            合并后的叶子节点
        """
        merged = HeaderNode(level=parent.level + 1, title="", parent=parent)
        merged.content_lines = [text]
        merged.merged_from = merged_nodes
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
        buffer_merged: list[HeaderNode] = []  # 追踪被合并的节点

        for child in node.children:
            if not child.is_leaf:
                if buffer_node:
                    new_children.append(buffer_node)
                    buffer_node = None
                    buffer_text = ""
                    buffer_merged = []
                new_children.append(child)
                continue

            child_text = HeaderTreeBuilder.get_subtree_text(child).strip()
            if not child_text:
                continue

            if buffer_node is None:
                buffer_node = child
                buffer_text = child_text
                buffer_merged = [child] if child.title or child.merged_from else []
                continue

            combined_text = _join_texts(buffer_text, child_text)
            if len(combined_text) <= max_len:
                buffer_text = combined_text
                # 追加当前节点到合并列表
                if child.title or child.merged_from:
                    buffer_merged.append(child)
                # 如果当前节点本身是合并节点，也包含其来源
                if child.merged_from:
                    buffer_merged.extend(child.merged_from)
                buffer_node = HeaderTreeBuilder.create_merged_leaf(node, buffer_text, buffer_merged)
            else:
                new_children.append(buffer_node)
                buffer_node = child
                buffer_text = child_text
                buffer_merged = [child] if child.title or child.merged_from else []

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
        """
        根据节点路径生成标题层级元数据
        
        对于合并节点，会：
        1. 使用第一个源节点的标题路径作为主分类
        2. 在 merged_headers 中记录所有合并的标题
        """
        level_to_header = {
            len(prefix): header_key for prefix, header_key in headers_to_split_on
        }
        metadata: JsonDict = {}
        
        # 收集标题路径
        path: list[HeaderNode] = []
        
        # 如果是合并节点，使用第一个源节点的标题路径
        primary_node = node.merged_from[0] if node.merged_from else node
        current = primary_node
        while current:
            if current.title:
                path.append(current)
            current = current.parent
        
        # 构建主标题层级元数据
        for item in reversed(path):
            header_key = level_to_header.get(item.level)
            if header_key:
                metadata[header_key] = item.title
        
        # 如果是合并节点，收集所有合并的标题
        if node.merged_from:
            merged_titles: list[str] = []
            for source_node in node.merged_from:
                if source_node.title:
                    merged_titles.append(source_node.title)
            if merged_titles:
                metadata["merged_headers"] = merged_titles
        
        return metadata
