"""
服务注册与发现模块
参考 OpenClaw skill 的快速发现机制
"""

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


@dataclass
class ToolService:
    """工具服务元数据 - 类似 SKILL.md 的 metadata"""

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    endpoint: str = ""  # 本地服务地址（外部执行器地址）
    tags: List[str] = None
    metadata: dict = None

    # OpenClaw skill 风格字段
    emoji: str = "🔧"
    requires: dict = None  # {"bins": [...], "env": [...]}

    # 价格属性 (P0)
    price: Optional[float] = None  # 服务价格 (如 0.00 表示免费)
    price_unit: str = "次"  # 价格单位 (如 "次", "月", "年")

    # 状态
    status: str = "online"  # online, offline
    registered_at: str = ""
    last_heartbeat: str = ""

    # 隧道
    tunnel_id: Optional[str] = None

    # 新增：服务与执行器分离支持
    execution_mode: str = "local"  # "local" | "remote" | "external"
    provider_client_id: Optional[str] = None  # 注册此服务的管理客户端ID
    owner: Optional[str] = None  # 服务所有者用户ID (P0: 用户服务过滤)
    executor_endpoint: Optional[str] = None  # 外部执行器地址（如n8n webhook）
    interface_spec: dict = None  # 接口规范 {"methods": [...], "schema": {...}}

    # 用户访问控制
    allowed_users: List[str] = None  # 允许访问此服务的用户 ID 列表（空列表表示允许所有用户）

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.requires is None:
            self.requires = {}
        if self.interface_spec is None:
            self.interface_spec = {}
        if self.allowed_users is None:
            self.allowed_users = []
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_metadata_dict(self) -> dict:
        """返回轻量级 metadata 字典，用于广播和发现"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "emoji": self.emoji,
            "requires": self.requires,
            "status": self.status,
            "tunnel_id": self.tunnel_id,
            "execution_mode": self.execution_mode,
            "provider_client_id": self.provider_client_id,
            "owner": self.owner,  # 服务所有者
            "price": self.price,  # 服务价格
            "price_unit": self.price_unit,  # 价格单位
            "allowed_users": self.allowed_users,  # 添加 allowed_users 到 metadata
        }

    def to_skill_descriptor(self) -> dict:
        """返回 skill 风格描述符，用于 skill 方式查询"""
        return {
            "skill_id": self.id,
            "id": self.id,  # 兼容字段
            "service_id": self.id,  # 兼容字段
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "emoji": self.emoji,
            "tags": self.tags,
            "requires": self.requires,
            "execution_mode": self.execution_mode,
            "interface_spec": self.interface_spec,
            "status": self.status,
            "owner": self.owner,  # 服务所有者
            "price": self.price,  # 服务价格
            "price_unit": self.price_unit,  # 价格单位
            "allowed_users": self.allowed_users,  # 添加 allowed_users
        }

    def can_access(self, user_id: str) -> bool:
        """检查用户是否有权访问此服务
        
        Args:
            user_id: 用户 ID
            
        Returns:
            True 如果用户有权访问，False 否则
        """
        # 如果 allowed_users 为空列表或 None，表示允许所有用户访问
        if not self.allowed_users:
            return True
        # 检查用户是否在允许列表中
        return user_id in self.allowed_users

    @classmethod
    def from_dict(cls, data: dict) -> "ToolService":
        return cls(**data)


class ServiceRegistry:
    """
    服务注册表 - 参考 skill 扫描发现机制

    类似 OpenClaw skill 的工作方式：
    - skill: 启动时扫描 skills/ 目录发现
    - registry: 节点启动时主动注册服务
    - 发现: REST API 查询 + 实时推送
    """

    def __init__(self, heartbeat_ttl: int = 60):
        """
        Args:
            heartbeat_ttl: 心跳超时秒数，默认60秒
        """
        self._services: Dict[str, ToolService] = {}
        self._skill_docs: Dict[str, str] = {}  # service_id -> skill.md 内容
        self._heartbeat_ttl = heartbeat_ttl
        self._callbacks: List[callable] = []

    async def register(self, service: ToolService, skill_doc: str = None) -> str:
        """注册服务，返回服务ID"""
        if not service.id:
            service.id = str(uuid.uuid4())[:8]

        service.registered_at = datetime.now(timezone.utc).isoformat()
        service.last_heartbeat = service.registered_at
        service.status = "online"

        self._services[service.id] = service

        # 存储 skill.md 内容（如果提供）
        if skill_doc:
            self._skill_docs[service.id] = skill_doc

        await self._notify_listeners("register", service)

        print(f"[Registry] Service registered: {service.name} (id={service.id})")
        return service.id

    async def unregister(self, service_id: str) -> bool:
        """注销服务"""
        if service_id in self._services:
            service = self._services.pop(service_id)
            # 同时清理 skill.md
            self._skill_docs.pop(service_id, None)
            await self._notify_listeners("unregister", service)
            print(f"[Registry] Service unregistered: {service.name} (id={service_id})")
            return True
        return False

    async def heartbeat(self, service_id: str) -> bool:
        """收到心跳"""
        if service_id in self._services:
            self._services[service_id].last_heartbeat = datetime.now(timezone.utc).isoformat()
            self._services[service_id].status = "online"
            return True
        return False

    def get(self, service_id: str) -> Optional[ToolService]:
        """获取单个服务"""
        return self._services.get(service_id)

    def get_skill_doc(self, service_id: str) -> Optional[str]:
        """获取服务的 skill.md 完整描述"""
        return self._skill_docs.get(service_id)

    def list_all(self) -> List[ToolService]:
        """列出所有服务"""
        return list(self._services.values())

    def list_all_metadata(self) -> List[dict]:
        """列出所有服务的轻量级 metadata"""
        return [s.to_metadata_dict() for s in self._services.values()]

    def list_all_skill_descriptors(self) -> List[dict]:
        """列出所有服务的 skill 风格描述符"""
        return [s.to_skill_descriptor() for s in self._services.values()]

    def find(
        self,
        name: str = None,
        tags: List[str] = None,
        status: str = None,
        execution_mode: str = None,
        owner: str = None,  # P0: 用户服务过滤
        min_price: float = None,  # P0: 价格范围
        max_price: float = None,
        sort_by: str = None,  # P0: 排序 (name, price, time)
        sort_order: str = "asc",  # asc or desc
        fuzzy: bool = True,  # P0: 模糊搜索开关
    ) -> List[ToolService]:
        """
        查找服务 - 类似 skill 的快速发现
        支持按名称、标签、状态、执行模式、价格范围过滤和排序
        
        Args:
            name: 服务名称 (支持模糊搜索)
            tags: 标签列表 (任一匹配)
            status: 服务状态
            execution_mode: 执行模式
            owner: 服务所有者用户ID (P0: 用户服务过滤)
            min_price: 最低价格
            max_price: 最高价格
            sort_by: 排序字段 (name, price, time)
            sort_order: 排序方向 (asc, desc)
            fuzzy: 是否启用模糊搜索 (默认开启)
        """
        results = list(self._services.values())

        # 名称过滤 - 支持模糊搜索
        if name:
            if fuzzy:
                # 模糊搜索: 检查名称是否包含搜索词 (不区分大小写)
                name_lower = name.lower()
                results = [s for s in results if name_lower in s.name.lower()]
            else:
                # 精确匹配
                results = [s for s in results if name.lower() == s.name.lower()]

        # 标签过滤 - 任一标签匹配即可
        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]

        # 状态过滤
        if status:
            results = [s for s in results if s.status == status]

        # 执行模式过滤
        if execution_mode:
            results = [s for s in results if s.execution_mode == execution_mode]

        # P0: 所有者过滤
        if owner:
            results = [s for s in results if s.owner == owner]

        # P0: 价格范围过滤
        if min_price is not None:
            results = [s for s in results if s.price is not None and s.price >= min_price]
        
        if max_price is not None:
            results = [s for s in results if s.price is not None and s.price <= max_price]

        # P0: 排序
        if sort_by:
            reverse = sort_order.lower() == "desc"
            if sort_by == "price":
                # 按价格排序 (None 价格排最后)
                results = sorted(
                    results, 
                    key=lambda s: s.price if s.price is not None else float('inf'),
                    reverse=reverse
                )
            elif sort_by == "name":
                # 按名称排序
                results = sorted(results, key=lambda s: s.name.lower(), reverse=reverse)
            elif sort_by == "time":
                # 按注册时间排序
                results = sorted(results, key=lambda s: s.registered_at, reverse=reverse)

        return results

    async def cleanup_stale(self):
        """清理超时离线服务"""
        now = datetime.now(timezone.utc)
        stale_ids = []

        for sid, service in self._services.items():
            last_hb = datetime.fromisoformat(service.last_heartbeat)
            if last_hb.tzinfo is None:
                last_hb = last_hb.replace(tzinfo=timezone.utc)
            elapsed = (now - last_hb).total_seconds()
            if elapsed > self._heartbeat_ttl:
                stale_ids.append(sid)
                # Debug: 打印心跳超时详情
                print(f"[Registry] DEBUG: {service.name} heartbeat elapsed: {elapsed:.1f}s > {self._heartbeat_ttl}s", flush=True)

        for sid in stale_ids:
            service = self._services.pop(sid, None)
            # 同时清理 skill_docs
            self._skill_docs.pop(sid, None)
            if service:
                service.status = "offline"
                await self._notify_listeners("offline", service)
                print(f"[Registry] Service stale: {service.name} (id={sid})")

    def add_listener(self, callback: callable):
        """添加状态变更监听器"""
        self._callbacks.append(callback)

    async def _notify_listeners(self, event: str, service: ToolService):
        for cb in self._callbacks:
            try:
                await cb(event, service)
            except Exception as e:
                print(f"[Registry] Listener error: {e}")


# 全局注册表实例
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    return _registry


def reset_registry():
    """重置全局注册表（用于测试）"""
    global _registry
    _registry = ServiceRegistry()
