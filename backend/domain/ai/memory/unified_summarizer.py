"""
统一摘要生成器
负责细粒度的对话历史摘要生成
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .models import ConversationTurn

if TYPE_CHECKING:
    pass


UNIFIED_SUMMARY_SYSTEM = """你是对话摘要生成器。请将以下对话内容压缩为结构化摘要。

摘要要求：
1. 采用细粒度方式，逐轮次提取关键要点
2. 保留每轮对话的：
   - 用户意图（问了什么/要做什么）
   - AI 执行结果（做了什么/回答了什么）
   - 涉及的文档（如有）
3. 使用清晰的格式组织，每轮用一行概括
4. 总字数控制在 300 字以内
5. 不要引入新内容，不做推测

输出格式示例：
- [RAG] 用户询问项目进度，AI 从知识库检索并回答了 Q3 目标完成情况
- [编辑] 用户要求修改 report.docx 的标题，AI 完成修改
- [建议] 用户询问文档改进建议，AI 提供了 3 点结构优化建议"""

UNIFIED_SUMMARY_HUMAN = """已有摘要：
{existing_summary}

新增对话（需要合并到摘要中）：
{new_conversations}

请生成合并后的新摘要："""


class UnifiedSummarizer:
    """统一摘要生成器
    
    特性：
    - 细粒度摘要：逐轮次提取要点
    - 支持增量合并：将新对话合并到已有摘要
    - 保留操作类型和文档引用信息
    """
    
    def __init__(self):
        """初始化摘要生成器"""
        self.system_prompt = UNIFIED_SUMMARY_SYSTEM
        self.human_template = UNIFIED_SUMMARY_HUMAN
    
    def format_turns(self, turns: list[ConversationTurn]) -> str:
        """将轮次列表格式化为文本
        
        Args:
            turns: 对话轮次列表
            
        Returns:
            格式化的对话文本
        """
        lines: list[str] = []
        for i, turn in enumerate(turns, 1):
            # 构建元信息标签
            intent_label = self._get_intent_label(turn.intent_type)
            doc_info = f" (文档: {turn.document_ref})" if turn.document_ref else ""
            
            lines.append(f"--- 第 {i} 轮 [{intent_label}]{doc_info} ---")
            lines.append(f"用户: {turn.user_input}")
            lines.append(f"助手: {turn.assistant_output[:200]}..." if len(turn.assistant_output) > 200 else f"助手: {turn.assistant_output}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_messages(
        self,
        existing_summary: str | None,
        turns: list[ConversationTurn]
    ) -> list[BaseMessage]:
        """格式化为 LangChain 消息列表
        
        Args:
            existing_summary: 已有摘要（可选）
            turns: 需要摘要的新轮次
            
        Returns:
            LangChain 消息列表
        """
        conversations_text = self.format_turns(turns)
        summary_text = existing_summary if existing_summary else "（无）"
        
        human_content = self.human_template.format(
            existing_summary=summary_text,
            new_conversations=conversations_text
        )
        
        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=human_content)
        ]
    
    def to_callable(self, ai_engine) -> Callable[[str | None, list[ConversationTurn]], Awaitable[str]]:
        """转换为可调用函数
        
        Args:
            ai_engine: AI 引擎实例
            
        Returns:
            异步摘要生成函数，签名: (existing_summary, turns) -> new_summary
        """
        async def summarize(
            existing_summary: str | None,
            turns: list[ConversationTurn]
        ) -> str:
            """执行摘要生成"""
            messages = self.format_messages(existing_summary, turns)
            chunks: list[str] = []
            async for chunk in ai_engine.stream_generate(messages):
                chunks.append(chunk)
            return "".join(chunks).strip()
        
        return summarize
    
    @staticmethod
    def _get_intent_label(intent_type: str) -> str:
        """获取意图类型的中文标签"""
        labels = {
            "rag_query": "RAG",
            "doc_advise": "建议",
            "doc_edit": "编辑",
            "doc_format": "格式化",
            "chitchat": "闲聊",
        }
        return labels.get(intent_type, intent_type)
