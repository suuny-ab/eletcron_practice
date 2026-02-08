"""提示词配置模块"""
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


class PromptConfigFactory:
    """提示词配置工厂"""

    _configs: dict[str, PromptConfig] = {
        'optimize': OptimizeConfig(),
        'advise': AdviseConfig(),
        'edit': EditConfig()
    }

    @classmethod
    def get_config(cls, task_type: str) -> PromptConfig:
        """根据任务类型获取配置"""
        if task_type not in cls._configs:
            raise ValueError(f"不支持的任务类型: {task_type}")
        return cls._configs[task_type]
