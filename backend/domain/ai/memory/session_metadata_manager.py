"""
会话元数据管理器
负责会话列表的 CRUD 操作和元数据自动同步
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    turn_count: int = 0
    last_intent: str = "chitchat"
    referenced_documents: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionMetadata:
        return cls(
            session_id=data.get("session_id", ""),
            title=data.get("title", "新会话"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            turn_count=data.get("turn_count", 0),
            last_intent=data.get("last_intent", "chitchat"),
            referenced_documents=data.get("referenced_documents", []),
        )


class SessionMetadataManager:
    """会话元数据管理器
    
    使用集中存储方案：所有会话元数据存储在 sessions_metadata.json 文件中
    """
    
    METADATA_FILENAME = "sessions_metadata.json"
    
    def __init__(
        self,
        base_dir: Path | None = None,
        title_generator: Callable[[str], Awaitable[str]] | None = None
    ):
        """初始化元数据管理器
        
        Args:
            base_dir: 会话存储目录，默认为 .data/ai_sessions/
            title_generator: 标题生成函数（LLM 调用），接收用户输入返回标题
        """
        backend_dir = Path(__file__).resolve().parents[3]
        self.base_dir = base_dir or (backend_dir / ".data" / "ai_sessions")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.base_dir / self.METADATA_FILENAME
        self.title_generator = title_generator
        
        # 内存缓存
        self._cache: dict[str, SessionMetadata] | None = None
    
    def _load_metadata(self) -> dict[str, SessionMetadata]:
        """加载元数据文件"""
        if self._cache is not None:
            return self._cache
        
        if not self.metadata_file.exists():
            self._cache = {}
            return self._cache
        
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            sessions = data.get("sessions", {})
            self._cache = {
                sid: SessionMetadata.from_dict(meta)
                for sid, meta in sessions.items()
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"元数据文件损坏，重新初始化: {e}")
            self._cache = {}
        
        return self._cache
    
    def _save_metadata(self) -> None:
        """保存元数据文件（原子写入）"""
        if self._cache is None:
            return
        
        data = {
            "sessions": {
                sid: meta.to_dict()
                for sid, meta in self._cache.items()
            }
        }
        
        # 原子写入：先写临时文件，再重命名
        temp_file = self.metadata_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(self.metadata_file)
    
    def _invalidate_cache(self) -> None:
        """使缓存失效"""
        self._cache = None
    
    def get_all_sessions(self, sort_by: str = "updated_at") -> list[SessionMetadata]:
        """获取所有会话列表
        
        Args:
            sort_by: 排序字段，支持 "created_at" 或 "updated_at"
            
        Returns:
            按时间倒序排列的会话列表
        """
        # 先同步所有 .jsonl 文件的元数据
        self._sync_all_sessions()
        
        metadata = self._load_metadata()
        sessions = list(metadata.values())
        
        # 按时间倒序排列
        sessions.sort(
            key=lambda s: getattr(s, sort_by, s.updated_at),
            reverse=True
        )
        
        return sessions
    
    def get_session(self, session_id: str) -> SessionMetadata | None:
        """获取单个会话元数据"""
        metadata = self._load_metadata()
        
        if session_id not in metadata:
            # 尝试从 .jsonl 文件同步
            synced = self._sync_session_from_jsonl(session_id)
            if synced:
                return synced
            return None
        
        return metadata.get(session_id)
    
    def create_session(self, session_id: str, title: str | None = None) -> SessionMetadata:
        """创建新会话元数据
        
        Args:
            session_id: 会话 ID
            title: 会话标题，为 None 时使用默认标题
            
        Returns:
            创建的会话元数据
        """
        metadata = self._load_metadata()
        
        now = datetime.now().isoformat()
        default_title = f"新会话 - {datetime.now().strftime('%m/%d %H:%M')}"
        
        session = SessionMetadata(
            session_id=session_id,
            title=title or default_title,
            created_at=now,
            updated_at=now,
            turn_count=0,
            last_intent="chitchat",
            referenced_documents=[],
        )
        
        metadata[session_id] = session
        self._save_metadata()
        
        logger.info(f"创建会话元数据: {session_id}")
        return session
    
    def update_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        turn_count: int | None = None,
        last_intent: str | None = None,
        document_ref: str | None = None,
    ) -> SessionMetadata | None:
        """更新会话元数据
        
        Args:
            session_id: 会话 ID
            title: 新标题
            turn_count: 新轮次数
            last_intent: 最后意图类型
            document_ref: 引用的文档名
            
        Returns:
            更新后的元数据，会话不存在时返回 None
        """
        metadata = self._load_metadata()
        
        if session_id not in metadata:
            # 会话不存在，尝试同步或创建
            synced = self._sync_session_from_jsonl(session_id)
            if not synced:
                return None
        
        session = metadata[session_id]
        
        if title is not None:
            session.title = title
        if turn_count is not None:
            session.turn_count = turn_count
        if last_intent is not None:
            session.last_intent = last_intent
        if document_ref is not None and document_ref not in session.referenced_documents:
            session.referenced_documents.append(document_ref)
        
        session.updated_at = datetime.now().isoformat()
        
        self._save_metadata()
        return session
    
    def rename_session(self, session_id: str, title: str) -> bool:
        """重命名会话
        
        Args:
            session_id: 会话 ID
            title: 新标题
            
        Returns:
            操作是否成功
        """
        result = self.update_session(session_id, title=title)
        if result:
            logger.info(f"会话重命名: {session_id} -> {title}")
        return result is not None
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        同时删除 .jsonl 文件和元数据
        
        Args:
            session_id: 会话 ID
            
        Returns:
            操作是否成功
        """
        metadata = self._load_metadata()
        
        # 删除元数据
        if session_id in metadata:
            del metadata[session_id]
            self._save_metadata()
        
        # 删除 .jsonl 文件
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        jsonl_file = self.base_dir / f"{safe_id}.jsonl"
        
        if jsonl_file.exists():
            jsonl_file.unlink()
            logger.info(f"删除会话文件: {jsonl_file}")
        
        logger.info(f"删除会话: {session_id}")
        return True
    
    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        metadata = self._load_metadata()
        
        if session_id in metadata:
            return True
        
        # 检查 .jsonl 文件是否存在
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        jsonl_file = self.base_dir / f"{safe_id}.jsonl"
        return jsonl_file.exists()
    
    async def generate_title(self, session_id: str, first_user_input: str) -> str:
        """生成会话标题
        
        使用 LLM 生成标题，如果 LLM 不可用则使用简单截取策略
        
        Args:
            session_id: 会话 ID
            first_user_input: 用户第一句话
            
        Returns:
            生成的标题
        """
        title = None
        
        # 尝试使用 LLM 生成
        if self.title_generator:
            try:
                title = await self.title_generator(first_user_input)
                title = title.strip()[:50]  # 限制长度
            except Exception as e:
                logger.warning(f"LLM 生成标题失败: {e}")
        
        # 回退到简单截取
        if not title:
            title = first_user_input[:20].strip()
            if len(first_user_input) > 20:
                title += "..."
        
        # 更新元数据
        self.update_session(session_id, title=title)
        logger.info(f"生成会话标题: {session_id} -> {title}")
        
        return title
    
    def increment_turn_count(self, session_id: str) -> None:
        """增加会话轮次计数"""
        metadata = self._load_metadata()
        
        if session_id not in metadata:
            # 会话不存在，尝试同步
            self._sync_session_from_jsonl(session_id)
            if session_id not in metadata:
                # 创建新会话
                self.create_session(session_id)
        
        session = metadata.get(session_id)
        if session:
            session.turn_count += 1
            session.updated_at = datetime.now().isoformat()
            self._save_metadata()
    
    def _sync_all_sessions(self) -> None:
        """同步所有 .jsonl 文件的元数据"""
        metadata = self._load_metadata()
        
        # 扫描所有 .jsonl 文件
        for jsonl_file in self.base_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            
            if session_id not in metadata:
                self._sync_session_from_jsonl(session_id)
    
    def _sync_session_from_jsonl(self, session_id: str) -> SessionMetadata | None:
        """从 .jsonl 文件同步会话元数据（旧会话兼容）
        
        Args:
            session_id: 会话 ID
            
        Returns:
            同步后的元数据，文件不存在时返回 None
        """
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        jsonl_file = self.base_dir / f"{safe_id}.jsonl"
        
        if not jsonl_file.exists():
            return None
        
        # 解析 .jsonl 文件获取元数据
        turn_count = 0
        first_user_input = None
        last_intent = "chitchat"
        referenced_documents: list[str] = []
        first_timestamp = None
        last_timestamp = None
        
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    record_type = record.get("type")
                    
                    if record_type == "turn":
                        turn_count += 1
                        
                        # 记录第一轮用户输入
                        if first_user_input is None:
                            first_user_input = record.get("user_input", "")
                        
                        # 更新最后意图
                        last_intent = record.get("intent_type", "chitchat")
                        
                        # 收集引用文档
                        doc_ref = record.get("document_ref")
                        if doc_ref and doc_ref not in referenced_documents:
                            referenced_documents.append(doc_ref)
                        
                        # 记录时间戳
                        timestamp = record.get("timestamp")
                        if timestamp:
                            if first_timestamp is None:
                                first_timestamp = timestamp
                            last_timestamp = timestamp
        
        except Exception as e:
            logger.error(f"解析会话文件失败 {jsonl_file}: {e}")
            return None
        
        # 生成标题
        if first_user_input:
            title = first_user_input[:20].strip()
            if len(first_user_input) > 20:
                title += "..."
        else:
            # 如果是文档名格式的旧会话
            if session_id.endswith(".md"):
                title = session_id
            else:
                title = f"会话 - {session_id[:8]}"
        
        # 创建元数据
        metadata = self._load_metadata()
        
        session = SessionMetadata(
            session_id=session_id,
            title=title,
            created_at=first_timestamp or datetime.now().isoformat(),
            updated_at=last_timestamp or datetime.now().isoformat(),
            turn_count=turn_count,
            last_intent=last_intent,
            referenced_documents=referenced_documents,
        )
        
        metadata[session_id] = session
        self._save_metadata()
        
        logger.info(f"同步旧会话元数据: {session_id} (轮次: {turn_count})")
        return session
