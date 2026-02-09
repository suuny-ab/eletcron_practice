"""
知识库文件操作工具函数
提供对Obsidian Vault知识库的文件操作
"""
from pathlib import Path
from .config_manager import config_manager
from ..core.exceptions import NotFoundException, ValidationException
from ..schemas.responses import FileReadResult, FileWriteResult



def _get_vault_path() -> Path:
    """
    获取知识库路径

    Returns:
        知识库根目录路径

    Raises:
        NotFoundException: 未配置知识库路径时
    """
    config = config_manager.read_config()
    if not config:
        raise NotFoundException("请先配置 Obsidian Vault 路径")

    vault_path = Path(config.obsidian_vault_path)
    if not vault_path.exists():
        raise NotFoundException(f"知识库路径不存在: {config.obsidian_vault_path}")

    if not vault_path.is_dir():
        raise ValidationException(f"知识库路径不是目录: {config.obsidian_vault_path}")

    return vault_path


def get_full_path(relative_path: str) -> Path:
    """
    获取文件的完整路径

    Args:
        relative_path: 相对于知识库根目录的文件路径

    Returns:
        文件的完整路径
    """
    vault_path = _get_vault_path()
    file_path = vault_path / relative_path

    # 安全检查：确保文件在知识库目录内
    try:
        file_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        raise ValidationException("无效的文件路径")

    return file_path


def read_file(relative_path: str) -> FileReadResult:
    """
    读取知识库文件内容

    Args:
        relative_path: 相对于知识库根目录的文件路径

    Returns:
        包含文件信息的字典

    Raises:
        NotFoundException: 文件不存在时
        ValidationException: 文件路径无效时
    """
    file_path = get_full_path(relative_path)

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
            content = ""

    return FileReadResult(
        success=True,
        filename=file_path.name,
        file_size=file_path.stat().st_size,
        file_path=relative_path.replace('\\', '/'),
        content=content,
    )


def write_file(relative_path: str, content: str) -> FileWriteResult:
    """
    写入知识库文件内容

    Args:
        relative_path: 相对于知识库根目录的文件路径
        content: 文件内容

    Returns:
        包含写入结果的字典
    """
    file_path = get_full_path(relative_path)

    # 父目录不存在时创建
    _ = file_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return FileWriteResult(
        success=True,
        filename=file_path.name,
        file_size=len(content),
        file_path=relative_path.replace('\\', '/'),
    )
