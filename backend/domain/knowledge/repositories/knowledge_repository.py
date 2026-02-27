"""
知识库仓储层
负责对 Obsidian Vault 的文件系统访问
"""
import time
from pathlib import Path

from infrastructure.config.config_context import ConfigContext
from core.exceptions import NotFoundException, ValidationException, ConfigError
from core.interfaces import IKnowledgeRepository, IConfigContext
from schemas.responses import FileReadResult, FileWriteResult, FileTreeNode




class KnowledgeRepository(IKnowledgeRepository):
    """知识库仓储层"""
    
    # 文件树缓存
    _file_tree_cache: list[FileTreeNode] | None = None
    _cache_timestamp: float = 0
    _cache_ttl: int = 60  # 缓存有效期60秒

    def __init__(self, config_context: IConfigContext):
        self._config_context = config_context

    def get_vault_path(self) -> Path:
        """获取知识库路径"""
        try:
            config = self._config_context.config
        except ConfigError:
            raise NotFoundException("请先配置 Obsidian Vault 路径")


        vault_path = Path(config.obsidian_vault_path)
        if not vault_path.exists():
            raise NotFoundException(f"知识库路径不存在: {config.obsidian_vault_path}")

        if not vault_path.is_dir():
            raise ValidationException(f"知识库路径不是目录: {config.obsidian_vault_path}")

        return vault_path

    def build_file_tree(self, root_path: Path, relative_path: Path | None = None) -> list[FileTreeNode]:
        """递归构建文件树"""
        if relative_path is None:
            relative_path = Path("")

        current_path = root_path / relative_path
        nodes = []

        exclude_dirs = {".obsidian", ".git", ".myapp", "node_modules", "__pycache__", ".venv"}
        exclude_files = {".DS_Store"}

        try:
            for item in sorted(current_path.iterdir()):
                if item.is_dir() and item.name in exclude_dirs:
                    continue
                if item.name.startswith(".") and item.name not in exclude_dirs:
                    continue
                if item.name in exclude_files:
                    continue

                rel_item_path = relative_path / item.name

                if item.is_dir():
                    children = self.build_file_tree(root_path, rel_item_path)
                    if children:
                        nodes.append(FileTreeNode(
                            key=str(rel_item_path).replace("\\", "/"),
                            title=item.name,
                            is_leaf=False,
                            children=children
                        ))
                elif item.is_file():
                    nodes.append(FileTreeNode(
                        key=str(rel_item_path).replace("\\", "/"),
                        title=item.name,
                        is_leaf=True,
                        children=None
                    ))
        except PermissionError:
            pass

        return nodes

    def get_file_tree(self) -> list[FileTreeNode]:
        """
        获取文件树（带缓存）
        
        Returns:
            list[FileTreeNode]: 文件树节点列表
        """
        # 检查缓存是否有效
        if (self._file_tree_cache is not None and 
            time.time() - self._cache_timestamp < self._cache_ttl):
            return self._file_tree_cache
        
        # 缓存失效，重新构建
        vault_path = self.get_vault_path()
        tree = self.build_file_tree(vault_path)
        
        # 更新缓存
        self._file_tree_cache = tree
        self._cache_timestamp = time.time()
        
        return tree
    
    def invalidate_file_tree_cache(self) -> None:
        """清除文件树缓存"""
        self._file_tree_cache = None
        self._cache_timestamp = 0

    def get_full_path(self, relative_path: str) -> Path:
        """获取文件的完整路径"""
        vault_path = self.get_vault_path()
        file_path = vault_path / relative_path

        try:
            file_path.resolve().relative_to(vault_path.resolve())
        except ValueError:
            raise ValidationException("无效的文件路径")

        return file_path

    def read_file(self, relative_path: str) -> FileReadResult:
        """读取知识库文件内容"""
        file_path = self.get_full_path(relative_path)

        if not file_path.exists():
            raise NotFoundException(f"文件不存在: {relative_path}")

        if not file_path.is_file():
            raise ValidationException("路径不是文件")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except Exception:
                content = ""

        return FileReadResult(
            success=True,
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            file_path=relative_path.replace("\\", "/"),
            content=content,
        )

    def write_file(self, relative_path: str, content: str) -> FileWriteResult:
        """写入知识库文件内容"""
        file_path = self.get_full_path(relative_path)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 文件变更，清除缓存
        self.invalidate_file_tree_cache()

        return FileWriteResult(
            success=True,
            filename=file_path.name,
            file_size=len(content),
            file_path=relative_path.replace("\\", "/"),
        )
