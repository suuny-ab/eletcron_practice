"""
流式响应工具函数 - 提供通用的流式响应处理
"""
from ..schemas import StreamChunk, StreamComplete, StreamError
from ..core import get_logger
from collections.abc import Callable, AsyncGenerator

logger = get_logger(__name__)



def create_json_stream(
    stream_generator: Callable[..., AsyncGenerator[str, None]],
    *args: str | None,
    **kwargs: str | None
) -> Callable[[], AsyncGenerator[str, None]]:
    """
    创建JSON格式的流式响应生成器
    
    职责：
    1. 调用服务层方法，获取纯文本流
    2. 用Pydantic模型包装数据
    3. 序列化为JSON字符串
    4. 统一错误处理
    
    Args:
        stream_generator: 服务层的流式生成器函数（返回纯文本）
        *args: 传递给生成器的位置参数
        **kwargs: 传递给生成器的关键字参数
        
    Returns:
        异步生成器函数，返回JSON字符串流

    """
    async def generate() -> AsyncGenerator[str, None]:
        """内部流式生成器"""
        try:
            # ① 遍历服务层返回的纯文本
            async for chunk in stream_generator(*args, **kwargs):
                # ② 用Pydantic模型包装内容
                chunk_model = StreamChunk(content=chunk)
                # ③ 序列化为JSON字符串并添加换行符
                yield chunk_model.model_dump_json() + "\n"

            # ④ 发送完成信号
            complete_model = StreamComplete()
            yield complete_model.model_dump_json() + "\n"

        except Exception as e:
            # ⑤ 捕获所有异常并发送错误信息
            # 流式响应不能通过全局异常处理器处理，必须在流式通道内发送错误
            import traceback

            # 获取异常类型和模块信息
            error_type = type(e).__name__
            error_module = type(e).__module__

            # 根据异常类型确定日志级别
            if error_type in ('NotFoundException', 'ValidationException'):
                logger.warning(
                    f"流式处理业务异常 [{error_type}]: {str(e)} | "
                    f"生成器: {stream_generator.__name__ if hasattr(stream_generator, '__name__') else 'unknown'}"
                )
            else:
                logger.error(
                    f"流式处理系统异常 [{error_type}]: {str(e)} | "
                    f"生成器: {stream_generator.__name__ if hasattr(stream_generator, '__name__') else 'unknown'} | "
                    f"模块: {error_module}",
                    exc_info=True  # 自动记录堆栈信息
                )

            # 发送错误信息到客户端
            # 如果是业务异常，直接显示消息；如果是系统异常，显示通用消息
            if error_type in ('NotFoundException', 'ValidationException'):
                error_message = str(e)
            else:
                error_message = f"处理失败: {str(e)}"

            error_model = StreamError(message=error_message)
            yield error_model.model_dump_json() + "\n"
    
    return generate