"""
统一 LLM 任务服务
负责根据任务类型调用模型，支持流式与同步返回
"""
from collections.abc import AsyncGenerator
import json

from langchain_core.messages import BaseMessage

from .chat_model import ChatModelService
from ..history import HistoryManager
from ..template import TemplateBuilder
from prompts.prompt_config import PromptConfigFactory



class LLMTaskService:
    """统一LLM任务服务"""

    def __init__(self, chat_model_service: ChatModelService):
        self._chat_model_service = chat_model_service
        self._template_builder = TemplateBuilder()
        self._history_manager = HistoryManager(chat_model_service)
        self._history_input_key_map = {
            "advise": "question",
            "edit": "requirement"
        }

    @staticmethod
    def _validate_params(config, params: dict) -> None:
        for param in config.params:
            if param not in params:
                raise ValueError(f"缺少必需参数: {param}")

    def _build_template(self, task_type: str, need_history: bool):
        config = PromptConfigFactory.get_config(task_type)
        return self._template_builder.build(
            system_prompt=config.system,
            human_prompt=config.human,
            need_history=need_history
        )

    async def stream(
        self,
        task_type: str,
        *,
        session_id: str | None = None,
        use_history: bool = False,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式处理任务（optimize/advise/edit/rag_qa）"""
        if task_type == "rerank":
            raise ValueError("rerank 任务不支持流式调用")

        config = PromptConfigFactory.get_config(task_type)
        self._validate_params(config, kwargs)

        if use_history:
            if not session_id:
                raise ValueError("启用历史记忆时必须提供 session_id")
            history_input_key = self._history_input_key_map.get(task_type)
            if not history_input_key:
                raise ValueError(f"任务类型 {task_type} 不支持历史记忆")

            template = self._build_template(task_type, need_history=True)
            base_chain = template | self._chat_model_service.chat_model | self._chat_model_service.output_parser
            chain_with_history = self._history_manager.create_chain_with_history(
                base_chain,
                history_input_key
            )
            config_dict = {"configurable": {"session_id": session_id}}
            async for chunk in chain_with_history.astream(kwargs, config=config_dict):
                if chunk:
                    yield chunk
            return

        template = self._build_template(task_type, need_history=False)
        messages: list[BaseMessage] = template.format_messages(**kwargs)
        async for chunk in self._chat_model_service.stream_generate(messages):
            yield chunk

    def invoke(self, task_type: str, **kwargs) -> list[int]:
        """同步调用任务（仅支持 rerank）"""
        if task_type != "rerank":
            raise ValueError(f"任务类型 {task_type} 不支持同步调用")

        config = PromptConfigFactory.get_config(task_type)
        self._validate_params(config, kwargs)
        template = self._build_template(task_type, need_history=False)
        messages = template.format_messages(**kwargs)

        response = self._chat_model_service.chat_model.invoke(messages)
        content = getattr(response, "content", str(response))

        try:
            indices = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("rerank 返回结果不是有效的JSON数组") from exc

        if not isinstance(indices, list):
            raise ValueError("rerank 返回结果不是JSON数组")

        if any(not isinstance(idx, int) for idx in indices):
            raise ValueError("rerank 返回包含非整数索引")

        return indices
