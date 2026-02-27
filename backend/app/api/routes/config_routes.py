"""
配置相关路由
处理配置的读取、更新和删除操作
"""
from fastapi import APIRouter, Request

from infrastructure.config.config_context import ConfigModel
from schemas.requests import UpdateConfigRequest
from schemas.responses import DataResponse, BaseResponse, ConfigData
from infrastructure.logging.logger import get_logger
from core.exceptions import NotFoundException, ConfigError


logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/config", tags=["配置管理"])


@router.get("", response_model=DataResponse[ConfigData])
async def get_config(request: Request):
    """
    读取当前配置

    Returns:
        DataResponse[ConfigData]: 包含配置数据的响应
    """
    config_context = request.app.state.config_context
    try:
        config = config_context.config
    except ConfigError:
        raise NotFoundException("配置文件不存在，请先创建配置")

    api_key_masked = f"****{config.api_key[-4:]}" if config.api_key else ""

    return DataResponse[ConfigData](
        data=ConfigData(
            obsidian_vault_path=config.obsidian_vault_path,
            api_key=api_key_masked,
            model_name=config.model_name,
            prompts=config.prompts
        )
    )


@router.put("", response_model=DataResponse[ConfigData])
async def update_config(request: UpdateConfigRequest, http_request: Request):
    """
    更新配置

    Args:
        request: 配置更新请求数据
        http_request: FastAPI 请求对象

    Returns:
        DataResponse[ConfigData]: 包含更新后配置数据的响应
    """
    config_context = http_request.app.state.config_context

    # 如果前端回传掩码或空字符串，则沿用已有 api_key
    existing_config = config_context.read_config(ConfigModel)
    api_key = request.api_key
    if existing_config and (not api_key or api_key.startswith("****")):
        api_key = existing_config.api_key

    # 构建配置对象
    config = config_context.build_config(
        config_class=ConfigModel,
        obsidian_vault_path=request.obsidian_vault_path,
        api_key=api_key,
        model_name=request.model_name,
        prompts=request.prompts
    )

    # 更新配置（自动持久化并触发监听器）
    config_context.update(config)

    api_key_masked = f"****{config.api_key[-4:]}" if config.api_key else ""

    return DataResponse[ConfigData](
        data=ConfigData(
            obsidian_vault_path=config.obsidian_vault_path,
            api_key=api_key_masked,
            model_name=config.model_name,
            prompts=config.prompts
        ),
        message="配置更新成功"
    )


@router.delete("", response_model=BaseResponse)
async def delete_config(http_request: Request):
    """
    删除配置

    Returns:
        BaseResponse: 操作结果响应
    """
    config_context = http_request.app.state.config_context
    success = config_context.delete_config()
    if not success:
        raise NotFoundException("配置文件不存在，无需删除")

    return BaseResponse(message="配置删除成功")
