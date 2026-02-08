"""
文件相关路由
处理文件上传、保存、删除等操作
"""
from pathlib import Path
from fastapi import APIRouter, UploadFile
from ..utils import (
    save_uploaded_file, delete_file, save_file
)
from ..schemas import SaveRequest, FileUploadData, FileSaveData, FileDeleteData
from ..schemas.responses import DataResponse

# 创建路由器
router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile):
    """
    上传文件并保存到服务器临时目录

    响应格式：统一成功/失败响应
    """
    # 读取文件内容
    contents = await file.read()

    # 验证文件名
    if not file.filename:
        from ..core.exceptions import ValidationException
        raise ValidationException("文件名不能为空")

    # 调用文件工具函数保存文件
    result = await save_uploaded_file(file.filename, contents)

    # ✅ 使用统一响应格式
    return DataResponse[FileUploadData](
        data=FileUploadData(
            filename=result["filename"],
            file_size=result["file_size"],
            file_path=result["file_path"]
        ),
        message="文件上传成功"
    )


@router.delete("/file/{filename}")
async def delete_uploaded_file(filename: str):
    """
    删除服务器上的临时文件

    响应格式：统一成功/失败响应
    """
    result = delete_file(filename)

    # ✅ 使用统一响应格式
    return DataResponse[FileDeleteData](
        data=FileDeleteData(
            filename=result["filename"],
            file_path=result["file_path"]
        ),
        message="文件删除成功"
    )


@router.post("/save")
async def save_to_server(request: SaveRequest):
    """
    保存编辑器内容到服务器文件系统

    响应格式：统一成功/失败响应
    """
    result = save_file(request.filename, request.content)

    # ✅ 使用统一响应格式
    return DataResponse[FileSaveData](
        data=FileSaveData(
            filename=result["filename"],
            file_size=result["file_size"],
            file_path=result["file_path"]
        ),
        message="文件保存成功"
    )
