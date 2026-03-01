"""
统一 Agent 图定义
基于 LangGraph 构建的统一工作流
"""
import time
from collections.abc import AsyncGenerator
from typing import Literal

from langgraph.graph import StateGraph, END

from ..state import UnifiedAgentState, OutputMessage
from ..nodes import (
    # RAG 节点
    analyze_question,
    execute_retrieval,
    evaluate_results,
    rewrite_query,
    generate_answer,
    direct_answer,
    # 统一 Agent 节点
    classify_intent,
    check_document,
    prompt_document,
    check_permission,
    suggest_mode_switch,
    load_history,
    save_history,
    # 文档操作节点
    advise_document,
    edit_document,
    format_document,
)
from ...memory import UnifiedMemoryManager, UnifiedSummarizer, SessionMetadataManager
from infrastructure.logging.logger import get_logger
from infrastructure.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class UnifiedAgent:
    """
    统一 Agent

    基于 LangGraph 的统一工作流，整合：
    - 闲聊对话
    - RAG 知识检索
    - 文档建议
    - 文档编辑（Diff）
    - 文档格式化（Diff）
    """

    def __init__(
        self,
        chat_model,
        retrieval_service,
        llm_task_service,
    ):
        self._chat_model = chat_model
        self._retrieval_service = retrieval_service
        self._llm_task_service = llm_task_service
        self._graph = self._build_graph()

        logger.info("[Unified Agent] 初始化完成")

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 图"""
        graph = StateGraph(UnifiedAgentState)

        # ===== 添加节点 =====
        graph.add_node("load_history", self._run_load_history)
        graph.add_node("classify", self._run_classify)
        graph.add_node("check_doc", self._run_check_doc)
        graph.add_node("prompt_doc", self._run_prompt_doc)
        graph.add_node("analyze", self._run_analyze)
        graph.add_node("retrieve", self._run_retrieve)
        graph.add_node("evaluate", self._run_evaluate)
        graph.add_node("rewrite", self._run_rewrite)
        graph.add_node("check_permission", self._run_check_permission)
        graph.add_node("suggest_mode", self._run_suggest_mode)

        # ===== 设置入口 =====
        graph.set_entry_point("load_history")

        # ===== 边定义 =====

        # load_history → classify
        graph.add_edge("load_history", "classify")

        # classify → 条件路由
        graph.add_conditional_edges(
            "classify",
            self._route_after_classify,
            {
                "generate": END,        # chitchat/纯RAG → 图外生成
                "check_doc": "check_doc",
                "rag_analyze": "analyze",
            }
        )

        # check_doc → 条件路由
        graph.add_conditional_edges(
            "check_doc",
            self._route_after_check_doc,
            {
                "prompt_doc": "prompt_doc",
                "rag_analyze": "analyze",
                "check_permission": "check_permission",
            }
        )

        # prompt_doc → END
        graph.add_edge("prompt_doc", END)

        # analyze → retrieve（在统一 Agent 中，analyze 后直接检索）
        graph.add_edge("analyze", "retrieve")

        # retrieve → evaluate
        graph.add_edge("retrieve", "evaluate")

        # evaluate → 条件路由
        graph.add_conditional_edges(
            "evaluate",
            self._route_after_evaluate,
            {
                "done": END,                   # RAG 完成 → 图外生成
                "check_permission": "check_permission",
                "rewrite": "rewrite",
            }
        )

        # rewrite → retrieve（循环）
        graph.add_edge("rewrite", "retrieve")

        # check_permission → 条件路由
        graph.add_conditional_edges(
            "check_permission",
            self._route_after_permission,
            {
                "suggest_mode": "suggest_mode",
                "done": END,     # 权限通过 → 图外执行文档操作
            }
        )

        # suggest_mode → END
        graph.add_edge("suggest_mode", END)

        return graph.compile()

    # ===== 节点包装器 =====

    async def _run_load_history(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.load_history.duration_seconds"):
            memory = self._create_memory_manager(state.get("session_id", ""))
            return await load_history(state, memory)

    async def _run_classify(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.classify.duration_seconds"):
            return await classify_intent(state, self._chat_model)

    async def _run_check_doc(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.check_doc.duration_seconds"):
            return await check_document(state)

    async def _run_prompt_doc(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.prompt_doc.duration_seconds"):
            return await prompt_document(state)

    async def _run_analyze(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.analyze.duration_seconds"):
            return await analyze_question(state, self._chat_model)

    async def _run_retrieve(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.retrieve.duration_seconds"):
            return await execute_retrieval(state, self._retrieval_service)

    async def _run_evaluate(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.evaluate.duration_seconds"):
            return await evaluate_results(state, self._chat_model)

    async def _run_rewrite(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.rewrite.duration_seconds"):
            return await rewrite_query(state, self._chat_model)

    async def _run_check_permission(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.check_permission.duration_seconds"):
            return await check_permission(state)

    async def _run_suggest_mode(self, state: UnifiedAgentState) -> dict:
        with metrics.timer("agent.node.suggest_mode.duration_seconds"):
            return await suggest_mode_switch(state)

    # ===== 路由函数 =====

    @staticmethod
    def _route_after_classify(state: UnifiedAgentState) -> str:
        intent = state.get("intent_type", "chitchat")
        needs_doc = state.get("needs_doc", False)
        needs_rag = state.get("needs_rag", False)

        if intent == "chitchat":
            return "generate"

        if needs_doc:
            return "check_doc"

        if needs_rag:
            return "rag_analyze"

        return "generate"

    @staticmethod
    def _route_after_check_doc(state: UnifiedAgentState) -> str:
        if state.get("should_end"):
            return "prompt_doc"

        if state.get("needs_rag"):
            return "rag_analyze"

        return "check_permission"

    @staticmethod
    def _route_after_evaluate(state: UnifiedAgentState) -> str:
        evaluation = state.get("evaluation", {})
        suggestion = evaluation.get("suggestion", "proceed")
        current_round = state.get("current_round", 1)
        max_rounds = state.get("max_rounds", 3)

        if suggestion == "retry" and current_round < max_rounds:
            return "rewrite"

        # RAG 完成后判断后续
        if state.get("needs_doc"):
            return "check_permission"

        return "done"

    @staticmethod
    def _route_after_permission(state: UnifiedAgentState) -> str:
        if state.get("should_end"):
            return "suggest_mode"
        return "done"

    # ===== 辅助方法 =====

    @staticmethod
    def _create_memory_manager(session_id: str) -> UnifiedMemoryManager:
        summarizer = UnifiedSummarizer()
        # 注意：summarizer.to_callable 需要 ai_engine，这里暂不接入摘要
        # 后续可通过注入 ai_engine 启用自动摘要
        return UnifiedMemoryManager(session_id=session_id)

    # ===== 主入口 =====

    async def astream(
        self,
        user_input: str,
        session_id: str = "",
        permission_mode: str = "assistant",
        document_content: str | None = None,
        document_name: str | None = None,
        top_k: int = 3,
        max_rounds: int = 3,
    ) -> AsyncGenerator[OutputMessage, None]:
        """
        流式执行统一 Agent

        Args:
            user_input: 用户输入
            session_id: 会话 ID
            permission_mode: 权限模式 (assistant/editor)
            document_content: 文档内容 (可选)
            document_name: 文档名称 (可选)
            top_k: RAG 检索数量
            max_rounds: RAG 最大检索轮次

        Yields:
            流式输出消息
        """
        # 初始化状态
        initial_state: UnifiedAgentState = {
            "session_id": session_id,
            "user_input": user_input,
            "permission_mode": permission_mode,
            "top_k": top_k,
            "max_rounds": max_rounds,
            "current_round": 0,
            "all_sources": [],
            "output_messages": [],
            "should_end": False,
        }

        if document_content:
            initial_state["document_content"] = document_content
        if document_name:
            initial_state["document_name"] = document_name

        logger.info(
            f"[Unified Agent] 开始执行: input={user_input[:50]}..., "
            f"mode={permission_mode}, doc={document_name or '无'}"
        )

        _wf_start = time.perf_counter()

        try:
            # === 阶段 1: 执行图（状态转换）===
            final_state = initial_state.copy()
            async for state_snapshot in self._graph.astream(
                initial_state, stream_mode="values"
            ):
                # 输出新增的消息
                prev_count = len(final_state.get("output_messages", []))
                messages = state_snapshot.get("output_messages", [])[prev_count:]
                for msg in messages:
                    yield msg
                final_state = state_snapshot

            # === 阶段 2: 检查提前结束 ===
            if final_state.get("should_end"):
                end_reason = final_state.get("end_reason", "")
                logger.info(f"[Unified Agent] 提前结束: {end_reason}")
                metrics.increment("agent.workflow.count")
                metrics.observe("agent.workflow.duration_seconds", time.perf_counter() - _wf_start)
                yield {
                    "type": "complete",
                    "content": None,
                    "data": {"end_reason": end_reason}
                }
                # 提前结束也保存历史
                await self._save_history(final_state)
                return

            # === 阶段 3: 流式生成输出 ===
            intent_type = final_state.get("intent_type", "chitchat")
            metrics.increment(f"agent.intent.{intent_type}.count")
            output_chunks: list[str] = []

            if intent_type == "chitchat":
                async for msg in direct_answer(final_state, self._chat_model):
                    if msg.get("type") == "chunk":
                        output_chunks.append(msg.get("content", ""))
                    yield msg

            elif intent_type == "rag_query":
                async for msg in generate_answer(final_state, self._llm_task_service):
                    if msg.get("type") == "chunk":
                        output_chunks.append(msg.get("content", ""))
                    yield msg

            elif intent_type == "doc_advise":
                async for msg in advise_document(final_state, self._llm_task_service):
                    if msg.get("type") == "chunk":
                        output_chunks.append(msg.get("content", ""))
                    yield msg

            elif intent_type == "doc_edit":
                async for msg in edit_document(final_state, self._llm_task_service):
                    if msg.get("type") == "chunk":
                        output_chunks.append(msg.get("content", ""))
                    yield msg

            elif intent_type == "doc_format":
                async for msg in format_document(final_state, self._llm_task_service):
                    if msg.get("type") == "chunk":
                        output_chunks.append(msg.get("content", ""))
                    yield msg

            # === 阶段 4: 保存历史 ===
            final_state["final_output"] = "".join(output_chunks)
            await self._save_history(final_state)

            # === 阶段 5: 记录工作流指标并发送完成消息 ===
            metrics.increment("agent.workflow.count")
            metrics.observe("agent.workflow.duration_seconds", time.perf_counter() - _wf_start)

            yield {
                "type": "complete",
                "content": None,
                "data": {
                    "intent_type": intent_type,
                    "permission_mode": permission_mode,
                    "retrieval_rounds": final_state.get("current_round", 0),
                    "total_sources": len(final_state.get("all_sources", [])),
                }
            }

            logger.info(
                f"[Unified Agent] 执行完成: intent={intent_type}, "
                f"rounds={final_state.get('current_round', 0)}"
            )

        except Exception as e:
            metrics.increment("agent.workflow.error.count")
            metrics.observe("agent.workflow.duration_seconds", time.perf_counter() - _wf_start)
            logger.error(f"[Unified Agent] 执行失败: {e}")
            yield {
                "type": "error",
                "content": f"Agent 执行失败: {str(e)}",
                "data": None
            }

    async def _save_history(self, state: UnifiedAgentState) -> None:
        """保存对话历史并更新元数据"""
        session_id = state.get("session_id", "")
        
        try:
            memory = self._create_memory_manager(session_id)
            await save_history(state, memory)
            
            # 更新会话元数据
            await self._update_session_metadata(state)
            
        except Exception as e:
            logger.error(f"[Unified Agent] 历史保存失败: {e}")
    
    async def _update_session_metadata(self, state: UnifiedAgentState) -> None:
        """更新会话元数据"""
        session_id = state.get("session_id", "")
        if not session_id:
            return
        
        try:
            metadata_manager = SessionMetadataManager()
            
            # 检查是否是首轮对话（需要生成标题）
            is_first_turn = not metadata_manager.session_exists(session_id)
            
            if is_first_turn:
                # 创建会话并使用 LLM 生成标题
                metadata_manager.create_session(session_id)
                await self._generate_session_title(
                    metadata_manager, session_id, state.get("user_input", "")
                )
            else:
                # 更新现有会话元数据
                metadata_manager.increment_turn_count(session_id)
                metadata_manager.update_session(
                    session_id,
                    last_intent=state.get("intent_type", "chitchat"),
                    document_ref=state.get("document_name"),
                )
        except Exception as e:
            logger.warning(f"[Unified Agent] 元数据更新失败: {e}")
    
    async def _generate_session_title(
        self,
        metadata_manager: SessionMetadataManager,
        session_id: str,
        user_input: str
    ) -> None:
        """使用 LLM 生成会话标题"""
        if not user_input or not self._chat_model:
            return
        
        try:
            # 构建标题生成提示
            prompt = f"""请为以下对话生成一个简短的标题（10-20字以内），直接返回标题文字，不要加引号或其他标点：

用户消息：{user_input[:200]}

标题："""
            
            from langchain_core.messages import HumanMessage
            response = await self._chat_model.ainvoke([HumanMessage(content=prompt)])
            title = response.content.strip()[:30]
            
            if title:
                metadata_manager.update_session(session_id, title=title)
                logger.info(f"[Unified Agent] 生成会话标题: {session_id} -> {title}")
        except Exception as e:
            logger.warning(f"[Unified Agent] 标题生成失败: {e}")
