"""
知识库相关接口定义
"""
from typing import Protocol, runtime_checkable
from pathlib import Path


@runtime_checkable
class IKnowledgeRepository(Protocol):
    """知识库仓储接口"""
    
    def get_vault_path(self) -> Path:
        """获取知识库路径"""
        ...
    
    def get_file_tree(self) -> list:
        """获取文件树"""
        ...
    
    def read_file(self, relative_path: str):
        """读取文件内容"""
        ...
    
    def write_file(self, relative_path: str, content: str):
        """写入文件内容"""
        ...
    
    def invalidate_file_tree_cache(self) -> None:
        """清除文件树缓存"""
        ...


@runtime_checkable
class IKnowledgeService(Protocol):
    """知识库服务接口"""
    
    def get_file_tree(self):
        """获取文件树"""
        ...
    
    def read_file(self, relative_path: str):
        """读取文件"""
        ...
    
    def write_file(self, relative_path: str, content: str):
        """写入文件"""
        ...


@runtime_checkable
class IRAGService(Protocol):
    """RAG 服务接口"""
    
    def retrieve_context(
        self, 
        question: str, 
        top_k: int = 3
    ) -> tuple[str, list[dict]]:
        """检索上下文"""
        ...
    
    def retrieve_sources_debug(
        self,
        question: str,
        top_k: int = 3
    ) -> dict:
        """带调试信息的检索（用于可视化调试面板）"""
        ...
    
    def start_watcher(self) -> None:
        """启动文件监听器"""
        ...
    
    def stop_watcher(self) -> None:
        """停止文件监听器"""
        ...
    
    def start_indexing(self) -> None:
        """启动索引"""
        ...
