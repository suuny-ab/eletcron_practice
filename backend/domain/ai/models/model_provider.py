"""
模型实例提供者 - 管理大模型实例
"""
from typing import Optional
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from pydantic import SecretStr


class ModelProvider:
    """模型实例提供者"""

    def __init__(self, api_key: str, model_name: str = "qwen-max"):
        """
        初始化模型提供者

        Args:
            api_key: API密钥
            model_name: 模型名称，默认为 qwen-max
        """
        self._api_key = SecretStr(api_key)
        self._model_name = model_name
        self._embedding_model_name: str = "text-embedding-v3"
        self._chat_model: Optional[ChatTongyi] = None
        self._embedding_model: Optional[DashScopeEmbeddings] = None

    @property
    def chat_model(self) -> ChatTongyi:
        """获取聊天模型实例（延迟初始化 + 缓存）"""
        if self._chat_model is None:
            self._chat_model = ChatTongyi(
                api_key=self._api_key.get_secret_value(),
                model=self._model_name
            )
        return self._chat_model

    @property
    def embedding_model(self) -> DashScopeEmbeddings:
        """获取 Embedding 模型实例（延迟初始化 + 缓存）"""
        if self._embedding_model is None:
            self._embedding_model = DashScopeEmbeddings(
                model=self._embedding_model_name,
                dashscope_api_key=self._api_key.get_secret_value()
            )
        return self._embedding_model
