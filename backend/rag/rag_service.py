"""
RAG服务核心
整合索引、检索功能
"""
from pathlib import Path
from typing import Optional
from collections.abc import AsyncGenerator
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.output_parsers import StrOutputParser
from .config import VECTOR_DB_PATH
from .document_processor import DocumentProcessor
from .file_watcher import FileWatcher


class RAGService:
    """RAG服务核心"""

    def __init__(self, notes_root: str, api_key: str, model_name: str = "text-embedding-v3", llm_model: str = "qwen-max"):
        """
        初始化RAG服务

        Args:
            notes_root: 笔记根目录路径
            api_key: API密钥（DashScope）
            model_name: Embedding模型名称
            llm_model: 大语言模型名称，默认 qwen-max
        """
        self.notes_root = Path(notes_root)
        self.api_key = api_key
        self.model_name = model_name
        self.llm_model = llm_model

        # 初始化文档处理器
        self.document_processor = DocumentProcessor()

        # 初始化向量数据库
        self.vectorstore: Optional[Chroma] = None

        # 初始化Embedding模型
        self._init_embedding_model()

        # 初始化LLM模型
        self._init_llm()

        # 初始化文件监听器
        self.file_watcher = FileWatcher(self._on_file_changed)
        self._is_watcher_started = False

        # 首次初始化时执行全量索引
        self._full_index()

    def _init_embedding_model(self):
        """初始化Embedding模型"""
        self.embeddings = DashScopeEmbeddings(
            model=self.model_name,
            dashscope_api_key=self.api_key
        )

    def _init_llm(self):
        """初始化大语言模型"""
        self.chat_model: ChatTongyi = ChatTongyi(
            api_key=self.api_key,  # pyright: ignore[reportArgumentType]
            model=self.llm_model
        )
        self.output_parser = StrOutputParser()

    def _full_index(self):
        """全量索引：索引所有Markdown文件"""
        if not self.notes_root.exists():
            return

        # 创建向量数据库
        self.vectorstore = Chroma(
            persist_directory=str(VECTOR_DB_PATH),
            embedding_function=self.embeddings,
            collection_name="knowledge_base"
        )

        # 检查是否已有数据
        try:
            existing_count = self.vectorstore._collection.count()
            if existing_count > 0:
                # 已有数据，跳过全量索引
                print(f"[RAG] 向量数据库已有 {existing_count} 个文档块，跳过全量索引")
                return
        except Exception:
            pass  # 如果查询失败，继续执行索引

        # 查找所有Markdown文件
        md_files = list(self.notes_root.rglob("*.md"))
        md_files.extend(list(self.notes_root.rglob("*.markdown")))

        if not md_files:
            print("[RAG] 未找到 Markdown 文件")
            return

        print(f"[RAG] 开始全量索引，共 {len(md_files)} 个文件...")

        # 切分并添加文档
        documents = []
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                filename = md_file.relative_to(self.notes_root).as_posix()
                chunks = self.document_processor.split_documents(filename, content)
                documents.extend(chunks)
            except Exception as e:
                print(f"[RAG] 警告: 读取文件失败 {md_file}: {e}")
                continue

        if documents:
            texts = [doc["content"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
            print(f"[RAG] 全量索引完成，共添加 {len(texts)} 个文档块")
        else:
            print("[RAG] 没有文档需要索引")

    def _on_file_changed(self, file_path: str, event_type: str):
        """
        文件变化回调

        Args:
            file_path: 文件路径
            event_type: 事件类型（created/modified/deleted）
        """
        try:
            relative_path = Path(file_path).relative_to(self.notes_root).as_posix()

            if event_type == "deleted":
                # 删除：移除该文件的所有文档块
                self._remove_file_documents(relative_path)
            else:
                # 创建或修改：重新索引该文件
                self._index_single_file(file_path, relative_path)
        except Exception as e:
            pass

    def _index_single_file(self, file_path: str, relative_path: str):
        """
        索引单个文件

        Args:
            file_path: 文件绝对路径
            relative_path: 文件相对路径
        """
        try:
            # 先删除该文件的旧文档
            self._remove_file_documents(relative_path)

            # 读取并切分文档
            content = Path(file_path).read_text(encoding="utf-8")
            chunks = self.document_processor.split_documents(relative_path, content)

            # 添加到向量数据库
            if chunks:
                texts = [doc["content"] for doc in chunks]
                metadatas = [doc["metadata"] for doc in chunks]
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
        except Exception:
            pass

    def _remove_file_documents(self, filename: str):
        """
        从向量数据库中移除指定文件的所有文档

        Args:
            filename: 文件名（相对路径）
        """
        try:
            # ChromaDB删除文档需要根据ID或条件
            # 这里通过metadata filter获取并删除
            self.vectorstore.delete(where={"filename": filename})
        except Exception:
            pass

    def start_watcher(self):
        """启动文件监听器"""
        if not self._is_watcher_started and self.notes_root.exists():
            self.file_watcher.start(str(self.notes_root))
            self._is_watcher_started = True

    def stop_watcher(self):
        """停止文件监听器"""
        if self._is_watcher_started:
            self.file_watcher.stop()
            self._is_watcher_started = False

    async def ask(self, question: str, top_k: int = 3) -> AsyncGenerator[dict, None]:
        """
        问答（流式）

        Args:
            question: 问题
            top_k: 返回的最相关文档数量

        Yields:
            dict: 包含类型和数据的字典
                - {"type": "answer", "content": "回答内容片段"}
                - {"type": "source", "data": {"filename": "...", "content": "...", "score": ...}}
                - {"type": "complete"}
                - {"type": "error", "content": "错误信息"}
        """
        try:
            if not self.vectorstore:
                yield {"type": "error", "content": "向量数据库未初始化"}
                return

            # 检索相关文档
            results = self.vectorstore.similarity_search_with_score(
                query=question,
                k=top_k
            )

            # 提取来源文档
            sources = []
            seen_files = set()
            for doc, score in results:
                filename = doc.metadata.get("filename", "")
                # 去重：同一文件只保留得分最高的一个文档块
                if filename not in seen_files:
                    seen_files.add(filename)
                    sources.append({
                        "filename": filename,
                        "content": doc.page_content,
                        "score": float(score)
                    })
                    # 如果已经收集到足够的文件，停止
                    if len(sources) >= top_k:
                        break

            # 构建上下文
            context_parts = []
            for i, source in enumerate(sources, 1):
                context_parts.append(f"\n参考资料 {i}（来自 {source['filename']}）：\n{source['content']}\n")
            context = "\n".join(context_parts)

            # 构建系统提示词
            system_prompt = """你是一个智能知识库助手。请根据提供的参考资料回答用户的问题。

回答要求：
1. 仅基于提供的参考资料回答问题，不要使用外部知识
2. 如果参考资料中没有相关信息，请明确告知
3. 回答要简洁、准确、有条理
4. 可以适当引用参考资料中的内容
5. 使用清晰的格式（如列表、分段等）组织回答

参考资料：
"""

            # 构建消息
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=system_prompt + context),
                HumanMessage(content=f"问题：{question}")
            ]

            # 流式生成回答
            stream = self.chat_model | self.output_parser
            async for chunk in stream.astream(input=messages):
                if chunk:
                    yield {"type": "answer", "content": chunk}

            # 发送来源文档
            for source in sources:
                yield {"type": "source", "data": source}

            # 发送完成信号
            yield {"type": "complete"}

        except Exception as e:
            yield {"type": "error", "content": str(e)}
