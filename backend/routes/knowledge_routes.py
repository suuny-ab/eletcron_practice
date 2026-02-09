"""
知识库相关路由
处理知识库文件树扫描、文件读取等操作
"""
from pathlib import Path
from fastapi import APIRouter
from ..utils.config_manager import config_manager
from ..schemas.responses import DataResponse, FileTreeData, FileTreeNode
from ..schemas.requests import FileUpdateRequest
from ..core.exceptions import NotFoundException, ValidationException

# 创建路由器
router = APIRouter(prefix="/knowledge", tags=["知识库"])


def _build_file_tree(root_path: Path, relative_path: Path = None) -> list[FileTreeNode]:
    """
    递归构建文件树

    Args:
        root_path: 根目录路径
        relative_path: 相对根目录的当前路径

    Returns:
        文件树节点列表
    """
    if relative_path is None:
        relative_path = Path("")

    current_path = root_path / relative_path
    nodes = []

    # 排除的目录和文件
    exclude_dirs = {'.obsidian', '.git', '.myapp', 'node_modules', '__pycache__', '.venv'}
    exclude_files = {'.DS_Store'}

    try:
        # 遍历当前目录
        for item in sorted(current_path.iterdir()):
            # 跳过排除的目录
            if item.is_dir() and item.name in exclude_dirs:
                continue
            # 跳过其他隐藏文件和排除的文件
            if item.name.startswith('.') and item.name not in exclude_dirs:
                continue
            if item.name in exclude_files:
                continue

            rel_item_path = relative_path / item.name

            if item.is_dir():
                # 目录：递归构建子树
                children = _build_file_tree(root_path, rel_item_path)
                if children:  # 只添加非空目录
                    nodes.append(FileTreeNode(
                        key=str(rel_item_path).replace('\\', '/'),
                        title=item.name,
                        is_leaf=False,
                        children=children
                    ))
            elif item.is_file():
                # 文件：添加叶子节点
                nodes.append(FileTreeNode(
                    key=str(rel_item_path).replace('\\', '/'),
                    title=item.name,
                    is_leaf=True,
                    children=None
                ))
    except PermissionError:
        # 跳过无权限访问的目录
        pass

    return nodes


@router.get("/tree", response_model=DataResponse[FileTreeData])
async def get_file_tree():
    """
    获取知识库文件树

    Returns:
        DataResponse[FileTreeData]: 包含文件树数据的响应
    """
    # 读取配置
    config = config_manager.read_config()
    if not config:
        raise NotFoundException("请先配置 Obsidian Vault 路径")

    vault_path = Path(config.obsidian_vault_path)
    if not vault_path.exists():
        raise NotFoundException(f"知识库路径不存在: {config.obsidian_vault_path}")

    if not vault_path.is_dir():
        raise ValidationException(f"知识库路径不是目录: {config.obsidian_vault_path}")

    # 构建文件树
    tree = _build_file_tree(vault_path)

    return DataResponse[FileTreeData](
        data=FileTreeData(tree=tree),
        message="文件树获取成功"
    )


@router.get("/file/{relative_path:path}", response_model=DataResponse[dict])
async def get_file_content(relative_path: str):
    """
    读取文件内容

    Args:
        relative_path: 相对于知识库根目录的文件路径

    Returns:
        DataResponse[dict]: 包含文件内容的响应
    """
    # 读取配置
    config = config_manager.read_config()
    if not config:
        raise NotFoundException("请先配置 Obsidian Vault 路径")

    # 构建完整文件路径
    vault_path = Path(config.obsidian_vault_path)
    file_path = vault_path / relative_path

    # 安全检查：确保文件在知识库目录内
    try:
        file_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        raise ValidationException("无效的文件路径")

    if not file_path.exists():
        raise NotFoundException(f"文件不存在: {relative_path}")

    if not file_path.is_file():
        raise ValidationException("路径不是文件")

    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            content = "[二进制文件，无法预览]"

    return DataResponse[dict](
        data={
            "relative_path": relative_path.replace('\\', '/'),
            "filename": file_path.name,
            "content": content,
            "size": file_path.stat().st_size
        },
        message="文件读取成功"
    )


@router.put("/file/{relative_path:path}", response_model=DataResponse[dict])
async def update_file_content(relative_path: str, request: FileUpdateRequest):
    """
    更新文件内容

    Args:
        relative_path: 相对于知识库根目录的文件路径
        request: 包含更新内容的请求体

    Returns:
        DataResponse[dict]: 包含更新结果的响应
    """
    # 读取配置
    config = config_manager.read_config()
    if not config:
        raise NotFoundException("请先配置 Obsidian Vault 路径")

    # 构建完整文件路径
    vault_path = Path(config.obsidian_vault_path)
    file_path = vault_path / relative_path

    # 安全检查：确保文件在知识库目录内
    try:
        file_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        raise ValidationException("无效的文件路径")

    if not file_path.exists():
        raise NotFoundException(f"文件不存在: {relative_path}")

    if not file_path.is_file():
        raise ValidationException("路径不是文件")

    # 写入文件内容
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)
    except Exception as e:
        raise ValidationException(f"写入文件失败: {str(e)}")

    return DataResponse[dict](
        data={
            "relative_path": relative_path.replace('\\', '/'),
            "filename": file_path.name,
            "size": file_path.stat().st_size
        },
        message="文件更新成功"
    )
