"""提示词配置模块"""
from typing import Optional
from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """提示词配置基类"""
    system: str = Field(..., description="系统提示词")
    human: str = Field(..., description="用户提示词")
    params: list[str] = Field(..., description="必需参数列表")


class OptimizeConfig(PromptConfig):
    """文档排版优化配置"""

    system: str = """
你是一个专业的Markdown文档排版优化专家，擅长整理和优化各类文档的结构和格式。
在保持原文的核心内容和意义不变的前提下可以对文档内容做适当修改。"""

    human: str = """
请优化以下Markdown文档的排版和结构：

文档内容：
{content}

请直接返回优化后的完整文档内容，不要添加额外的说明文字。"""

    params: list[str] = ['content']


class AdviseConfig(PromptConfig):
    """文档建议配置"""
    system: str = """
你是一个专业的文档助手，擅长分析和优化各类文档内容。
请基于用户提供的文档内容和问题，提供有价值的建议和回答。

回答要求：
1. 语言需要专业且友好
2. 建议需要实用且具体
3. 格式要清晰易读"""
    human: str = """
文件内容：
{content}

用户问题：{question}

请基于以上文件内容和用户问题，提供专业的分析和建议。"""
    params: list[str] = ['content', 'question']


class EditConfig(PromptConfig):
    """文档编辑配置"""
    system: str = """
你是一个专业的文档编辑专家，擅长根据用户的具体要求编辑和优化Markdown文档。

编辑原则：
1. 严格遵守用户的要求进行编辑
2. 保持Markdown格式的规范性
3. 确保文档的逻辑连贯性
4. 保持原文档的核心观点和意图，除非用户明确要求改变
5. 输出完整的编辑后文档，不要添加额外的说明文字"""
    human: str = """
用户编辑要求：
{requirement}

原文档内容：
{content}

请根据用户要求编辑上述文档，直接返回编辑后的完整Markdown内容。"""
    params: list[str] = ['content', 'requirement']


class SummaryConfig(PromptConfig):
    """对话摘要配置"""
    system: str = """
你是对话摘要器。请将以下对话内容压缩为一段摘要，保留关键结论、修改细则、明确的约束与约定，去除重复、闲聊与无关信息。

摘要要求：
1. 以清晰要点组织，不超过 200 字
2. 必须保留用户已确认的修改决策与约束
3. 不要引入新的内容，不做推测"""
    human: str = """
{conversation}"""
    params: list[str] = ['conversation']


class PromptConfigFactory:
    """提示词配置工厂 - 支持动态配置"""

    # 默认配置（当用户未自定义时使用）
    _default_configs: dict[str, PromptConfig] = {
        'optimize': OptimizeConfig(),
        'advise': AdviseConfig(),
        'edit': EditConfig(),
        'summary': SummaryConfig()
    }

    # 用户自定义配置（从配置文件加载）
    _custom_configs: dict[str, PromptConfig] = {}

    @classmethod
    def get_config(cls, task_type: str) -> PromptConfig:
        """根据任务类型获取配置（优先使用自定义配置）"""
        if task_type in cls._custom_configs:
            return cls._custom_configs[task_type]
        if task_type in cls._default_configs:
            return cls._default_configs[task_type]
        raise ValueError(f"不支持的任务类型: {task_type}")

    @classmethod
    def update_configs(cls, prompts: dict[str, dict[str, str]]) -> None:
        """
        更新自定义提示词配置

        Args:
            prompts: 提示词字典 {task_type: {system, human}}
        """
        cls._custom_configs.clear()
        for task_type, prompt_data in prompts.items():
            if task_type in cls._default_configs:
                # 更新现有任务的提示词
                default_config = cls._default_configs[task_type]
                cls._custom_configs[task_type] = PromptConfig(
                    system=prompt_data.get('system', default_config.system),
                    human=prompt_data.get('human', default_config.human),
                    params=default_config.params
                )

    @classmethod
    def reset_config(cls, task_type: str) -> None:
        """
        重置某个任务类型的提示词为默认值

        Args:
            task_type: 任务类型
        """
        if task_type in cls._custom_configs:
            del cls._custom_configs[task_type]

    @classmethod
    def get_all_configs(cls) -> dict[str, dict[str, str]]:
        """
        获取所有提示词配置（用于前端显示）

        Returns:
            {task_type: {system, human, is_custom}}
        """
        result = {}
        for task_type in ['optimize', 'advise', 'edit', 'summary']:
            config = cls.get_config(task_type)
            is_custom = task_type in cls._custom_configs
            result[task_type] = {
                'system': config.system,
                'human': config.human,
                'is_custom': is_custom
            }
        return result
