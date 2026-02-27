"""
知识库服务层 - 对外提供知识库业务能力
"""
from ..repositories.knowledge_repository import KnowledgeRepository
from schemas.responses import FileTreeData, FileReadResult, FileWriteResult





class KnowledgeService:
    """知识库服务"""

    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def get_file_tree(self) -> FileTreeData:
        """获取文件树（使用缓存）"""
        tree = self._repository.get_file_tree()
        return FileTreeData(tree=tree)

    def read_file(self, relative_path: str) -> FileReadResult:
        return self._repository.read_file(relative_path)

    def write_file(self, relative_path: str, content: str) -> FileWriteResult:
        return self._repository.write_file(relative_path, content)


