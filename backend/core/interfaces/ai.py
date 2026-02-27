"""
AI 相关接口定义
"""
from typing import Protocol, AsyncGenerator, runtime_checkable
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings


@runtime_checkable
class IModelProvider(Protocol):
    """模型提供者接口"""
    
    @property
    def chat_model(self) -> ChatTongyi:
        """获取聊天模型实例"""
        ...
    
    @property
    def embedding_model(self) -> DashScopeEmbeddings:
        """获取 Embedding 模型实例"""
        ...


@runtime_checkable  
class IChatModelService(Protocol):
    """聊天模型服务接口"""
    
    @property
    def chat_model(self):
        """获取聊天模型"""
        ...
    
    @property
    def output_parser(self):
        """获取输出解析器"""
        ...
    
    async def stream_generate(self, messages: list) -> AsyncGenerator[str, None]:
        """流式生成内容"""
        ...


@runtime_checkable
class ILLMTaskService(Protocol):
    """LLM 任务服务接口"""
    
    async def stream(
        self,
        task_type: str,
        *,
        session_id: str | None = None,
        use_history: bool = False,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式处理任务"""
        ...
    
    def invoke(self, task_type: str, **kwargs) -> list[int]:
        """同步调用任务"""
        ...
