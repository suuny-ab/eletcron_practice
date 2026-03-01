"""
统一 Agent 状态定义
"""
from typing import TypedDict, Literal


# ===== 子类型定义 =====

class AnalysisResult(TypedDict, total=False):
    """问题分析结果（RAG 用）"""
    question_type: Literal["knowledge_query", "chitchat", "clarification"]
    reasoning: str
    should_retrieve: bool
    key_entities: list[str]
    initial_query: str


class EvaluationResult(TypedDict, total=False):
    """检索评估结果"""
    is_sufficient: bool
    confidence: float
    reasoning: str
    missing_aspects: list[str]
    suggestion: Literal["proceed", "retry", "give_up"]


class SourceItem(TypedDict):
    """检索来源项"""
    filename: str
    content: str
    score: float


class OutputMessage(TypedDict):
    """流式输出消息"""
    type: Literal["status", "thinking", "sources", "chunk", "diff", "prompt", "error", "complete"]
    content: str | None
    data: dict | list | None


class ConversationTurnDict(TypedDict, total=False):
    """对话轮次（字典形式，用于状态传递）"""
    turn_id: str
    timestamp: str
    user_input: str
    assistant_output: str
    intent_type: str
    permission_mode: str
    document_ref: str | None
    tool_calls: list[str]
    retrieval_sources: list[str]


# ===== 统一 Agent 状态 =====

class UnifiedAgentState(TypedDict, total=False):
    """统一 Agent 状态
    
    整合 RAG 问答、文档建议、文档编辑、文档格式化等功能
    """
    
    # ===== 输入（必需）=====
    session_id: str                      # 会话标识
    user_input: str                      # 用户输入
    permission_mode: str                 # 权限模式: assistant / editor
    
    # ===== 输入（可选）=====
    document_content: str                # 文档内容
    document_name: str                   # 文档名称
    
    # ===== 历史上下文 =====
    history_summary: str                 # 历史摘要
    recent_turns: list[ConversationTurnDict]  # 近期对话轮次
    
    # ===== 意图分类结果 =====
    intent_type: str                     # chitchat/rag_query/doc_advise/doc_edit/doc_format
    needs_rag: bool                      # 是否需要 RAG 检索
    needs_doc: bool                      # 是否需要文档上下文
    
    # ===== RAG 检索状态 =====
    analysis: AnalysisResult             # 问题分析结果
    current_round: int                   # 当前检索轮次
    max_rounds: int                      # 最大检索轮次
    current_query: str                   # 当前查询
    all_sources: list[SourceItem]        # 所有检索结果
    evaluation: EvaluationResult         # 评估结果
    top_k: int                           # 检索数量
    
    # ===== 输出 =====
    output_messages: list[OutputMessage] # 流式消息队列
    final_output: str                    # 最终输出
    
    # ===== 控制流 =====
    should_end: bool                     # 是否提前结束
    end_reason: str                      # 结束原因: prompt_doc / suggest_mode / error
    error: str                           # 错误信息

