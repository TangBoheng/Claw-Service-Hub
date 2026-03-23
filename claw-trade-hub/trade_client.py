"""Trade Client - 交易客户端

支持挂牌、竞价、议价功能。
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional


class TradeClient:
    """交易客户端 - 挂牌/竞价/议价"""

    def __init__(self, hub_url: str = "ws://localhost:8765", agent_id: str = None):
        self.hub_url = hub_url
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.websocket = None
        self._message_queue = asyncio.Queue()
        self._running = False

    async def connect(self):
        """连接到 Hub"""
        import websockets
        self.websocket = await websockets.connect(self.hub_url)
        await self.websocket.send(json.dumps({
            "type": "connect",
            "client_type": "trade",
            "agent_id": self.agent_id,
        }))
        self._running = True
        asyncio.create_task(self._listen())
        print(f"[TradeClient] Connected to {self.hub_url}")

    async def _listen(self):
        """监听服务器消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "error":
                    # 处理错误消息
                    error_msg = data.get("message", "Unknown error")
                    error_code = data.get("error_code", "UNKNOWN_ERROR")
                    details = data.get("details", "")
                    print(f"[TradeClient] Error ({error_code}): {error_msg} - {details}")
                    await self._message_queue.put(data)
                elif msg_type in ("bid_create", "negotiation_offer", "negotiation_counter"):
                    await self._message_queue.put(data)
        except Exception as e:
            print(f"[TradeClient] Listen error: {e}")
        finally:
            self._running = False

    async def create_listing(self, title: str, description: str, price: float, category: str = "service") -> str:
        """创建挂牌"""
        if not self.websocket:
            await self.connect()
        listing_id = f"listing_{uuid.uuid4().hex[:12]}"
        await self.websocket.send(json.dumps({
            "type": "listing_create",
            "listing_id": listing_id,
            "agent_id": self.agent_id,
            "title": title,
            "description": description,
            "price": price,
            "category": category,
        }))
        return listing_id

    async def query_listings(self, category: str = None) -> list:
        """查询挂牌"""
        if not self.websocket:
            await self.connect()
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        await self.websocket.send(json.dumps({
            "type": "listing_query",
            "request_id": request_id,
            "category": category,
        }))
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
        await self.websocket.send(json.dumps({
            "type": "bid_create",
            "bid_id": bid_id,
            "agent_id": self.agent_id,
            "listing_id": listing_id,
            "price": price,
        }))
        return bid_id

    async def accept_bid(self, bid_id: str) -> bool:
        """接受出价"""
        if not self.websocket:
            await self.connect()
        await self.websocket.send(json.dumps({
            "type": "bid_accept",
            "bid_id": bid_id,
            "agent_id": self.agent_id,
        }))
        return True

    async def negotiate(self, listing_id: str, price: float, counter: bool = False, original_offer_id: str = None) -> str:
        """
        议价出价或还价
        
        Args:
            listing_id: 挂牌 ID
            price: 价格
            counter: 是否是还价
            original_offer_id: 原始 offer ID（仅在 counter=True 时使用）
            
        Returns:
            offer_id
        """
        if not self.websocket:
            await self.connect()
            
        # 如果是还价，使用原始 offer_id；否则生成新的
        if counter and original_offer_id:
            offer_id = original_offer_id  # 使用原始 offer_id 作为 counter ID
        else:
            offer_id = f"neg_{uuid.uuid4().hex[:12]}"
            
        msg_type = "negotiation_counter" if counter else "negotiation_offer"
        await self.websocket.send(json.dumps({
            "type": msg_type,
            "offer_id": offer_id,
            "agent_id": self.agent_id,
            "listing_id": listing_id,
            "price": price,
        }))
        return offer_id

    async def accept_negotiation(self, offer_id: str) -> bool:
        """接受议价"""
        if not self.websocket:
            await self.connect()
        await self.websocket.send(json.dumps({
            "type": "negotiation_accept",
            "offer_id": offer_id,
            "agent_id": self.agent_id,
        }))
        return True

    async def offers(self) -> AsyncGenerator[dict, None]:
        """监听报价/议价消息"""
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                yield msg
            except asyncio.TimeoutError:
                continue

    async def close(self):
        self._running = False
        if self.websocket:
            await self.websocket.close()