"""Chat Client - 通讯客户端

用于服务提供者和消费者之间的双向实时通讯。
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional


class ChatClient:
    """Chat 客户端 - 发送消息、获取历史、监听消息流"""

    def __init__(
        self,
        hub_url: str = "ws://localhost:8765",
        agent_id: str = None,
    ):
        """
        初始化 Chat 客户端

        Args:
            hub_url: Hub 服务器地址
            agent_id: 智能体 ID
        """
        self.hub_url = hub_url
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.websocket = None
        self._message_queue = asyncio.Queue()
        self._running = False

    async def connect(self):
        """连接到 Hub"""
        import websockets

        self.websocket = await websockets.connect(self.hub_url)
        # 发送连接消息
        await self.websocket.send(
            json.dumps(
                {
                    "type": "connect",
                    "client_type": "chat",
                    "agent_id": self.agent_id,
                }
            )
        )
        # 启动消息监听
        self._running = True
        asyncio.create_task(self._listen())
        print(f"[ChatClient] Connected to {self.hub_url} as {self.agent_id}")

    async def _listen(self):
        """监听服务器消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "chat_message":
                    # 收到聊天消息
                    await self._message_queue.put(data)
                elif msg_type == "connected":
                    print(f"[ChatClient] Server confirmed connection")
                elif msg_type == "error":
                    # 处理错误消息
                    error_msg = data.get("message", "Unknown error")
                    error_code = data.get("error_code", "UNKNOWN_ERROR")
                    details = data.get("details", "")
                    print(f"[ChatClient] Error ({error_code}): {error_msg} - {details}")
                    # 将错误放入队列供调用者处理
                    await self._message_queue.put(data)
                # 处理交易相关响应消息
                elif msg_type in ("listing_created", "listing_query_response", "bid_created", 
                                  "bid_accept_response", "negotiation_sent", "negotiation_counter_sent",
                                  "negotiation_accept_response", "bid_received", "negotiation_received",
                                  "bid_accepted", "negotiation_accepted", "negotiation_counter"):
                    # 放入消息队列等待处理
                    await self._message_queue.put(data)
        except Exception as e:
            print(f"[ChatClient] Listen error: {e}")
        finally:
            self._running = False

    async def send_message(
        self,
        target_agent: str = None,
        service_id: str = None,
        content: str = None,
    ) -> str:
        """
        发送消息

        Args:
            target_agent: 目标智能体 ID
            service_id: 通过服务找到智能体（优先使用）
            content: 消息内容

        Returns:
            message_id
        """
        if not self.websocket:
            await self.connect()

        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        message = {
            "type": "chat_message",
            "message_id": message_id,
            "sender_id": self.agent_id,
            "target_agent": target_agent,
            "service_id": service_id,
            "content": content,
        }

        await self.websocket.send(json.dumps(message))
        print(f"[ChatClient] Sent message {message_id}: {content[:50]}...")
        return message_id

    async def get_history(
        self,
        service_id: str = None,
        channel_id: str = None,
        limit: int = 50,
    ) -> list:
        """
        获取消息历史

        Args:
            service_id: 服务 ID
            channel_id: 频道 ID
            limit: 返回条数

        Returns:
            消息列表
        """
        if not self.websocket:
            await self.connect()

        request_id = f"req_{uuid.uuid4().hex[:8]}"
        await self.websocket.send(
            json.dumps(
                {
                    "type": "chat_history",
                    "request_id": request_id,
                    "service_id": service_id,
                    "channel_id": channel_id,
                    "limit": limit,
                }
            )
        )

        # 等待响应
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=5.0)
                if msg.get("request_id") == request_id:
                    return msg.get("messages", [])
            except asyncio.TimeoutError:
                break

        return []

    async def messages(self) -> AsyncGenerator[dict, None]:
        """
        监听消息流（异步迭代器）

        Usage:
            async for msg in client.messages():
                print(msg['content'])
        """
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                yield msg
            except asyncio.TimeoutError:
                continue

    async def close(self):
        """关闭连接"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
            print(f"[ChatClient] Disconnected")


    # ========== 交易相关方法 ==========

    async def create_listing(
        self,
        title: str,
        description: str,
        price: float,
        category: str = "service",
    ) -> str:
        """创建挂牌"""
        if not self.websocket:
            await self.connect()
        listing_id = f"listing_{uuid.uuid4().hex[:12]}"
        message = {
            "type": "listing_create",
            "listing_id": listing_id,
            "agent_id": self.agent_id,
            "title": title,
            "description": description,
            "price": price,
            "category": category,
        }
        await self.websocket.send(json.dumps(message))
        print(f"[ChatClient] Created listing {listing_id}: {title}")
        return listing_id

    async def query_listings(self, category: str = None) -> list:
        """查询挂牌"""
        if not self.websocket:
            await self.connect()
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        await self.websocket.send(
            json.dumps({"type": "listing_query", "request_id": request_id, "category": category})
        )
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=5.0)
                if msg.get("request_id") == request_id:
                    return msg.get("listings", [])
            except asyncio.TimeoutError:
                break
        return []

    async def create_bid(self, listing_id: str, price: float) -> str:
        """创建出价"""
        if not self.websocket:
            await self.connect()
        bid_id = f"bid_{uuid.uuid4().hex[:12]}"
        message = {
            "type": "bid_create",
            "bid_id": bid_id,
            "agent_id": self.agent_id,
            "listing_id": listing_id,
            "price": price,
        }
        await self.websocket.send(json.dumps(message))
        print(f"[ChatClient] Created bid {bid_id} for {listing_id}: {price}")
        return bid_id

    async def accept_bid(self, bid_id: str) -> bool:
        """接受出价"""
        if not self.websocket:
            await self.connect()
        await self.websocket.send(
            json.dumps({"type": "bid_accept", "bid_id": bid_id, "agent_id": self.agent_id})
        )
        print(f"[ChatClient] Accepted bid {bid_id}")
        return True

    async def negotiate(
        self,
        listing_id: str,
        price: float,
        counter: bool = False,
        original_offer_id: str = None,
        raise_on_error: bool = True,
    ) -> Optional[str]:
        """
        议价出价或还价
        
        Args:
            listing_id: 挂牌 ID
            price: 价格
            counter: 是否是还价
            original_offer_id: 原始 offer ID（仅在 counter=True 时使用）
            raise_on_error: 收到错误响应时是否抛出异常，False 时返回 None
            
        Returns:
            offer_id (成功时) 或 None (失败且 raise_on_error=False)
            
        Raises:
            Exception: 如果服务器返回错误且 raise_on_error=True
        """
        if not self.websocket:
            await self.connect()
            
        # 如果是还价，使用原始 offer_id；否则生成新的
        if counter and original_offer_id:
            offer_id = original_offer_id  # 使用原始 offer_id 作为 counter ID
        else:
            offer_id = f"neg_{uuid.uuid4().hex[:12]}"
            
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        msg_type = "negotiation_counter" if counter else "negotiation_offer"
        message = {
            "type": msg_type,
            "request_id": request_id,
            "offer_id": offer_id,
            "agent_id": self.agent_id,
            "listing_id": listing_id,
            "price": price,
        }
        
        await self.websocket.send(json.dumps(message))
        print(f"[ChatClient] Sent {msg_type} {offer_id}: {price}")
        
        # 等待服务器响应
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=10.0)
                
                # 检查是否是针对此请求的响应
                if msg.get("request_id") == request_id:
                    if msg.get("type") == "error":
                        error_msg = msg.get("message", "Unknown error")
                        error_code = msg.get("error_code", "UNKNOWN_ERROR")
                        print(f"[ChatClient] Error ({error_code}): {error_msg}")
                        if raise_on_error:
                            raise Exception(f"[{error_code}] {error_msg}")
                        return None
                    # 成功响应
                    print(f"[ChatClient] Negotiation {offer_id} accepted")
                    return offer_id
                    
            except asyncio.TimeoutError:
                print(f"[ChatClient] Timeout waiting for {msg_type} response")
                if raise_on_error:
                    raise TimeoutError(f"Timeout waiting for negotiation response")
                return None
                
        # 连接已关闭
        if raise_on_error:
            raise ConnectionError("Connection closed while waiting for response")
        return None

    async def accept_negotiation(self, offer_id: str) -> bool:
        """接受议价"""
        if not self.websocket:
            await self.connect()
        await self.websocket.send(
            json.dumps({"type": "negotiation_accept", "offer_id": offer_id, "agent_id": self.agent_id})
        )
        print(f"[ChatClient] Accepted negotiation {offer_id}")
        return True


# 便捷函数
async def send_chat_message(
    hub_url: str,
    agent_id: str,
    target_agent: str,
    content: str,
    service_id: str = None,
) -> str:
    """发送单条消息的便捷函数"""
    client = ChatClient(hub_url=hub_url, agent_id=agent_id)
    await client.connect()
    message_id = await client.send_message(
        target_agent=target_agent,
        service_id=service_id,
        content=content,
    )
    await client.close()
    return message_id