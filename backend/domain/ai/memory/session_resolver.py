"""会话标识解析器（业务层不可见）"""
from pathlib import Path


class SessionResolver:
    """会话标识解析器

    根据业务参数解析 session_id，对业务层透明
    """

    def resolve(self, task_type: str, **kwargs) -> str:
        """根据业务参数解析 session_id

        Args:
            task_type: 任务类型 ('advise', 'edit')
            **kwargs: 业务参数

        Returns:
            session_id: 会话标识符

        Raises:
            ValueError: 无法确定会话标识
        """
        # advise 和 edit 任务使用 filename 作为会话标识
        if task_type in {"advise", "edit"}:
            filename = kwargs.get("filename")
            if filename:
                return Path(filename).name

        raise ValueError(f"无法为任务类型 {task_type} 确定会话标识")
