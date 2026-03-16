"""
隧道管理器 - WebSocket 隧道
类似 SSH 反向隧道，节点主动连接到云端，云端代理请求
"""
import asyncio
from typing import Dict, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid


@dataclass
class Tunnel:
    """隧道连接"""
    id: str
    service_id: str
    client_id: str  # 客户端标识
    created_at: str = ""
    last_active: str = ""
    status: str = "active"  # active, idle, closed
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_active = self.created_at
    
    def to_dict(self) -> dict:
        return asdict(self)


class TunnelManager:
    """
    隧道管理器
    
    工作流程：
    1. 节点通过 WebSocket 连接到云端
    2. 云端分配 tunnel_id
    3. 调用方通过 tunnel_id 发起请求
    4. 云端将请求通过 WebSocket 转发到对应节点
    5. 节点处理请求，返回结果
    
    消息协议：
    - client->server: {"type": "register", "service_id": "xxx", "capabilities": [...]}
    - server->client: {"type": "registered", "tunnel_id": "xxx"}
    - server->client: {"type": "request", "request_id": "xxx", "method": "xxx", "params": {...}}
    - client->server: {"type": "response", "request_id": "xxx", "result": {...}}
    """
    
    def __init__(self):
        self._tunnels: Dict[str, Tunnel] = {}  # tunnel_id -> Tunnel
        self._client_sessions: Dict[str, str] = {}  # client_id -> tunnel_id
        self._request_handlers: Dict[str, asyncio.Future] = {}  # request_id -> future
        self._callbacks: Dict[str, list] = {
            "connect": [],
            "disconnect": [],
            "request": [],
        }
    
    async def create_tunnel(self, service_id: str, client_id: str) -> Tunnel:
        """创建隧道"""
        tunnel = Tunnel(
            id=str(uuid.uuid4())[:12],
            service_id=service_id,
            client_id=client_id
        )
        
        self._tunnels[tunnel.id] = tunnel
        self._client_sessions[client_id] = tunnel.id
        
        print(f"[Tunnel] Created: {tunnel.id} for service {service_id}")
        
        for cb in self._callbacks["connect"]:
            await cb(tunnel)
        
        return tunnel
    
    async def close_tunnel(self, tunnel_id: str):
        """关闭隧道"""
        tunnel = self._tunnels.pop(tunnel_id, None)
        if tunnel:
            self._client_sessions.pop(tunnel.client_id, None)
            
            # 清理 pending requests
            for _, future in list(self._request_handlers.items()):
                if not future.done():
                    future.set_exception(Exception("Tunnel closed"))
            
            print(f"[Tunnel] Closed: {tunnel_id}")
            
            for cb in self._callbacks["disconnect"]:
                await cb(tunnel)
    
    def get_tunnel(self, tunnel_id: str) -> Optional[Tunnel]:
        return self._tunnels.get(tunnel_id)
    
    def get_tunnel_by_client(self, client_id: str) -> Optional[Tunnel]:
        tid = self._client_sessions.get(client_id)
        return self._tunnels.get(tid) if tid else None
    
    def list_tunnels(self) -> list:
        return list(self._tunnels.values())
    
    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def forward_request(
        self, 
        tunnel_id: str, 
        request_id: str, 
        method: str, 
        params: dict,
        timeout: float = 30.0
    ) -> dict:
        """
        转发请求到对应节点
        
        Args:
            tunnel_id: 目标隧道
            request_id: 请求ID
            method: 调用方法
            params: 方法参数
            timeout: 超时时间
            
        Returns:
            True if request was forwarded, False otherwise
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return False
        
        # 创建 future 等待响应
        future = asyncio.Future()
        self._request_handlers[request_id] = future
        
        # 构造请求消息
        message = {
            "type": "request",
            "request_id": request_id,
            "method": method,
            "params": params,
            "tunnel_id": tunnel_id
        }
        
        # 通知 request 监听器 (实际发送由外部 WebSocket handler 处理)
        for cb in self._callbacks["request"]:
            await cb(tunnel.client_id, message)
        
        try:
            # 等待响应（不在这里返回，由 handle_response 处理）
            await asyncio.wait_for(future, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            self._request_handlers.pop(request_id, None)
            return False
        except Exception as e:
            self._request_handlers.pop(request_id, None)
            print(f"[Tunnel] Forward request error: {e}")
            return False
    
    async def handle_response(self, request_id: str, response: dict):
        """处理来自节点的响应"""
        future = self._request_handlers.pop(request_id, None)
        if future and not future.done():
            future.set_result(response)
    
    async def update_activity(self, tunnel_id: str):
        """更新隧道活跃时间"""
        tunnel = self._tunnels.get(tunnel_id)
        if tunnel:
            tunnel.last_active = datetime.now(timezone.utc).isoformat()


# 全局隧道管理器
_tunnel_manager = TunnelManager()


def get_tunnel_manager() -> TunnelManager:
    return _tunnel_manager


def reset_tunnel_manager():
    """重置全局隧道管理器（用于测试）"""
    global _tunnel_manager
    _tunnel_manager = TunnelManager()