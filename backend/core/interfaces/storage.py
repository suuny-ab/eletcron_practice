"""
存储相关接口定义
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class IDocumentProcessor(Protocol):
    """文档处理器接口"""
    
    def split_documents(
        self, 
        filename: str, 
        content: str
    ) -> list[dict]:
        """
        切分文档
        
        Args:
            filename: 文件名
            content: 文档内容
            
        Returns:
            切分后的文档块列表
        """
        ...
