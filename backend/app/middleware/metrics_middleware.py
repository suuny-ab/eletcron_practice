"""
HTTP 请求指标中间件
记录每个请求的耗时、状态码和路由信息
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.metrics import get_metrics
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)
metrics = get_metrics()

# 不记录指标的路径前缀（避免监控自身产生噪声）
_SKIP_PREFIXES = ("/api/health",)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求指标中间件

    采集指标：
    - http.requests.count            — 总请求计数
    - http.requests.{method}.count   — 按方法计数
    - http.requests.duration_seconds  — 请求耗时直方图
    - http.responses.{status}.count  — 按状态码段计数 (2xx/4xx/5xx)
    - http.errors.count              — 5xx 错误计数
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 跳过健康检查等端点，避免噪声
        for prefix in _SKIP_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        method = request.method
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            metrics.increment("http.requests.count")
            metrics.increment(f"http.requests.{method}.count")
            metrics.increment("http.errors.count")
            metrics.increment("http.responses.5xx.count")
            metrics.observe("http.requests.duration_seconds", time.perf_counter() - start)
            raise

        elapsed = time.perf_counter() - start
        status_group = f"{response.status_code // 100}xx"

        metrics.increment("http.requests.count")
        metrics.increment(f"http.requests.{method}.count")
        metrics.increment(f"http.responses.{status_group}.count")
        metrics.observe("http.requests.duration_seconds", elapsed)

        if response.status_code >= 500:
            metrics.increment("http.errors.count")

        return response
