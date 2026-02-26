"""
流式响应工具函数 - 提供通用的流式响应处理
"""
from ..core.error_handler import log_exception
from ..core.exceptions import BaseBusinessException
from collections.abc import Callable, AsyncGenerator
from typing import cast
import json


def create_json_stream(
    stream_generator: Callable[..., AsyncGenerator[object, None]],
    *args: object,
    **kwargs: object
) -> Callable[[], AsyncGenerator[str, None]]:

    """
    创建JSON格式的流式响应生成器
    
    职责：
    1. 调用服务层方法，获取纯文本流或事件流
    2. 统一序列化为NDJSON事件
    3. 统一错误处理
    
    Args:
        stream_generator: 服务层的流式生成器函数（返回纯文本或事件对象）
        *args: 传递给生成器的位置参数
        **kwargs: 传递给生成器的关键字参数

        
    Returns:
        异步生成器函数，返回JSON字符串流


    """
    async def generate() -> AsyncGenerator[str, None]:
        """内部流式生成器"""
        try:
            # ① 遍历服务层返回的流式内容
            has_complete = False
            async for chunk in stream_generator(*args, **kwargs):
                if isinstance(chunk, dict):
                    event = cast(dict[str, object], chunk)
                else:
                    event = {"type": "chunk", "content": str(chunk)}

                if event.get("type") == "complete":
                    has_complete = True

                yield json.dumps(event, ensure_ascii=False) + "\n"


            # ④ 发送完成信号（若服务层未显式输出）
            if not has_complete:
                yield json.dumps({"type": "complete", "status": "done"}, ensure_ascii=False) + "\n"

        except Exception as e:
            # ⑤ 捕获所有异常并发送错误信息
            # 流式响应不能通过全局异常处理器处理，必须在流式通道内发送错误

            # 使用统一的异常日志记录
            generator_name = stream_generator.__name__ if hasattr(stream_generator, '__name__') else 'unknown'
            log_exception(e, f"流式处理 | 生成器: {generator_name}")

            # 发送错误信息到客户端
            # 如果是业务异常，直接显示消息；如果是系统异常，显示通用消息
            if isinstance(e, BaseBusinessException):
                error_message = str(e)
            else:
                error_message = f"处理失败: {str(e)}"

            yield json.dumps({"type": "error", "content": error_message}, ensure_ascii=False) + "\n"

    return generate