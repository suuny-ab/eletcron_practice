"""
提示词模板构建器
负责构建LangChain的ChatPromptTemplate
"""
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)


class TemplateBuilder:
    """提示词模板构建器"""

    def build(self, system_prompt: str, human_prompt: str, need_history: bool = False):  # type: ignore[return-value]
        """构建提示词模板

        Args:
            system_prompt: 系统提示词
            human_prompt: 用户提示词
            need_history: 是否需要历史消息占位符

        Returns:
            ChatPromptTemplate实例
        """
        messages = [
            SystemMessagePromptTemplate.from_template(system_prompt)
        ]

        if need_history:
            messages.append(MessagesPlaceholder(variable_name="history"))  # type: ignore[arg-type]

        messages.append(HumanMessagePromptTemplate.from_template(human_prompt))  # type: ignore[arg-type]

        return ChatPromptTemplate.from_messages(messages)
