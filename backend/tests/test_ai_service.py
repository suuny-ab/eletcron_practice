"""
AI 服务单元测试
"""
import pytest
from app.services import AIService
from tests.mocks.mock_services import MockLLMTaskService, MockKnowledgeRepository


def test_ai_service_with_mocks():
    """测试 AI 服务使用 Mock 依赖"""
    # 创建 mock 依赖
    mock_llm = MockLLMTaskService()
    mock_repo = MockKnowledgeRepository()

    # 注入 mock 依赖
    service = AIService(
        llm_task_service=mock_llm,
        knowledge_repository=mock_repo
    )

    # 测试读取文件
    result = service._knowledge_repository.read_file("test.md")
    assert result.content == "# 测试内容\n\n这是测试内容。"

    # 测试写入文件
    result = service._knowledge_repository.write_file("test.md", "新内容")
    assert result.success is True
    assert result.file_size == len("新内容")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
