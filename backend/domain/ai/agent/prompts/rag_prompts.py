"""
RAG Agent 专用 Prompt 模板
"""

QUESTION_ANALYZE_PROMPT = """你是一个问题分析助手。请分析用户的问题，判断问题类型并提取关键信息。

用户问题：{question}

当前笔记上下文（如有）：
{note_context}

请分析这个问题并返回 JSON 格式的结果：

```json
{{
    "question_type": "knowledge_query 或 chitchat 或 clarification",
    "reasoning": "你的分析理由",
    "should_retrieve": true或false,
    "key_entities": ["关键实体1", "关键实体2"],
    "initial_query": "优化后的检索查询词"
}}
```

判断标准：
- knowledge_query: 需要检索知识库才能准确回答的问题（技术问题、概念解释、具体内容查询等）
- chitchat: 闲聊、问候、与知识库内容无关的一般性问题
- clarification: 问题过于模糊，需要用户进一步澄清才能回答

注意：
1. 如果是 chitchat，should_retrieve 应为 false
2. 如果是 knowledge_query，请提取关键实体并生成优化的检索查询词
3. initial_query 应该简洁、关键词明确，便于检索

只返回 JSON，不要有其他内容。"""


RETRIEVAL_EVALUATE_PROMPT = """你是一个检索结果评估助手。请评估当前检索结果是否足够回答用户的问题。

用户问题：{question}

当前检索轮次：{current_round} / {max_rounds}

检索到的内容：
{retrieved_content}

请评估这些检索结果并返回 JSON 格式的结果：

```json
{{
    "is_sufficient": true或false,
    "confidence": 0.0到1.0之间的置信度,
    "reasoning": "你的评估理由",
    "missing_aspects": ["缺失的方面1", "缺失的方面2"],
    "suggestion": "proceed 或 retry 或 give_up"
}}
```

评估标准：
- is_sufficient: 检索结果是否包含回答问题所需的核心信息
- confidence: 基于这些结果能给出满意答案的把握程度
- missing_aspects: 如果信息不足，列出缺少哪些方面的内容
- suggestion:
  - proceed: 信息足够，可以生成答案
  - retry: 信息不足，建议补充检索（仅当还有剩余轮次时）
  - give_up: 信息不足且已无法继续检索，基于现有内容尽力回答

只返回 JSON，不要有其他内容。"""


QUERY_REWRITE_PROMPT = """你是一个查询优化助手。请基于评估结果重新构造检索查询词。

原始问题：{question}

已检索到的内容摘要：
{retrieved_summary}

缺失的方面：{missing_aspects}

请生成新的检索查询词并返回 JSON 格式的结果：

```json
{{
    "new_query": "新的检索查询词",
    "strategy": "focus_missing 或 synonym_expand 或 broader_scope",
    "reasoning": "重构理由"
}}
```

策略说明：
- focus_missing: 聚焦于缺失的方面，针对性检索
- synonym_expand: 使用同义词或相关词扩展查询
- broader_scope: 扩大检索范围，使用更宽泛的查询词

注意：
1. 新查询应该与已检索到的内容互补，避免重复检索相同内容
2. 查询词应简洁明确，包含核心关键词

只返回 JSON，不要有其他内容。"""
