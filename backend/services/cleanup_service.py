"""
历史记录清理服务
定期清理孤儿会话（笔记已删除但历史记录仍存在）
"""
from pathlib import Path
from typing import Optional

from ..core import get_logger


logger = get_logger(__name__)


class SessionCleanupService:
    """会话清理服务"""

    def __init__(
        self,
        notes_root: Optional[Path] = None,
        sessions_dir: Optional[Path] = None
    ):
        """
        初始化清理服务

        Args:
            notes_root: 笔记根目录，默认使用配置中的 Obsidian Vault 路径
            sessions_dir: 会话记录目录
        """
        backend_dir = Path(__file__).resolve().parents[1]
        self.sessions_dir = sessions_dir or (backend_dir / "ai_engine" / "data" / "ai_sessions")
        self.notes_root = notes_root

    async def cleanup_orphaned_sessions(self) -> int:
        """
        清理孤儿会话

        Returns:
            清理的会话数量
        """
        if not self.sessions_dir.exists():
            logger.info("会话目录不存在，无需清理")
            return 0

        if not self.notes_root:
            logger.warning("笔记根目录未配置，无法清理孤儿会话")
            return 0

        cleaned_count = 0

        for session_file in self.sessions_dir.glob("*.jsonl"):
            session_id = session_file.stem

            # 递归搜索对应的笔记文件
            # 注意：session_id 可能包含 .md 扩展名，也可能不包含
            note_files = list(self.notes_root.rglob(f"{session_id}"))
            if not note_files:
                logger.info(f"发现孤儿会话: {session_id}, 正在清理...")
                session_file.unlink()
                cleaned_count += 1

        logger.info(f"清理完成，共清理 {cleaned_count} 个孤儿会话")
        return cleaned_count


# 全局清理服务实例
_cleanup_service: Optional[SessionCleanupService] = None


def get_cleanup_service() -> SessionCleanupService:
    """获取清理服务实例"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = SessionCleanupService()
    return _cleanup_service


def set_cleanup_notes_root(notes_root: Path) -> None:
    """设置清理服务的笔记根目录"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = SessionCleanupService(notes_root=notes_root)
    else:
        _cleanup_service.notes_root = notes_root
