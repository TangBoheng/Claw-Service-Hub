"""
服务注册与发现模块
参考 OpenClaw skill 的快速发现机制
"""
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import uuid


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

    # 状态
    status: str = "online"  # online, offline
    registered_at: str = ""
    last_heartbeat: str = ""

    # 隧道
    tunnel_id: Optional[str] = None

    # 新增：服务与执行器分离支持
    execution_mode: str = "local"  # "local" | "remote" | "external"
    provider_client_id: Optional[str] = None  # 注册此服务的管理客户端ID
    executor_endpoint: Optional[str] = None  # 外部执行器地址（如n8n webhook）
    interface_spec: dict = None  # 接口规范 {"methods": [...], "schema": {...}}

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.requires is None:
            self.requires = {}
        if self.interface_spec is None:
            self.interface_spec = {}
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
            "provider_client_id": self.provider_client_id
        }

    def to_skill_descriptor(self) -> dict:
        """返回 skill 风格描述符，用于 skill 方式查询"""
        return {
            "skill_id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "emoji": self.emoji,
            "tags": self.tags,
            "requires": self.requires,
            "execution_mode": self.execution_mode,
            "interface_spec": self.interface_spec,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ToolService':
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
        execution_mode: str = None
    ) -> List[ToolService]:
        """
        查找服务 - 类似 skill 的快速发现
        支持按名称、标签、状态、执行模式过滤
        """
        results = self._services.values()

        if name:
            results = [s for s in results if name.lower() in s.name.lower()]

        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]

        if status:
            results = [s for s in results if s.status == status]

        if execution_mode:
            results = [s for s in results if s.execution_mode == execution_mode]

        return list(results)
    
    async def cleanup_stale(self):
        """清理超时离线服务"""
        now = datetime.now(timezone.utc)
        stale_ids = []
        
        for sid, service in self._services.items():
            last_hb = datetime.fromisoformat(service.last_heartbeat)
            if last_hb.tzinfo is None:
                last_hb = last_hb.replace(tzinfo=timezone.utc)
            if (now - last_hb).total_seconds() > self._heartbeat_ttl:
                stale_ids.append(sid)
        
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