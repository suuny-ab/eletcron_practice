"""
API 路由集成测试
测试健康检查、配置管理、知识库等端点

注意：这些测试需要完整的环境配置（包括 chromadb 等依赖）
运行方式：pip install -r requirements.txt && pytest tests/integration/ -v
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


# 标记所有测试需要完整环境
pytestmark = pytest.mark.integration


class TestHealthRoutes:
    """测试健康检查路由"""

    def test_health_check(self):
        """测试健康检查端点"""
        # 延迟导入避免循环导入
        from app.main import app
        
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


class TestKnowledgeRoutes:
    """测试知识库路由"""

    @pytest.fixture
    def mock_knowledge_service(self):
        """Mock 知识库服务"""
        mock = Mock()
        mock.get_file_tree.return_value = [
            {"key": "test.md", "title": "test.md", "is_leaf": True, "children": None}
        ]
        mock.read_file.return_value = Mock(
            success=True,
            filename="test.md",
            file_size=100,
            file_path="test.md",
            content="# 测试内容"
        )
        mock.write_file.return_value = Mock(
            success=True,
            filename="test.md",
            file_size=50,
            file_path="test.md"
        )
        return mock

    def test_get_file_tree(self, mock_knowledge_service):
        """测试获取文件树"""
        from app.main import app
        from app.dependencies import get_knowledge_service
        
        app.dependency_overrides[get_knowledge_service] = lambda: mock_knowledge_service
        
        try:
            with TestClient(app) as client:
                response = client.get("/knowledge/tree")
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                assert data["message"] == "文件树获取成功"
        finally:
            app.dependency_overrides.clear()

    def test_get_file_content(self, mock_knowledge_service):
        """测试读取文件内容"""
        from app.main import app
        from app.dependencies import get_knowledge_service
        
        app.dependency_overrides[get_knowledge_service] = lambda: mock_knowledge_service
        
        try:
            with TestClient(app) as client:
                response = client.get("/knowledge/file/test.md")
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                assert data["message"] == "文件读取成功"
        finally:
            app.dependency_overrides.clear()

    def test_update_file_content(self, mock_knowledge_service):
        """测试更新文件内容"""
        from app.main import app
        from app.dependencies import get_knowledge_service
        
        app.dependency_overrides[get_knowledge_service] = lambda: mock_knowledge_service
        
        try:
            with TestClient(app) as client:
                response = client.put(
                    "/knowledge/file/test.md",
                    json={"content": "# 新内容"}
                )
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                assert data["message"] == "文件更新成功"
        finally:
            app.dependency_overrides.clear()


class TestConfigRoutes:
    """测试配置管理路由"""

    @pytest.fixture
    def mock_config_context(self):
        """Mock 配置上下文"""
        mock = Mock()
        mock.get.return_value = {
            "notes_root": "/test/path",
            "api_key": "test_key"
        }
        mock.update.return_value = None
        return mock

    def test_get_config(self, mock_config_context):
        """测试获取配置"""
        from app.main import app
        from app.dependencies import get_config_context
        
        app.dependency_overrides[get_config_context] = lambda: mock_config_context
        
        try:
            with TestClient(app) as client:
                response = client.get("/config")
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
        finally:
            app.dependency_overrides.clear()

    def test_update_config(self, mock_config_context):
        """测试更新配置"""
        from app.main import app
        from app.dependencies import get_config_context
        
        app.dependency_overrides[get_config_context] = lambda: mock_config_context
        
        try:
            with TestClient(app) as client:
                response = client.put(
                    "/config",
                    json={"notes_root": "/new/path"}
                )
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestAIRoutes:
    """测试 AI 路由"""

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI 服务"""
        mock = Mock()
        
        # Mock 流式方法
        async def mock_stream(*args, **kwargs):
            yield "测试"
            yield "输出"
        
        mock.optimize_markdown_layout_stream = mock_stream
        mock.chat_suggestion_stream = mock_stream
        mock.edit_document_stream = mock_stream
        mock.rag_answer_stream = mock_stream
        return mock

    @pytest.fixture
    def mock_rag_service(self):
        """Mock RAG 服务"""
        mock = Mock()
        mock.retrieve_context.return_value = ("上下文", [{"filename": "test.md", "content": "内容"}])
        return mock

    def test_optimize_endpoint_exists(self, mock_ai_service):
        """测试排版优化端点存在"""
        from app.main import app
        from app.dependencies import get_ai_service
        
        app.dependency_overrides[get_ai_service] = lambda: mock_ai_service
        
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/ai/optimize",
                    json={"filename": "test.md"}
                )
                # 流式响应应该返回 200
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_advise_endpoint_exists(self, mock_ai_service):
        """测试 AI 建议端点存在"""
        from app.main import app
        from app.dependencies import get_ai_service
        
        app.dependency_overrides[get_ai_service] = lambda: mock_ai_service
        
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/ai/advise",
                    json={"filename": "test.md", "question": "测试问题"}
                )
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_edit_endpoint_exists(self, mock_ai_service):
        """测试文档编辑端点存在"""
        from app.main import app
        from app.dependencies import get_ai_service
        
        app.dependency_overrides[get_ai_service] = lambda: mock_ai_service
        
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/ai/edit",
                    json={"filename": "test.md", "requirement": "添加标题"}
                )
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_rag_endpoint_exists(self, mock_ai_service, mock_rag_service):
        """测试 RAG 问答端点存在"""
        from app.main import app
        from app.dependencies import get_ai_service, get_rag_service
        
        app.dependency_overrides[get_ai_service] = lambda: mock_ai_service
        app.dependency_overrides[get_rag_service] = lambda: mock_rag_service
        
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/ai/rag",
                    json={"question": "测试问题"}
                )
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestRequestValidation:
    """测试请求参数验证"""

    def test_optimize_missing_filename(self):
        """测试排版优化缺少文件名"""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.post(
                "/ai/optimize",
                json={}
            )
            # 应该返回 422（验证错误）或 400（参数缺失）
            assert response.status_code in [400, 422]

    def test_advise_missing_question(self):
        """测试 AI 建议缺少问题"""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.post(
                "/ai/advise",
                json={"filename": "test.md"}
            )
            assert response.status_code in [400, 422]

    def test_edit_missing_requirement(self):
        """测试文档编辑缺少需求"""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.post(
                "/ai/edit",
                json={"filename": "test.md"}
            )
            assert response.status_code in [400, 422]

    def test_rag_missing_question(self):
        """测试 RAG 问答缺少问题"""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.post(
                "/ai/rag",
                json={}
            )
            assert response.status_code in [400, 422]


class TestErrorHandling:
    """测试错误处理"""

    def test_not_found_route(self):
        """测试不存在的路由"""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.get("/nonexistent")
            assert response.status_code == 404

    def test_method_not_allowed(self):
        """测试不允许的 HTTP 方法"""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.delete("/health")
            assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
