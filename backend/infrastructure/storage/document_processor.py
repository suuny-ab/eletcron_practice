"""
文档处理器
负责将 Markdown 文档切分成适合向量化的文本块
"""
from typing import Any, cast

from domain.knowledge.rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MARKDOWN_HEADERS_TO_SPLIT_ON,
)
from infrastructure.storage.frontmatter_parser import FrontmatterParser
from infrastructure.storage.header_tree import HeaderNode, HeaderTreeBuilder
from infrastructure.storage.protected_blocks import ProtectedBlockParser, SplitBlock
from infrastructure.storage.text_splitter import TextSplitter

JsonDict = dict[str, Any]


class DocumentProcessor:
    """文档处理器，负责文档切分"""

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

        cleaned_content, fm_metadata = FrontmatterParser.parse(content)
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

    def _split_by_headers(self, text: str, base_metadata: JsonDict) -> list[JsonDict]:
        """按标题层级切分 + 合并策略"""
        root = HeaderTreeBuilder.build(text)

        HeaderTreeBuilder.collapse_small_sections(root, CHUNK_SIZE)
        HeaderTreeBuilder.merge_leaf_siblings(root, CHUNK_SIZE)

        chunks: list[JsonDict] = []
        for leaf in HeaderTreeBuilder.iter_leaves_in_order(root):
            leaf_text = HeaderTreeBuilder.get_subtree_text(leaf).strip()
            if not leaf_text:
                continue
            metadata = base_metadata.copy()
            metadata.update(
                HeaderTreeBuilder.build_header_metadata(leaf, MARKDOWN_HEADERS_TO_SPLIT_ON)
            )
            chunks.append({"content": leaf_text, "metadata": metadata})

        return chunks

    def _split_overlong_text(
        self,
        text: str,
        max_len: int,
        overlap_len: int
    ) -> list[str]:
        """对超长文本进行二次切分，并按需增加重叠"""
        blocks = ProtectedBlockParser.parse(text)
        units: list[SplitBlock] = []
        for block in blocks:
            if block["type"] == "protected":
                units.append(block)
                continue

            for paragraph in TextSplitter.split_paragraphs(block["text"]):
                if TextSplitter.is_list_block(paragraph):
                    for item in TextSplitter.split_list_items(paragraph):
                        units.append({"type": "normal", "kind": "normal", "text": item})
                else:
                    units.append({"type": "normal", "kind": "normal", "text": paragraph})

        expanded: list[SplitBlock] = []
        for unit in units:
            unit_text = unit["text"]
            if unit["type"] == "normal" and len(unit_text) > max_len:
                for piece in TextSplitter.split_by_sentences(unit_text, max_len):
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

            candidate = TextSplitter.join_texts(buffer, unit_text)
            if len(candidate) <= max_len:
                buffer = candidate
            else:
                chunks.append(buffer)
                buffer = unit_text

        if buffer:
            chunks.append(buffer)

        if not chunks:
            return []

        return TextSplitter.apply_overlap(chunks, overlap_len)
