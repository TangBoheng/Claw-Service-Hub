"""Chat Channel Manager - 频道管理器"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional


class ChatChannel:
    """聊天频道 - 两个智能体之间的通讯通道"""

    def __init__(
        self,
        channel_id: str = None,
        provider_id: str = None,
        consumer_id: str = None,
        service_id: str = None,
    ):
        self.channel_id = channel_id or f"ch_{uuid.uuid4().hex[:12]}"
        self.provider_id = provider_id  # 服务提供者
        self.consumer_id = consumer_id  # 服务使用者
        self.service_id = service_id  # 关联服务
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "active"  # active | closed

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "provider_id": self.provider_id,
            "consumer_id": self.consumer_id,
            "service_id": self.service_id,
            "created_at": self.created_at,
            "status": self.status,
        }

    def close(self):
        """关闭频道"""
        self.status = "closed"


class ChatChannelManager:
    """频道管理器 - 创建/获取/关闭频道"""

    def __init__(self):
        self._channels: Dict[str, ChatChannel] = {}
        # service_id -> channel_id 映射（用于快速查找）
        self._service_channels: Dict[str, str] = {}

    def create_channel(
        self,
        service_id: str,
        provider_id: str,
        consumer_id: str = None,
    ) -> ChatChannel:
        """创建频道（服务注册时自动创建）"""
        # 检查是否已存在该服务的频道
        if service_id in self._service_channels:
            existing_channel_id = self._service_channels[service_id]
            return self._channels[existing_channel_id]

        channel = ChatChannel(
            provider_id=provider_id,
            consumer_id=consumer_id,
            service_id=service_id,
        )

        self._channels[channel.channel_id] = channel
        self._service_channels[service_id] = channel.channel_id

        print(f"[ChatChannel] Created channel {channel.channel_id} for service {service_id}")
        return channel

    def get_channel(self, channel_id: str) -> Optional[ChatChannel]:
        """获取频道"""
        return self._channels.get(channel_id)

    def get_channel_by_service(self, service_id: str) -> Optional[ChatChannel]:
        """通过 service_id 获取频道"""
        channel_id = self._service_channels.get(service_id)
        if channel_id:
            return self._channels.get(channel_id)
        return None

    def close_channel(self, channel_id: str) -> bool:
        """关闭频道"""
        channel = self._channels.get(channel_id)
        if channel:
            channel.close()
            # 清理映射
            if channel.service_id in self._service_channels:
                del self._service_channels[channel.service_id]
            return True
        return False

    def list_channels(self) -> list:
        """列出所有频道"""
        return [ch.to_dict() for ch in self._channels.values()]


# 全局频道管理器
_channel_manager: Optional[ChatChannelManager] = None


def get_channel_manager() -> ChatChannelManager:
    """获取全局频道管理器"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChatChannelManager()
    return _channel_manager