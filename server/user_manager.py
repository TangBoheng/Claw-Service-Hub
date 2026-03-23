"""
用户注册与认证模块
负责用户的创建、认证和管理
支持服务级别的访问控制
"""

import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


class User:
    """用户实体"""

    def __init__(
        self,
        user_id: str,
        name: str = None,
        api_key: str = None,
        created_at: datetime = None,
        is_active: bool = True,
    ):
        self.user_id = user_id
        self.name = name or f"user_{user_id[:8]}"
        self.api_key = api_key or self._generate_api_key()
        self.created_at = created_at or datetime.now(timezone.utc)
        self.is_active = is_active

    def _generate_api_key(self) -> str:
        """生成用户 API Key"""
        return f"ush_{uuid.uuid4().hex}"

    def verify_api_key(self, api_key: str) -> bool:
        """验证 API Key"""
        return self.is_active and self.api_key == api_key

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }

    def to_metadata_dict(self) -> dict:
        """返回轻量级 metadata（不包含 API Key）"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """从字典创建"""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            user_id=data["user_id"],
            name=data.get("name"),
            api_key=data.get("api_key"),
            created_at=created_at,
            is_active=data.get("is_active", True),
        )


class UserManager:
    """
    用户管理器
    负责用户的创建、认证和管理
    支持从 SQLite 加载持久化数据
    """

    def __init__(self, db_path: str = None, storage=None):
        """
        Initialize UserManager.

        Args:
            db_path: Path to SQLite database file for persistence (optional)
            storage: Storage instance (optional, for sharing with other managers)
        """
        # 用户存储: user_id -> User
        self._users: Dict[str, User] = {}
        
        # API Key 索引: api_key -> user_id (快速查找)
        self._api_key_index: Dict[str, str] = {}

        # Storage for persistence
        self._storage = storage
        self._db_path = db_path

        # Load existing users from storage if available
        if db_path:
            self._load_from_storage()

    def _load_from_storage(self):
        """Load users from SQLite storage."""
        if not self._storage:
            from server.storage import Storage
            self._storage = Storage(self._db_path)

        try:
            users = self._storage.get_all_users()
            for user_data in users:
                user = User.from_dict(user_data)
                self._users[user.user_id] = user
                self._api_key_index[user.api_key] = user.user_id
        except Exception as e:
            print(f"[UserManager] Failed to load users: {e}")
            pass  # Ignore if storage not available

    def _save_user(self, user: User):
        """Save user to storage."""
        if self._storage:
            self._storage.save_user(user.to_dict())

    def create_user(self, name: str = None) -> User:
        """
        创建新用户
        
        Args:
            name: 用户名称（可选，默认自动生成）
            
        Returns:
            User 实例
        """
        user_id = str(uuid.uuid4())[:12]
        user = User(user_id=user_id, name=name)
        
        self._users[user.user_id] = user
        self._api_key_index[user.api_key] = user.user_id
        
        # Persist to storage
        self._save_user(user)
        
        print(f"[UserManager] User created: {user.user_id} (name={user.name})")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """通过 API Key 获取用户"""
        user_id = self._api_key_index.get(api_key)
        if user_id:
            return self._users.get(user_id)
        return None

    def verify_api_key(self, api_key: str) -> Optional[dict]:
        """
        验证 API Key
        
        Returns:
            {"valid": bool, "user": User or None, "reason": str}
        """
        if not api_key:
            return {"valid": False, "user": None, "reason": "API Key 不能为空"}
        
        user = self.get_user_by_api_key(api_key)
        
        if not user:
            return {"valid": False, "user": None, "reason": "无效的 API Key"}
        
        if not user.is_active:
            return {"valid": False, "user": user, "reason": "用户已被禁用"}
        
        return {"valid": True, "user": user, "reason": ""}

    def list_users(self, active_only: bool = False) -> List[dict]:
        """列出所有用户"""
        result = []
        for user in self._users.values():
            if active_only and not user.is_active:
                continue
            result.append(user.to_metadata_dict())
        return result

    def deactivate_user(self, user_id: str) -> bool:
        """禁用用户"""
        user = self._users.get(user_id)
        if user:
            user.is_active = False
            self._save_user(user)
            return True
        return False

    def activate_user(self, user_id: str) -> bool:
        """启用用户"""
        user = self._users.get(user_id)
        if user:
            user.is_active = True
            self._save_user(user)
            return True
        return False

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        user = self._users.pop(user_id, None)
        if user:
            self._api_key_index.pop(user.api_key, None)
            if self._storage:
                self._storage.delete_user(user_id)
            return True
        return False


# 全局实例
user_manager = UserManager()