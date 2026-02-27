"""
Mock 服务实现，用于单元测试
"""
from typing import AsyncGenerator
from core.interfaces import (
    IModelProvider,
    IChatModelService,
    ILLMTaskService,
    IKnowledgeRepository,
)


class MockModelProvider(IModelProvider):
    """Mock 模型提供者"""

    def __init__(self):
        self._chat_model = None
        self._embedding_model = None

    @property
    def chat_model(self):
        return self._chat_model

    @property
    def embedding_model(self):
        return self._embedding_model


class MockLLMTaskService(ILLMTaskService):
    """Mock LLM 任务服务"""

    async def stream(
        self,
        task_type: str,
        *,
        session_id: str | None = None,
        use_history: bool = False,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        # 返回固定的测试输出
        yield "这是测试输出"

    def invoke(self, task_type: str, **kwargs) -> list[int]:
        return []


class MockKnowledgeRepository(IKnowledgeRepository):
    """Mock 知识库仓储"""

    def read_file(self, relative_path: str):
        from schemas.responses import FileReadResult
        return FileReadResult(
            success=True,
            filename="test.md",
            file_size=100,
            file_path=relative_path,
            content="# 测试内容\n\n这是测试内容。"
        )

    def write_file(self, relative_path: str, content: str):
        from schemas.responses import FileWriteResult
        return FileWriteResult(
            success=True,
            filename="test.md",
            file_size=len(content),
            file_path=relative_path
        )

    def get_vault_path(self):
        from pathlib import Path
        return Path("/mock/vault")

    def get_file_tree(self) -> list:
        from schemas.responses import FileTreeNode
        return [
            FileTreeNode(
                key="test.md",
                title="test.md",
                is_leaf=True,
                children=None
            )
        ]

    def invalidate_file_tree_cache(self) -> None:
        pass
