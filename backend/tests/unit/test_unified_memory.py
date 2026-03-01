"""
统一记忆模块单元测试
"""
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from domain.ai.memory.models import ConversationTurn, HistorySummary
from domain.ai.memory.unified_memory import UnifiedMemoryManager
from domain.ai.memory.unified_summarizer import UnifiedSummarizer


class TestConversationTurn:
    """ConversationTurn 数据模型测试"""
    
    def test_create_turn(self):
        """测试创建对话轮次"""
        turn = ConversationTurn(
            user_input="这份报告有什么问题？",
            assistant_output="报告存在以下问题：1. 格式不统一...",
            intent_type="doc_advise",
            permission_mode="assistant",
            document_ref="report.docx"
        )
        
        assert turn.user_input == "这份报告有什么问题？"
        assert turn.intent_type == "doc_advise"
        assert turn.permission_mode == "assistant"
        assert turn.document_ref == "report.docx"
        assert turn.turn_id is not None
        assert turn.timestamp is not None
    
    def test_turn_to_dict(self):
        """测试转换为字典"""
        turn = ConversationTurn(
            user_input="测试问题",
            assistant_output="测试回答",
            intent_type="rag_query",
            permission_mode="assistant",
            retrieval_sources=["doc1.pdf", "doc2.pdf"]
        )
        
        data = turn.to_dict()
        
        assert data["type"] == "turn"
        assert data["user_input"] == "测试问题"
        assert data["assistant_output"] == "测试回答"
        assert data["intent_type"] == "rag_query"
        assert data["retrieval_sources"] == ["doc1.pdf", "doc2.pdf"]
        assert "timestamp" in data
    
    def test_turn_from_dict(self):
        """测试从字典恢复"""
        data = {
            "turn_id": "abc123",
            "timestamp": "2024-01-01T10:00:00",
            "user_input": "用户输入",
            "assistant_output": "助手输出",
            "intent_type": "doc_edit",
            "permission_mode": "editor",
            "document_ref": "test.md",
            "tool_calls": ["edit_document"],
            "retrieval_sources": []
        }
        
        turn = ConversationTurn.from_dict(data)
        
        assert turn.turn_id == "abc123"
        assert turn.user_input == "用户输入"
        assert turn.intent_type == "doc_edit"
        assert turn.permission_mode == "editor"
        assert turn.document_ref == "test.md"
        assert turn.tool_calls == ["edit_document"]


class TestHistorySummary:
    """HistorySummary 数据模型测试"""
    
    def test_create_summary(self):
        """测试创建摘要"""
        summary = HistorySummary(
            content="用户讨论了项目进度和文档修改",
            covered_turns=6,
            topics=["report.docx", "rag_query"]
        )
        
        assert summary.content == "用户讨论了项目进度和文档修改"
        assert summary.covered_turns == 6
        assert "report.docx" in summary.topics
    
    def test_summary_to_dict(self):
        """测试转换为字典"""
        summary = HistorySummary(
            content="测试摘要",
            covered_turns=3,
            topics=["topic1"]
        )
        
        data = summary.to_dict()
        
        assert data["type"] == "summary"
        assert data["content"] == "测试摘要"
        assert data["covered_turns"] == 3


class TestUnifiedMemoryManager:
    """UnifiedMemoryManager 测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def memory_manager(self, temp_dir):
        """创建内存管理器实例"""
        return UnifiedMemoryManager(session_id="test", base_dir=temp_dir)
    
    def test_add_and_get_turn_sync(self, memory_manager):
        """测试同步添加和获取轮次"""
        turn = ConversationTurn(
            user_input="测试问题",
            assistant_output="测试回答",
            intent_type="rag_query",
            permission_mode="assistant"
        )
        
        memory_manager.add_turn_sync(turn)
        summary, turns = memory_manager.get_history_sync()
        
        assert summary is None
        assert len(turns) == 1
        assert turns[0].user_input == "测试问题"
    
    def test_multiple_turns(self, memory_manager):
        """测试多轮对话"""
        for i in range(5):
            turn = ConversationTurn(
                user_input=f"问题 {i}",
                assistant_output=f"回答 {i}",
                intent_type="rag_query",
                permission_mode="assistant"
            )
            memory_manager.add_turn_sync(turn)
        
        summary, turns = memory_manager.get_history_sync()
        
        assert len(turns) == 5
        assert turns[0].user_input == "问题 0"
        assert turns[4].user_input == "问题 4"
    
    def test_clear_history(self, memory_manager):
        """测试清空历史"""
        turn = ConversationTurn(
            user_input="测试",
            assistant_output="回答",
            intent_type="chitchat",
            permission_mode="assistant"
        )
        memory_manager.add_turn_sync(turn)
        
        memory_manager.clear()
        
        summary, turns = memory_manager.get_history_sync()
        assert summary is None
        assert len(turns) == 0
    
    def test_format_for_langchain(self, memory_manager):
        """测试格式化为 LangChain 消息"""
        turn1 = ConversationTurn(
            user_input="问题1",
            assistant_output="回答1",
            intent_type="rag_query",
            permission_mode="assistant"
        )
        turn2 = ConversationTurn(
            user_input="问题2",
            assistant_output="回答2",
            intent_type="doc_advise",
            permission_mode="assistant",
            document_ref="test.md"
        )
        
        messages = memory_manager.format_for_langchain(None, [turn1, turn2])
        
        assert len(messages) == 4  # 2 human + 2 ai
        assert messages[0].type == "human"
        assert messages[1].type == "ai"
        assert "[文档: test.md]" in messages[2].content
    
    def test_format_with_summary(self, memory_manager):
        """测试带摘要的格式化"""
        summary = HistorySummary(
            content="之前讨论了项目进度",
            covered_turns=6,
            topics=["rag_query"]
        )
        turn = ConversationTurn(
            user_input="继续",
            assistant_output="好的",
            intent_type="chitchat",
            permission_mode="assistant"
        )
        
        messages = memory_manager.format_for_langchain(summary, [turn])
        
        assert len(messages) == 3  # 1 system (summary) + 1 human + 1 ai
        assert messages[0].type == "system"
        assert "历史摘要" in messages[0].content


class TestUnifiedSummarizer:
    """UnifiedSummarizer 测试"""
    
    def test_format_turns(self):
        """测试格式化轮次"""
        summarizer = UnifiedSummarizer()
        
        turns = [
            ConversationTurn(
                user_input="什么是RAG？",
                assistant_output="RAG是检索增强生成...",
                intent_type="rag_query",
                permission_mode="assistant"
            ),
            ConversationTurn(
                user_input="帮我改一下标题",
                assistant_output="已修改标题",
                intent_type="doc_edit",
                permission_mode="editor",
                document_ref="report.md"
            )
        ]
        
        result = summarizer.format_turns(turns)
        
        assert "[RAG]" in result
        assert "[编辑]" in result
        assert "(文档: report.md)" in result
        assert "什么是RAG？" in result
    
    def test_format_messages(self):
        """测试格式化为 LangChain 消息"""
        summarizer = UnifiedSummarizer()
        
        turns = [
            ConversationTurn(
                user_input="测试",
                assistant_output="回答",
                intent_type="chitchat",
                permission_mode="assistant"
            )
        ]
        
        messages = summarizer.format_messages(None, turns)
        
        assert len(messages) == 2
        assert messages[0].type == "system"
        assert messages[1].type == "human"
        assert "（无）" in messages[1].content  # 无已有摘要
    
    def test_format_messages_with_existing_summary(self):
        """测试带已有摘要的格式化"""
        summarizer = UnifiedSummarizer()
        
        turns = [
            ConversationTurn(
                user_input="新问题",
                assistant_output="新回答",
                intent_type="rag_query",
                permission_mode="assistant"
            )
        ]
        
        messages = summarizer.format_messages("之前的摘要内容", turns)
        
        assert "之前的摘要内容" in messages[1].content
    
    def test_get_intent_label(self):
        """测试意图标签转换"""
        assert UnifiedSummarizer._get_intent_label("rag_query") == "RAG"
        assert UnifiedSummarizer._get_intent_label("doc_advise") == "建议"
        assert UnifiedSummarizer._get_intent_label("doc_edit") == "编辑"
        assert UnifiedSummarizer._get_intent_label("doc_format") == "格式化"
        assert UnifiedSummarizer._get_intent_label("chitchat") == "闲聊"
        assert UnifiedSummarizer._get_intent_label("unknown") == "unknown"


class TestAsyncOperations:
    """异步操作测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.mark.asyncio
    async def test_async_add_and_get(self, temp_dir):
        """测试异步添加和获取"""
        manager = UnifiedMemoryManager(session_id="async-test", base_dir=temp_dir)
        
        turn = ConversationTurn(
            user_input="异步测试",
            assistant_output="异步回答",
            intent_type="rag_query",
            permission_mode="assistant"
        )
        
        await manager.add_turn(turn)
        summary, turns = await manager.get_history()
        
        assert len(turns) == 1
        assert turns[0].user_input == "异步测试"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
