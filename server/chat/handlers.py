"""Chat WebSocket handlers for Claw Service Hub.

Handles WebSocket message processing for:
- Chat message sending
- Chat history retrieval
"""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Any, List, Optional

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection
    from server.chat.channel import ChatChannelManager, ChatMessage


class ChatHandler:
    """Chat message handler"""

    def __init__(
        self,
        channel_mgr: "ChatChannelManager",
        client_websockets: Dict[str, Any],
        messages: Dict[str, Any],
    ):
        self.channel_mgr = channel_mgr
        self.client_websockets = client_websockets
        self.messages = messages  # Reference to HubServer._chat_messages

    async def handle_chat_message(
        self, websocket: "ServerConnection", client_id: str, message: dict
    ):
        """处理 Chat 消息"""
        message_id = message.get("message_id")
        sender_id = message.get("sender_id", client_id)
        target_agent = message.get("target_agent")
        service_id = message.get("service_id")
        content = message.get("content", "")

        # 添加时间戳
        message["timestamp"] = datetime.now(timezone.utc).isoformat()

        # 存储消息
        self.messages[message_id] = message

        # 通过 service_id 查找频道和目标
        if service_id:
            channel = self.channel_mgr.get_channel_by_service(service_id)
            if channel:
                # 转发给 Provider
                provider_ws = self.client_websockets.get(channel.provider_id)
                if provider_ws:
                    await provider_ws.send(json.dumps({
                        "type": "chat_message",
                        "message_id": message_id,
                        "sender_id": sender_id,
                        "service_id": service_id,
                        "content": content,
                        "timestamp": message["timestamp"],
                    }))

                # 如果有 consumer，也转发
                if channel.consumer_id:
                    consumer_ws = self.client_websockets.get(channel.consumer_id)
                    if consumer_ws:
                        await consumer_ws.send(json.dumps({
                            "type": "chat_message",
                            "message_id": message_id,
                            "sender_id": sender_id,
                            "service_id": service_id,
                            "content": content,
                            "timestamp": message["timestamp"],
                        }))

                print(f"[Server] Chat message forwarded via channel {channel.channel_id}")
                return

        # 直接通过 target_agent 转发
        if target_agent:
            target_ws = self.client_websockets.get(target_agent)
            if target_ws:
                await target_ws.send(json.dumps(message))
                print(f"[Server] Chat message forwarded to {target_agent}")
                return
            else:
                print(f"[Server] Target agent {target_agent} not found")

        # 响应发送者确认收到
        await websocket.send(json.dumps({
            "type": "chat_message_ack",
            "message_id": message_id,
            "status": "delivered" if target_agent else "pending",
        }))

    async def handle_chat_history(
        self, websocket: "ServerConnection", client_id: str, message: dict
    ):
        """处理获取 Chat 历史消息"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        channel_id = message.get("channel_id")
        limit = message.get("limit", 50)

        # 查找频道
        channel = None
        if channel_id:
            channel = self.channel_mgr.get_channel(channel_id)
        elif service_id:
            channel = self.channel_mgr.get_channel_by_service(service_id)

        # 获取该频道的所有消息
        messages = []
        if channel:
            # 过滤该频道相关的消息（通过 service_id）
            for msg in self.messages.values():
                if msg.get("service_id") == channel.service_id:
                    messages.append(msg)

        # 限制数量
        messages = messages[-limit:]

        # 响应给客户端
        await websocket.send(json.dumps({
            "type": "chat_history_response",
            "request_id": request_id,
            "channel_id": channel_id or (channel.channel_id if channel else None),
            "service_id": service_id,
            "messages": messages,
            "total": len(messages),
        }))

        print(f"[Server] Chat history: {len(messages)} messages for {service_id or channel_id}")
