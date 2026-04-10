"""Type definitions for Claw Client."""

from typing import Any, Awaitable, Callable, Dict, Protocol

# 消息回调类型
MessageCallback = Callable[[Dict[str, Any]], Awaitable[None]]

# 请求处理器类型
RequestHandler = Callable[..., Awaitable[Dict[str, Any]]]

# WebSocket 消息类型
WebSocketMessage = Dict[str, Any]

# 服务 ID 类型
ServiceId = str

# 通道 ID 类型
ChannelId = str

# Key 类型
ApiKey = str


class ServiceInfo(Protocol):
    """服务信息 Protocol"""
    service_id: ServiceId
    name: str
    description: str
    price: float


class ChannelInfo(Protocol):
    """通道信息 Protocol"""
    channel_id: ChannelId
    service_id: ServiceId
    status: str
