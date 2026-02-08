"""
配置相关路由
处理配置的读取、更新和删除操作
"""
from fastapi import APIRouter
from ..utils.config_manager import config_manager
from ..schemas.requests import UpdateConfigRequest
from ..schemas.responses import DataResponse, BaseResponse, ConfigData

# 创建路由器
router = APIRouter(prefix="/config", tags=["配置管理"])


@router.get("", response_model=DataResponse[ConfigData])
async def get_config():
    """
    读取当前配置

    Returns:
        DataResponse[ConfigData]: 包含配置数据的响应
    """
    config = config_manager.read_config()
    if config is None:
        from ..core.exceptions import NotFoundException
        raise NotFoundException("配置文件不存在，请先创建配置")

    return DataResponse[ConfigData](
        data=ConfigData(
            obsidian_vault_path=config.obsidian_vault_path,
            api_key=config.api_key,
            model_name=config.model_name
        )
    )


@router.put("", response_model=DataResponse[ConfigData])
async def update_config(request: UpdateConfigRequest):
    """
    更新配置

    Args:
        request: 配置更新请求数据

    Returns:
        DataResponse[ConfigData]: 包含更新后配置数据的响应
    """
    config = config_manager.write_config(
        obsidian_vault_path=request.obsidian_vault_path,
        api_key=request.api_key,
        model_name=request.model_name
    )

    # 重新加载 AI 配置（由工具层负责）
    from ..services.ai_service import reload_ai_service
    reload_ai_service()

    return DataResponse[ConfigData](
        data=ConfigData(
            obsidian_vault_path=config.obsidian_vault_path,
            api_key=config.api_key,
            model_name=config.model_name
        ),
        message="配置更新成功"
    )


@router.delete("", response_model=BaseResponse)
async def delete_config():
    """
    删除配置

    Returns:
        BaseResponse: 操作结果响应
    """
    success = config_manager.delete_config()
    if not success:
        from ..core.exceptions import NotFoundException
        raise NotFoundException("配置文件不存在，无需删除")

    return BaseResponse(message="配置删除成功")
