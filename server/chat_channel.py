"""Chat Channel Manager - 聊天频道管理"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional


class ChatChannel:
    """聊天频道"""
    
    def __init__(
        self,
        channel_id: str,
        service_id: str,
        provider_id: str,
        consumer_id: str = None
    ):
        self.channel_id = channel_id
        self.service_id = service_id
        self.provider_id = provider_id
        self.consumer_id = consumer_id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "active"  # active, ended
    
    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "service_id": self.service_id,
            "provider_id": self.provider_id,
            "consumer_id": self.consumer_id,
            "created_at": self.created_at,
            "status": self.status
        }


class ChatChannelManager:
    """聊天频道管理器"""
    
    def __init__(self):
        self._channels: Dict[str, ChatChannel] = {}  # channel_id -> ChatChannel
        self._service_channels: Dict[str, ChatChannel] = {}  # service_id -> ChatChannel
    
    def create_channel(
        self,
        service_id: str,
        provider_id: str,
        consumer_id: str = None
    ) -> ChatChannel:
        """创建频道"""
        channel_id = f"ch_{uuid.uuid4().hex[:12]}"
        channel = ChatChannel(
            channel_id=channel_id,
            service_id=service_id,
            provider_id=provider_id,
            consumer_id=consumer_id
        )
        
        self._channels[channel_id] = channel
        self._service_channels[service_id] = channel
        
        return channel
    
    def get_channel(self, channel_id: str) -> Optional[ChatChannel]:
        """获取频道"""
        return self._channels.get(channel_id)
    
    def get_channel_by_service(self, service_id: str) -> Optional[ChatChannel]:
        """通过服务ID获取频道"""
        return self._service_channels.get(service_id)
    
    def bind_consumer(self, channel_id: str, consumer_id: str):
        """绑定消费者"""
        channel = self._channels.get(channel_id)
        if channel:
            channel.consumer_id = consumer_id
    
    def end_channel(self, channel_id: str):
        """结束频道"""
        channel = self._channels.get(channel_id)
        if channel:
            channel.status = "ended"


# 全局单例
_channel_manager = None

def get_channel_manager() -> ChatChannelManager:
    """获取频道管理器单例"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChatChannelManager()
    return _channel_manager