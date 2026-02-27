"""
简单测试脚本：验证磁盘配置中的 API Key 是否可用
- 读取 ~/.myapp/config.json
- 测试 ChatTongyi 调用
- 测试 DashScope Embeddings 调用
"""
from __future__ import annotations

import json
from pathlib import Path

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings


def load_config() -> dict:
    config_path = Path.home() / ".myapp" / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def test_chat(api_key: str, model_name: str) -> None:
    print(f"[Chat] model={model_name}")
    chat = ChatTongyi(api_key=api_key, model=model_name)
    resp = chat.invoke("ping")
    content = getattr(resp, "content", str(resp))
    print("[Chat] OK, response:", content[:200])


def test_embedding(api_key: str) -> None:
    print("[Embedding] model=text-embedding-v3")
    embed = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=api_key)
    vec = embed.embed_query("ping")
    print("[Embedding] OK, vector_dim:", len(vec))


if __name__ == "__main__":
    cfg = load_config()
    api_key = cfg.get("api_key", "")
    model_name = cfg.get("model_name", "qwen-max")

    if not api_key:
        raise ValueError("配置中的 api_key 为空")

    print("使用配置文件中的 api_key 后 4 位:", f"****{api_key[-4:]}")

    try:
        test_chat(api_key, model_name)
    except Exception as exc:
        print("[Chat] FAILED:", exc)

    try:
        test_embedding(api_key)
    except Exception as exc:
        print("[Embedding] FAILED:", exc)
