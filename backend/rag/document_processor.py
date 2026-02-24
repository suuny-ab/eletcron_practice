"""
文档处理器
负责将Markdown文档切分成适合向量化的文本块
"""
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from .config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MARKDOWN_HEADERS_TO_SPLIT_ON,
)


class DocumentProcessor:
    """文档处理器，负责文档切分"""

    def __init__(self):
        """初始化文档处理器"""
        # 创建Markdown标题切分器
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=MARKDOWN_HEADERS_TO_SPLIT_ON
        )

        # 创建递归字符切分器（用于进一步切分较大的块）
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
        )

    def split_documents(self, filename: str, content: str) -> list[dict]:
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
        # 先使用Markdown标题切分器
        md_docs = self.markdown_splitter.split_text(content)

        chunks = []
        for i, doc in enumerate(md_docs):
            text = doc.page_content
            metadata = doc.metadata.copy()
            metadata["filename"] = filename
            metadata["chunk_id"] = f"{filename}_chunk_{i}"

            # 如果块仍然较大，使用递归切分器进一步切分
            if len(text) > CHUNK_SIZE * 1.5:
                sub_chunks = self.text_splitter.split_text(text)
                for j, sub_chunk in enumerate(sub_chunks):
                    sub_metadata = metadata.copy()
                    sub_metadata["chunk_id"] = f"{filename}_chunk_{i}_{j}"
                    chunks.append({
                        "content": sub_chunk,
                        "metadata": sub_metadata
                    })
            else:
                chunks.append({
                    "content": text,
                    "metadata": metadata
                })

        return chunks
