"""
RAG Agent 图定义
基于 LangGraph 构建的智能 RAG 流程
"""
from collections.abc import AsyncGenerator
from typing import Literal

from langgraph.graph import StateGraph, END

from ..state import RAGAgentState, OutputMessage
from ..nodes import (
    analyze_question,
    execute_retrieval,
    evaluate_results,
    rewrite_query,
    generate_answer,
    direct_answer,
    ask_clarification,
)
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RAGAgent:
    """
    RAG Agent
    
    基于 LangGraph 的智能 RAG 流程，支持：
    - 问题分析与分类
    - 多轮检索
    - 结果评估与查询重构
    - 流式答案生成
    """
    
    def __init__(
        self,
        chat_model,
        retrieval_service,
        llm_task_service,
    ):
        """
        初始化 RAG Agent
        
        Args:
            chat_model: 聊天模型实例
            retrieval_service: 检索服务实例
            llm_task_service: LLM 任务服务实例
        """
        self._chat_model = chat_model
        self._retrieval_service = retrieval_service
        self._llm_task_service = llm_task_service
        self._graph = self._build_graph()
        
        logger.info("[RAG Agent] 初始化完成")
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 图"""
        graph = StateGraph(RAGAgentState)
        
        # 添加节点（直接使用异步方法）
        graph.add_node("analyze", self._run_analyze)
        graph.add_node("retrieve", self._run_retrieve)
        graph.add_node("evaluate", self._run_evaluate)
        graph.add_node("rewrite", self._run_rewrite)
        
        # 设置入口
        graph.set_entry_point("analyze")
        
        # 问题分析后的路由
        graph.add_conditional_edges(
            "analyze",
            self._route_after_analyze,
            {
                "retrieve": "retrieve",
                "direct": END,  # 直接回答在流式阶段处理
                "clarify": END,  # 追问也在流式阶段处理
            }
        )
        
        # 检索后进入评估
        graph.add_edge("retrieve", "evaluate")
        
        # 评估后的路由
        graph.add_conditional_edges(
            "evaluate",
            self._route_after_evaluate,
            {
                "generate": END,  # 生成答案在流式阶段处理
                "rewrite": "rewrite",
            }
        )
        
        # 重构后继续检索
        graph.add_edge("rewrite", "retrieve")
        
        return graph.compile()
    
    async def _run_analyze(self, state: RAGAgentState) -> dict:
        """运行问题分析节点"""
        return await analyze_question(state, self._chat_model)
    
    async def _run_retrieve(self, state: RAGAgentState) -> dict:
        """运行检索节点"""
        return await execute_retrieval(state, self._retrieval_service)
    
    async def _run_evaluate(self, state: RAGAgentState) -> dict:
        """运行评估节点"""
        return await evaluate_results(state, self._chat_model)
    
    async def _run_rewrite(self, state: RAGAgentState) -> dict:
        """运行查询重构节点"""
        return await rewrite_query(state, self._chat_model)
    
    def _route_after_analyze(
        self, state: RAGAgentState
    ) -> Literal["retrieve", "direct", "clarify"]:
        """问题分析后的路由"""
        analysis = state.get("analysis", {})
        question_type = analysis.get("question_type", "knowledge_query")
        should_retrieve = analysis.get("should_retrieve", True)
        
        if question_type == "chitchat" or not should_retrieve:
            return "direct"
        elif question_type == "clarification":
            return "clarify"
        else:
            return "retrieve"
    
    def _route_after_evaluate(
        self, state: RAGAgentState
    ) -> Literal["generate", "rewrite"]:
        """评估后的路由"""
        evaluation = state.get("evaluation", {})
        suggestion = evaluation.get("suggestion", "proceed")
        current_round = state.get("current_round", 1)
        max_rounds = state.get("max_rounds", 3)
        
        if suggestion == "retry" and current_round < max_rounds:
            return "rewrite"
        else:
            return "generate"
    
    async def astream(
        self,
        question: str,
        session_id: str = "",
        note_context: str | None = None,
        top_k: int = 3,
        max_rounds: int = 3,
    ) -> AsyncGenerator[OutputMessage, None]:
        """
        流式执行 RAG Agent
        
        Args:
            question: 用户问题
            session_id: 会话ID
            note_context: 当前笔记上下文
            top_k: 检索数量
            max_rounds: 最大检索轮次
            
        Yields:
            流式输出消息
        """
        # 初始化状态
        initial_state: RAGAgentState = {
            "user_input": question,
            "session_id": session_id,
            "document_content": note_context,
            "top_k": top_k,
            "max_rounds": max_rounds,
            "current_round": 0,
            "all_sources": [],
            "output_messages": [],
        }
        
        logger.info(f"[RAG Agent] 开始执行: question={question[:50]}...")
        
        try:
            # 执行图，使用 stream_mode="values" 获取完整状态
            final_state = initial_state.copy()
            async for state in self._graph.astream(initial_state, stream_mode="values"):
                # state 是完整的当前状态
                # 输出新增的消息
                prev_count = len(final_state.get("output_messages", []))
                messages = state.get("output_messages", [])[prev_count:]
                for msg in messages:
                    yield msg
                final_state = state
            
            # 根据最终状态决定如何生成答案
            analysis = final_state.get("analysis", {})
            question_type = analysis.get("question_type", "knowledge_query")
            
            if question_type == "chitchat":
                # 直接回答
                async for msg in direct_answer(final_state, self._chat_model):
                    yield msg
            elif question_type == "clarification":
                # 请求澄清
                result = await ask_clarification(final_state)
                for msg in result.get("output_messages", []):
                    yield msg
            else:
                # 基于检索结果生成答案
                async for msg in generate_answer(final_state, self._llm_task_service):
                    yield msg
            
            # 发送完成消息
            yield {
                "type": "complete",
                "content": None,
                "data": {
                    "retrieval_rounds": final_state.get("current_round", 0),
                    "total_sources": len(final_state.get("all_sources", []))
                }
            }
            
            logger.info(
                f"[RAG Agent] 执行完成: rounds={final_state.get('current_round', 0)}, "
                f"sources={len(final_state.get('all_sources', []))}"
            )
            
        except Exception as e:
            logger.error(f"[RAG Agent] 执行失败: {e}")
            yield {
                "type": "error",
                "content": f"RAG Agent 执行失败: {str(e)}",
                "data": None
            }
