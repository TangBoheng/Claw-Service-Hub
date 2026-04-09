"""Chat Channel Manager - 聊天频道管理"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


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


class ChatMessage:
    """聊天消息"""

    def __init__(
        self,
        message_id: str,
        sender_id: str,
        service_id: str,
        content: str,
        target_agent: str = None,
        timestamp: str = None,
    ):
        self.message_id = message_id
        self.sender_id = sender_id
        self.service_id = service_id
        self.target_agent = target_agent
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "service_id": self.service_id,
            "target_agent": self.target_agent,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class ChatChannelManager:
    """聊天频道管理器"""

    def __init__(self):
        self._channels: Dict[str, ChatChannel] = {}  # channel_id -> ChatChannel
        self._service_channels: Dict[str, ChatChannel] = {}  # service_id -> ChatChannel
        self._messages: Dict[str, ChatMessage] = {}  # message_id -> ChatMessage

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
        """通过服务 ID 获取频道"""
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

    def store_message(self, message_id: str, sender_id: str, service_id: str,
                      content: str, target_agent: str = None) -> ChatMessage:
        """存储消息"""
        msg = ChatMessage(
            message_id=message_id,
            sender_id=sender_id,
            service_id=service_id,
            content=content,
            target_agent=target_agent,
        )
        self._messages[message_id] = msg
        return msg

    def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """获取消息"""
        return self._messages.get(message_id)

    def get_history(self, service_id: str = None, channel_id: str = None,
                    limit: int = 50) -> List[ChatMessage]:
        """获取聊天历史"""
        # 查找频道
        channel = None
        if channel_id:
            channel = self.get_channel(channel_id)
        elif service_id:
            channel = self.get_channel_by_service(service_id)

        if not channel:
            return []

        # 过滤该频道的消息
        messages = [
            msg for msg in self._messages.values()
            if msg.service_id == channel.service_id
        ]

        # 按时间排序，返回最新的 limit 条
        messages.sort(key=lambda m: m.timestamp, reverse=True)
        return messages[:limit]


# 全局单例
_channel_manager = None


def get_channel_manager() -> ChatChannelManager:
    """获取频道管理器单例"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChatChannelManager()
    return _channel_manager
