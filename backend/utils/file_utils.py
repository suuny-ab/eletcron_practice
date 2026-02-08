"""
文件操作工具函数 - 提供文件操作的基础功能
"""
from pathlib import Path
from typing import TypedDict

from ..core.exceptions import NotFoundException, ValidationException

# 默认上传目录
DEFAULT_UPLOAD_DIR = Path("temp_uploads")


# 定义返回值类型
class FileInfo(TypedDict):
    """文件信息返回值类型"""
    success: bool
    filename: str
    file_size: int
    file_path: str


class FileContentInfo(FileInfo):
    """包含文件内容的返回值类型"""
    content: str


class FileDeleteResult(TypedDict):
    """文件删除结果类型"""
    message: str
    filename: str
    file_path: str


class FileSaveResult(TypedDict):
    """文件保存结果类型"""
    success: bool
    message: str
    filename: str
    file_size: int
    file_path: str


class FileListItem(TypedDict):
    """文件列表项类型"""
    filename: str
    file_size: int
    file_path: str
    modified_time: float


def ensure_upload_dir(upload_dir: Path = DEFAULT_UPLOAD_DIR) -> Path:
    """
    确保上传目录存在
    
    Args:
        upload_dir: 上传目录路径
    
    Returns:
        确保存在的目录路径
    """
    _ = upload_dir.mkdir(exist_ok=True)
    return upload_dir


def validate_filename(filename: str) -> None:
    """
    验证文件名安全性

    Args:
        filename: 文件名

    Raises:
        ValidationException: 文件名不安全时
    """
    # 安全检查：防止目录遍历攻击
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationException("非法的文件名")

    # 检查文件扩展名
    if not filename.lower().endswith('.md'):
        raise ValidationException("只支持 .md 文件")


def get_file_path(filename: str, upload_dir: Path = DEFAULT_UPLOAD_DIR) -> Path:
    """
    获取文件的完整路径
    
    Args:
        filename: 文件名
        upload_dir: 上传目录
    
    Returns:
        文件的完整路径
    """
    validate_filename(filename)
    return upload_dir / filename


async def save_uploaded_file(filename: str, content: bytes, upload_dir: Path = DEFAULT_UPLOAD_DIR) -> FileInfo:
    """
    保存上传的文件
    
    Args:
        filename: 文件名
        content: 文件内容（字节）
        upload_dir: 上传目录
    
    Returns:
        包含文件信息的字典
    """
    validate_filename(filename)
    ensured_upload_dir = ensure_upload_dir(upload_dir)
    
    file_path = get_file_path(filename, upload_dir=ensured_upload_dir)
    
    # 保存文件
    with open(file_path, 'wb') as f:
        _ = f.write(content)
    
    return {
        "success": True,
        "filename": filename,
        "file_size": len(content),
        "file_path": str(file_path)
    }


def read_file(filename: str, upload_dir: Path = DEFAULT_UPLOAD_DIR) -> FileContentInfo:
    """
    读取文件内容

    Args:
        filename: 文件名
        upload_dir: 上传目录

    Returns:
        包含文件信息的字典

    Raises:
        NotFoundException: 文件不存在时
    """
    file_path = get_file_path(filename, upload_dir)

    if not file_path.exists():
        raise NotFoundException(f"文件不存在: {filename}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "success": True,
        "filename": filename,
        "file_size": file_path.stat().st_size,
        "content": content,
        "file_path": str(file_path)
    }


def save_file(filename: str, content: str, upload_dir: Path = DEFAULT_UPLOAD_DIR) -> FileSaveResult:
    """
    保存文件内容
    
    Args:
        filename: 文件名
        content: 文件内容
        upload_dir: 上传目录
    
    Returns:
        包含保存结果的字典
    """
    file_path = get_file_path(filename, upload_dir)
    
    # 如果文件不存在，允许创建
    _ = ensure_upload_dir(upload_dir)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        _ = f.write(content)
    
    return {
        "success": True,
        "message": "文件保存成功",
        "filename": filename,
        "file_size": len(content),
        "file_path": str(file_path)
    }


def delete_file(filename: str, upload_dir: Path = DEFAULT_UPLOAD_DIR) -> FileDeleteResult:
    """
    删除文件

    Args:
        filename: 文件名
        upload_dir: 上传目录

    Returns:
        包含删除结果的字典

    Raises:
        NotFoundException: 文件不存在时
    """
    file_path = get_file_path(filename, upload_dir)

    if not file_path.exists():
        raise NotFoundException(f"文件不存在: {filename}")

    file_path.unlink()

    return {
        "message": "文件删除成功",
        "filename": filename,
        "file_path": str(file_path)
    }


def file_exists(filename: str, upload_dir: Path = DEFAULT_UPLOAD_DIR) -> bool:
    """
    检查文件是否存在
    
    Args:
        filename: 文件名
        upload_dir: 上传目录
    
    Returns:
        文件是否存在
    """
    file_path = get_file_path(filename, upload_dir)
    return file_path.exists()


def list_files(upload_dir: Path = DEFAULT_UPLOAD_DIR) -> list[FileListItem]:
    """
    列出目录中的所有文件
    
    Args:
        upload_dir: 上传目录
    
    Returns:
        文件信息列表
    """
    _ = ensure_upload_dir(upload_dir)
    
    files: list[FileListItem] = []
    for file_path in upload_dir.glob("*.md"):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "file_size": stat.st_size,
                "file_path": str(file_path),
                "modified_time": stat.st_mtime
            })
    
    return files