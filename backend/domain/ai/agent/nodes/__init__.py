"""
统一 Agent 节点模块
"""
# RAG 相关节点（复用）
from .analyze import analyze_question
from .retrieve import execute_retrieval
from .evaluate import evaluate_results
from .rewrite import rewrite_query
from .generate import generate_answer
from .direct import direct_answer, ask_clarification

# 统一 Agent 新节点
from .classify import classify_intent
from .check_doc import check_document, prompt_document
from .check_permission import check_permission, suggest_mode_switch
from .history import load_history, save_history
from .doc_advise import advise_document
from .doc_edit import edit_document
from .doc_format import format_document

__all__ = [
    # RAG 节点
    "analyze_question",
    "execute_retrieval",
    "evaluate_results",
    "rewrite_query",
    "generate_answer",
    "direct_answer",
    "ask_clarification",
    # 统一 Agent 节点
    "classify_intent",
    "check_document",
    "prompt_document",
    "check_permission",
    "suggest_mode_switch",
    "load_history",
    "save_history",
    "advise_document",
    "edit_document",
    "format_document",
]
