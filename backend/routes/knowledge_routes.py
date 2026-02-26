"""
知识库相关路由
处理知识库文件树扫描、文件读取等操作
"""
from fastapi import APIRouter, Depends
from ..services.dependencies import get_knowledge_service
from ..schemas.responses import DataResponse, FileTreeData, FileReadResult, FileWriteResult
from ..schemas.requests import FileUpdateRequest

# 创建路由器
router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/tree", response_model=DataResponse[FileTreeData])
async def get_file_tree(knowledge_service = Depends(get_knowledge_service)):
    """
    获取知识库文件树

    Returns:
        DataResponse[FileTreeData]: 包含文件树数据的响应
    """
    tree = knowledge_service.get_file_tree()

    return DataResponse[FileTreeData](
        data=tree,
        message="文件树获取成功"
    )


@router.get("/file/{relative_path:path}", response_model=DataResponse[FileReadResult])
async def get_file_content(relative_path: str, knowledge_service = Depends(get_knowledge_service)):
    """
    读取文件内容

    Args:
        relative_path: 相对于知识库根目录的文件路径

    Returns:
        DataResponse[FileReadResult]: 包含文件内容的响应
    """
    file_info = knowledge_service.read_file(relative_path)

    return DataResponse[FileReadResult](
        data=file_info,
        message="文件读取成功"
    )


@router.put("/file/{relative_path:path}", response_model=DataResponse[FileWriteResult])
async def update_file_content(relative_path: str, request: FileUpdateRequest, knowledge_service = Depends(get_knowledge_service)):
    """
    更新文件内容

    Args:
        relative_path: 相对于知识库根目录的文件路径
        request: 包含更新内容的请求体

    Returns:
        DataResponse[FileWriteResult]: 包含更新结果的响应
    """
    file_info = knowledge_service.write_file(relative_path, request.content)

    return DataResponse[FileWriteResult](
        data=file_info,
        message="文件更新成功"
    )
