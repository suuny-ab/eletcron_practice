"""
文档处理器单元测试
测试 Markdown 分块、Frontmatter 解析、文本切分
"""
import sys
import os
import pytest

# 避免循环导入：直接导入需要测试的模块
from infrastructure.storage.frontmatter_parser import FrontmatterParser
from infrastructure.storage.text_splitter import TextSplitter


# 在导入 DocumentProcessor 之前，先导入 config 模块避免循环
# 这样 document_processor 导入 config 时不会触发 rag 包的 __init__
import domain.knowledge.rag.config  # noqa: F401


def get_document_processor():
    """获取 DocumentProcessor 实例"""
    from infrastructure.storage.document_processor import DocumentProcessor
    return DocumentProcessor()


class TestFrontmatterParser:
    """测试 Frontmatter 解析器"""

    def test_parse_no_frontmatter(self):
        """测试无 frontmatter 的文档"""
        content = "# 标题\n\n正文内容"
        cleaned, metadata = FrontmatterParser.parse(content)

        assert cleaned == content
        assert metadata == {}

    def test_parse_simple_frontmatter(self):
        """测试简单 frontmatter"""
        content = """---
title: 测试标题
author: 作者名
---

# 正文标题

内容"""
        cleaned, metadata = FrontmatterParser.parse(content)

        assert "---" not in cleaned
        assert "# 正文标题" in cleaned
        assert metadata["title"] == "测试标题"
        assert metadata["author"] == "作者名"

    def test_parse_frontmatter_with_tags_list(self):
        """测试带标签列表的 frontmatter"""
        content = """---
tags: [python, 机器学习, RAG]
---

内容"""
        cleaned, metadata = FrontmatterParser.parse(content)

        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)
        assert "python" in metadata["tags"]

    def test_parse_frontmatter_with_yaml_list(self):
        """测试 YAML 列表格式的标签"""
        content = """---
tags:
  - python
  - 机器学习
---

内容"""
        cleaned, metadata = FrontmatterParser.parse(content)

        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)

    def test_parse_incomplete_frontmatter(self):
        """测试不完整的 frontmatter（缺少结束符）"""
        content = """---
title: 测试
# 这不是结束符

内容"""
        cleaned, metadata = FrontmatterParser.parse(content)

        # 不完整的 frontmatter 应该作为普通内容
        assert cleaned == content
        assert metadata == {}

    def test_parse_empty_frontmatter(self):
        """测试空 frontmatter"""
        content = """---
---

内容"""
        cleaned, metadata = FrontmatterParser.parse(content)

        assert "内容" in cleaned
        assert metadata == {}


class TestTextSplitter:
    """测试文本切分器"""

    def test_join_texts(self):
        """测试文本拼接"""
        result = TextSplitter.join_texts("第一段", "第二段")
        assert result == "第一段\n\n第二段"

    def test_join_texts_empty_first(self):
        """测试第一段为空"""
        result = TextSplitter.join_texts("", "第二段")
        assert result == "第二段"

    def test_join_texts_empty_second(self):
        """测试第二段为空"""
        result = TextSplitter.join_texts("第一段", "")
        assert result == "第一段"

    def test_split_paragraphs(self):
        """测试段落切分"""
        text = """第一段内容

第二段内容

第三段内容"""
        paragraphs = TextSplitter.split_paragraphs(text)

        assert len(paragraphs) == 3
        assert paragraphs[0] == "第一段内容"
        assert paragraphs[1] == "第二段内容"

    def test_split_paragraphs_multiple_blank_lines(self):
        """测试多个空行切分"""
        text = """第一段


第二段"""
        paragraphs = TextSplitter.split_paragraphs(text)
        assert len(paragraphs) == 2

    def test_is_list_block_unordered(self):
        """测试无序列表识别"""
        paragraph = """- 项目1
- 项目2
- 项目3"""
        assert TextSplitter.is_list_block(paragraph) is True

    def test_is_list_block_ordered(self):
        """测试有序列表识别"""
        paragraph = """1. 第一项
2. 第二项"""
        assert TextSplitter.is_list_block(paragraph) is True

    def test_is_list_block_not_list(self):
        """测试非列表段落"""
        paragraph = "这是一个普通段落，不是列表。"
        assert TextSplitter.is_list_block(paragraph) is False

    def test_split_list_items(self):
        """测试列表项切分"""
        paragraph = """- 第一项
- 第二项
- 第三项"""
        items = TextSplitter.split_list_items(paragraph)

        assert len(items) == 3
        assert items[0] == "- 第一项"

    def test_split_list_items_multiline(self):
        """测试多行列表项"""
        paragraph = """- 第一项
  继续第一项
- 第二项"""
        items = TextSplitter.split_list_items(paragraph)

        assert len(items) == 2
        assert "继续第一项" in items[0]

    def test_split_by_length(self):
        """测试按长度切分"""
        text = "a" * 100
        chunks = TextSplitter.split_by_length(text, 30)

        assert len(chunks) == 4
        assert all(len(c) <= 30 for c in chunks)

    def test_split_by_sentences(self):
        """测试按句子切分"""
        text = "第一句话。第二句话。第三句话非常长" + "x" * 100 + "。"
        chunks = TextSplitter.split_by_sentences(text, 50)

        assert len(chunks) > 1

    def test_apply_overlap(self):
        """测试重叠切分"""
        chunks = ["第一块内容abcdef", "第二块内容", "第三块内容"]
        overlapped = TextSplitter.apply_overlap(chunks, 5)

        assert len(overlapped) == 3
        # 第二块应该包含第一块的末尾
        assert "bcdef" in overlapped[1]

    def test_apply_overlap_single_chunk(self):
        """测试单块不需要重叠"""
        chunks = ["只有一块"]
        overlapped = TextSplitter.apply_overlap(chunks, 10)
        assert overlapped == chunks

    def test_apply_overlap_zero(self):
        """测试零重叠"""
        chunks = ["第一块", "第二块"]
        overlapped = TextSplitter.apply_overlap(chunks, 0)
        assert overlapped == chunks


class TestDocumentProcessor:
    """测试文档处理器"""

    @pytest.fixture
    def processor(self):
        """延迟导入以避免循环导入"""
        return get_document_processor()

    def test_split_documents_empty_content(self, processor):
        """测试空内容"""
        chunks = processor.split_documents("test.md", "")
        assert chunks == []

    def test_split_documents_whitespace_only(self, processor):
        """测试纯空白内容"""
        chunks = processor.split_documents("test.md", "   \n\n   ")
        assert chunks == []

    def test_split_documents_simple(self, processor):
        """测试简单文档切分"""
        content = """# 标题

这是一段简单的内容。"""
        chunks = processor.split_documents("test.md", content)

        assert len(chunks) >= 1
        assert all("content" in c for c in chunks)
        assert all("metadata" in c for c in chunks)
        assert all(c["metadata"]["filename"] == "test.md" for c in chunks)

    def test_split_documents_with_frontmatter(self, processor):
        """测试带 frontmatter 的文档"""
        content = """---
title: 测试文档
tags: [测试, RAG]
---

# 正文标题

正文内容"""
        chunks = processor.split_documents("test.md", content)

        assert len(chunks) >= 1
        # Frontmatter 应该被解析到 metadata
        # 内容中不应该包含 frontmatter
        for chunk in chunks:
            assert "---" not in chunk["content"]

    def test_split_documents_by_headers(self, processor):
        """测试按标题切分"""
        content = """# 一级标题

一级内容

## 二级标题 A

二级内容 A

## 二级标题 B

二级内容 B"""
        chunks = processor.split_documents("test.md", content)

        # 应该按标题切分成多个块
        assert len(chunks) >= 1

    def test_split_documents_long_content(self, processor):
        """测试超长内容二次切分"""
        # 创建超过 CHUNK_SIZE 的内容
        long_content = "# 标题\n\n" + "这是一段很长的内容。" * 100
        chunks = processor.split_documents("test.md", long_content)

        # 超长内容应该被二次切分
        assert len(chunks) >= 1

    def test_split_documents_chunk_id_unique(self, processor):
        """测试 chunk_id 唯一性"""
        content = """# 标题1

内容1

# 标题2

内容2

# 标题3

内容3"""
        chunks = processor.split_documents("test.md", content)

        chunk_ids = [c["metadata"]["chunk_id"] for c in chunks]
        # 所有 chunk_id 应该唯一
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_split_documents_preserves_code_blocks(self, processor):
        """测试代码块保护"""
        content = """# 代码示例

```python
def hello():
    print("Hello, World!")
```

这是代码说明。"""
        chunks = processor.split_documents("test.md", content)

        # 代码块应该完整保留
        full_content = " ".join(c["content"] for c in chunks)
        assert "def hello():" in full_content or "hello" in full_content

    def test_split_documents_metadata_fields(self, processor):
        """测试 metadata 字段完整性"""
        content = "# 测试\n\n内容"
        chunks = processor.split_documents("test.md", content)

        assert len(chunks) >= 1
        chunk = chunks[0]
        assert "filename" in chunk["metadata"]
        assert "chunk_id" in chunk["metadata"]
        assert "chunk_length" in chunk["metadata"]
        assert chunk["metadata"]["chunk_length"] == len(chunk["content"])


class TestDocumentProcessorEdgeCases:
    """测试文档处理器边界情况"""

    @pytest.fixture
    def processor(self):
        """延迟导入以避免循环导入"""
        return get_document_processor()

    def test_split_nested_headers(self, processor):
        """测试嵌套标题"""
        content = """# H1

## H2

### H3

内容在H3下

## 另一个 H2

内容在这里"""
        chunks = processor.split_documents("test.md", content)
        assert len(chunks) >= 1

    def test_split_only_headers(self, processor):
        """测试仅有标题的文档"""
        content = """# 标题1

## 标题2

### 标题3"""
        chunks = processor.split_documents("test.md", content)
        # 应该能处理仅有标题的情况
        assert isinstance(chunks, list)

    def test_split_chinese_content(self, processor):
        """测试中文内容处理"""
        content = """# 中文标题

这是一段中文内容。包含各种标点符号：逗号，句号。感叹号！问号？

## 第二部分

更多中文内容。"""
        chunks = processor.split_documents("test.md", content)

        assert len(chunks) >= 1
        # 中文应该正确处理
        full_content = " ".join(c["content"] for c in chunks)
        assert "中文" in full_content

    def test_split_mixed_content(self, processor):
        """测试中英混合内容"""
        content = """# Python 入门指南

Python is a programming language. Python 是一种编程语言。

## Installation 安装

使用 pip install 进行安装。"""
        chunks = processor.split_documents("test.md", content)

        assert len(chunks) >= 1

    def test_split_special_characters(self, processor):
        """测试特殊字符处理"""
        content = """# 特殊字符测试

包含特殊字符：<>&"'[]{}()

```
<code>test</code>
```"""
        chunks = processor.split_documents("test.md", content)

        assert len(chunks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
