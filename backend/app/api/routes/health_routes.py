"""
健康检查路由
提供系统健康状态和指标查看接口
"""
import sys
import platform
from pathlib import Path
from fastapi import APIRouter, Request
from pydantic import BaseModel

from infrastructure.metrics import get_metrics
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["健康检查"])


class HealthStatus(BaseModel):
    """健康状态响应"""
    status: str
    version: str = "1.0.0"
    uptime_seconds: float


class ServiceStatus(BaseModel):
    """服务状态"""
    name: str
    status: str
    details: dict = {}


class DetailedHealthResponse(BaseModel):
    """详细健康检查响应"""
    status: str
    version: str = "1.0.0"
    uptime_seconds: float
    python_version: str
    platform: str
    services: list[ServiceStatus]
    metrics: dict


class MetricsResponse(BaseModel):
    """指标响应"""
    uptime_seconds: float
    counters: dict
    histograms: dict


@router.get("", response_model=HealthStatus)
async def health_check():
    """
    基础健康检查

    返回简单的健康状态，用于负载均衡器或监控系统
    """
    metrics = get_metrics()
    snapshot = metrics.get_snapshot()

    return HealthStatus(
        status="healthy",
        uptime_seconds=snapshot["uptime_seconds"]
    )


@router.get("/detail", response_model=DetailedHealthResponse)
async def detailed_health_check(request: Request):
    """
    详细健康检查

    返回系统详细状态，包括各服务健康情况和运行指标
    """
    metrics = get_metrics()
    snapshot = metrics.get_snapshot()

    # 检查各服务状态
    services = []

    # 1. 配置服务
    config_status = "healthy"
    config_details = {}
    if hasattr(request.app.state, "config_context"):
        config_context = request.app.state.config_context
        try:
            from infrastructure.config.config_context import ConfigModel
            config = config_context.read_config(ConfigModel)
            if config:
                config_details["vault_configured"] = bool(config.obsidian_vault_path)
                config_details["model_name"] = config.model_name
            else:
                config_status = "degraded"
                config_details["warning"] = "未配置"
        except Exception as e:
            config_status = "unhealthy"
            config_details["error"] = str(e)
    else:
        config_status = "unhealthy"
        config_details["error"] = "服务未初始化"

    services.append(ServiceStatus(
        name="config",
        status=config_status,
        details=config_details
    ))

    # 2. RAG 服务
    rag_status = "not_configured"
    rag_details = {}
    if hasattr(request.app.state, "rag_service") and request.app.state.rag_service:
        rag_service = request.app.state.rag_service
        try:
            index_status = rag_service.get_index_status()
            rag_details["is_indexing"] = index_status.get("is_indexing", False)
            rag_details["notes_root"] = index_status.get("notes_root", "")

            if index_status.get("marker"):
                rag_details["indexed_files"] = index_status["marker"].get("file_count", 0)
                rag_details["indexed_chunks"] = index_status["marker"].get("chunk_count", 0)

            rag_status = "healthy"
        except Exception as e:
            rag_status = "unhealthy"
            rag_details["error"] = str(e)

    services.append(ServiceStatus(
        name="rag",
        status=rag_status,
        details=rag_details
    ))

    # 3. AI 服务
    ai_status = "not_configured"
    ai_details = {}
    if hasattr(request.app.state, "ai_service"):
        ai_status = "healthy"
        # 可以添加更多 AI 服务状态检查
    else:
        ai_details["warning"] = "服务未初始化"
        ai_status = "degraded"

    services.append(ServiceStatus(
        name="ai",
        status=ai_status,
        details=ai_details
    ))

    # 确定总体状态
    overall_status = "healthy"
    for service in services:
        if service.status == "unhealthy":
            overall_status = "unhealthy"
            break
        elif service.status == "degraded" and overall_status == "healthy":
            overall_status = "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        uptime_seconds=snapshot["uptime_seconds"],
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        services=services,
        metrics={
            "counters": snapshot["counters"],
            "histograms": snapshot["histograms"],
        }
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics_endpoint():
    """
    获取运行指标

    返回 Prometheus 风格的指标数据
    """
    metrics = get_metrics()
    snapshot = metrics.get_snapshot()

    return MetricsResponse(
        uptime_seconds=snapshot["uptime_seconds"],
        counters=snapshot["counters"],
        histograms=snapshot["histograms"],
    )
