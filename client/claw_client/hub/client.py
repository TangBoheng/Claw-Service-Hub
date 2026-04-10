"""
Claw Service Hub - 统一客户端

整合服务提供者、消费者、管理型客户端的所有能力。
支持通过 pip 安装后直接使用。

安装:
    pip install claw-service-hub-client

使用:
    from claw_service_hub_client import HubClient
    
    hub = HubClient(url="ws://localhost:8765")
    await hub.connect()
"""

import asyncio
import json
import uuid
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol


class HubClient:
    """
    Claw Service Hub 统一客户端
    
    整合了服务管理、发现、调用、通讯、交易等所有能力。
    智能体可自主选择使用哪些功能。
    
    用法:
        hub = HubClient(url="ws://localhost:8765")
        await hub.connect()
        
        # 发布服务
        await hub.provide(service_id="my-service", description="...", price=10)
        
        # 发现服务
        services = await hub.search(query="关键词")
        
        # 调用服务
        key = await hub.request_key(service_id="target-service")
        result = await hub.call(service_id="target-service", method="query", params={}, key=key["key"])
    """

    def __init__(
        self,
        url: str = "ws://localhost:8765",
        name: str = None,
        description: str = "",
        heartbeat_interval: int = 15,
        auto_reconnect: bool = True,
    ):
        """
        初始化 HubClient
        
        Args:
            url: Hub 服务地址
            name: 客户端名称（可选）
            description: 客户端描述
            heartbeat_interval: 心跳间隔（秒）
            auto_reconnect: 是否自动重连
        """
        self.url = url
        self.name = name or f"client-{str(uuid.uuid4())[:8]}"
        self.description = description
        self.heartbeat_interval = heartbeat_interval
        self.auto_reconnect = auto_reconnect

        # 连接状态
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.client_id = str(uuid.uuid4())[:8]
        self.user_id: Optional[str] = None

        # 服务相关
        self._services: Dict[str, dict] = {}  # service_id -> service_info
        self._channels: Dict[str, dict] = {}  # service_id -> channel_info
        self._keys: Dict[str, str] = {}  # service_id -> key

        # 请求/响应管理
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._request_handlers: Dict[str, Callable] = {}

        # 消息回调
        self._message_callback: Optional[Callable] = None
        self._chat_callbacks: Dict[str, List[Callable]] = {
            "message": [],
            "chat_request": [],
            "trade_offer": [],
        }

        # 生命周期策略
        self._lifecycle_policy: Optional[dict] = None

    # ==================== 连接管理 ====================

    async def connect(self) -> bool:
        """
        建立与 Hub 的连接
        
        Returns:
            是否连接成功
        """
        print(f"[HubClient] Connecting to {self.url}...")

        try:
            self.websocket = await websockets.connect(self.url, ping_interval=None)
            self.running = True

            # 启动后台任务
            asyncio.create_task(self._receive_loop())
            asyncio.create_task(self._heartbeat_loop())

            print(f"[HubClient] Connected as: {self.client_id}")
            return True

        except Exception as e:
            print(f"[HubClient] Connection failed: {e}")
            return False

    async def disconnect(self):
        """断开与 Hub 的连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        print("[HubClient] Disconnected")

    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("[HubClient] Connection closed")
            self.running = False
            if self.auto_reconnect:
                await self._reconnect()
        except Exception as e:
            print(f"[HubClient] Receive error: {e}")

    async def _process_message(self, raw_message: str):
        """处理接收到的消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            request_id = message.get("request_id")

            # 响应类消息
            if msg_type in [
                "registered", "login_success", "service_list", "metadata_list",
                "skill_list", "service_docs", "channel_established", "service_response",
                "key_request_response", "error", "success", "rating_result",
                "listings_result", "bid_result", "offer_result", "transactions_result",
                "chat_result", "history_result", "rating_stats",
                # 用户相关响应
                "user_register_response", "user_auth_response"
            ]:
                self._resolve_future(request_id, message)

            # 推送类消息
            elif msg_type == "message":
                await self._handle_message(message)
            elif msg_type == "chat_request":
                await self._handle_chat_request(message)
            elif msg_type == "trade_offer":
                await self._handle_trade_offer(message)
            elif msg_type == "request":
                await self._handle_request(message)
            elif msg_type == "key_request":
                # 服务提供者收到 Key 请求
                await self._handle_key_request_from_server(message)
            elif msg_type == "ping":
                await self.websocket.send(json.dumps({"type": "pong"}))

        except json.JSONDecodeError:
            print(f"[HubClient] Invalid JSON: {raw_message[:100]}")
        except Exception as e:
            print(f"[HubClient] Error processing message: {e}")

    def _resolve_future(self, request_id: str, result: Any):
        """解析等待中的 future"""
        if request_id and request_id in self._response_futures:
            future = self._response_futures.pop(request_id)
            if not future.done():
                future.set_result(result)

    async def _send_request(
        self, msg_type: str, payload: dict, timeout: float = 30.0
    ) -> Any:
        """发送请求并等待响应"""
        if not self.websocket:
            raise RuntimeError("Not connected")

        request_id = str(uuid.uuid4())[:12]
        future = asyncio.Future()
        self._response_futures[request_id] = future

        message = {
            "type": msg_type,
            "request_id": request_id,
            "client_id": self.client_id,
            **payload,
        }

        await self.websocket.send(json.dumps(message))

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._response_futures.pop(request_id, None)
            return {"error": "Request timeout"}

    async def _reconnect(self):
        """自动重连"""
        print("[HubClient] Attempting to reconnect...")
        await asyncio.sleep(5)
        await self.connect()

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)
            if self.websocket:
                try:
                    await self.websocket.send(
                        json.dumps({"type": "heartbeat", "client_id": self.client_id})
                    )
                except Exception as e:
                    print(f"[HubClient] Heartbeat error: {e}")
                    self.running = False
                    break

    # ==================== 用户身份 ====================

    async def register(self, name: str) -> dict:
        """
        注册用户
        
        Args:
            name: 用户名
            
        Returns:
            {user_id, api_key, name}
        """
        result = await self._send_request("user_register", {"name": name})

        # 服务器返回 user_register_response
        if result.get("type") == "user_register_response" or result.get("success"):
            user = result.get("user", {})
            self.user_id = user.get("user_id")
            return {
                "user_id": user.get("user_id"),
                "api_key": user.get("api_key"),
                "name": user.get("name"),
            }

        return result

    async def login(self, api_key: str) -> dict:
        """
        登录验证
        
        Args:
            api_key: API密钥
            
        Returns:
            {user_id, name, is_active}
        """
        result = await self._send_request("user_auth", {"api_key": api_key})

        # 服务器返回 user_auth_response
        if result.get("type") == "user_auth_response" or result.get("success"):
            user = result.get("user", {})
            self.user_id = user.get("user_id")
            return {
                "user_id": user.get("user_id"),
                "name": user.get("name"),
                "is_active": True,
            }

        return result

    async def whoami(self) -> dict:
        """
        查看当前用户信息
        
        Returns:
            {user_id, name, ...}
        """
        return await self._send_request("whoami", {"client_id": self.client_id})

    # ==================== 服务管理 ====================

    async def provide(
        self,
        service_id: str,
        description: str,
        schema: dict = None,
        price: float = 0,
        floor_price: float = None,
        max_calls: int = None,
        ttl: int = None,
        tags: List[str] = None,
        metadata: dict = None,
    ) -> dict:
        """
        发布服务
        
        Args:
            service_id: 服务唯一标识
            description: 服务描述
            schema: 服务接口定义
            price: 价格（积分）
            floor_price: 底价（议价用）
            max_calls: 最大调用次数
            ttl: 有效期（秒）
            tags: 标签列表
            metadata: 额外元数据
            
        Returns:
            {service_id, status}
        """
        service_info = {
            "service_id": service_id,
            "name": service_id,
            "description": description,
            "schema": schema or {},
            "price": price,
            "floor_price": floor_price,
            "max_calls": max_calls,
            "ttl": ttl,
            "tags": tags or [],
            "metadata": metadata or {},
            "provider_id": self.client_id,
        }

        result = await self._send_request("register", {"service": service_info})

        if result.get("type") == "registered":
            self._services[service_id] = service_info
            return {"service_id": result.get("service_id"), "status": "registered"}

        return result

    async def unregister(self, service_id: str) -> dict:
        """
        注销服务
        
        Args:
            service_id: 服务ID
            
        Returns:
            {status}
        """
        result = await self._send_request("unregister", {"service_id": service_id})

        if service_id in self._services:
            del self._services[service_id]

        return result

    async def update(self, service_id: str, **kwargs) -> dict:
        """
        更新服务信息
        
        Args:
            service_id: 服务ID
            **kwargs: 要更新的字段
            
        Returns:
            {status}
        """
        return await self._send_request(
            "update_service", {"service_id": service_id, "updates": kwargs}
        )

    # ==================== 服务发现 ====================

    async def search(
        self,
        query: str = "",
        tags: List[str] = None,
        status: str = "online",
    ) -> List[dict]:
        """
        搜索服务
        
        Args:
            query: 搜索关键词
            tags: 标签过滤
            status: 状态过滤
            
        Returns:
            服务列表
        """
        result = await self._send_request(
            "skill_discover",
            {"query": query, "tags": tags or [], "status": status},
        )

        if isinstance(result, list):
            return result
        return result.get("skills", result.get("services", []))

    async def discover(self) -> List[dict]:
        """
        列出所有可用服务
        
        Returns:
            服务列表
        """
        return await self.search()

    async def get_info(self, service_id: str) -> dict:
        """
        获取服务详情
        
        Args:
            service_id: 服务ID
            
        Returns:
            服务详情
        """
        return await self._send_request("get_service_docs", {"service_id": service_id})

    # ==================== 服务调用 ====================

    async def request_key(self, service_id: str, purpose: str = "") -> dict:
        """
        请求访问凭证
        
        Args:
            service_id: 目标服务ID
            purpose: 用途说明
            
        Returns:
            {key, lifecycle}
        """
        result = await self._send_request(
            "key_request",
            {"service_id": service_id, "purpose": purpose},
            timeout=30.0,
        )

        if result.get("success") and result.get("key"):
            self._keys[service_id] = result["key"]
            return {
                "key": result["key"],
                "lifecycle": result.get("lifecycle", {}),
            }

        return result

    async def establish_channel(self, service_id: str) -> dict:
        """
        建立服务通道
        
        Args:
            service_id: 目标服务ID
            
        Returns:
            {channel_id, tunnel_id}
        """
        result = await self._send_request(
            "establish_channel",
            {"service_id": service_id, "consumer_client_id": self.client_id},
            timeout=30.0,
        )

        if result.get("type") == "channel_established" or result.get("channel_id"):
            self._channels[service_id] = {
                "channel_id": result.get("channel_id"),
                "tunnel_id": result.get("tunnel_id"),
            }
            return result

        return result

    async def call(
        self,
        service_id: str,
        method: str,
        params: dict = None,
        key: str = None,
    ) -> dict:
        """
        调用远程服务
        
        Args:
            service_id: 服务ID
            method: 调用方法
            params: 方法参数
            key: 访问凭证（可选）
            
        Returns:
            服务响应
        """
        # 确保通道已建立
        if service_id not in self._channels:
            channel_result = await self.establish_channel(service_id)
            if "error" in channel_result:
                return channel_result

        channel_info = self._channels.get(service_id, {})
        tunnel_id = channel_info.get("tunnel_id")

        if not tunnel_id:
            return {"error": "Failed to get tunnel_id"}

        payload = {
            "service_id": service_id,
            "tunnel_id": tunnel_id,
            "method": method,
            "params": params or {},
        }

        if key:
            payload["key"] = key
        elif service_id in self._keys:
            payload["key"] = self._keys[service_id]

        result = await self._send_request("call_service", payload, timeout=60.0)

        return result.get("response", result)

    async def close_channel(self, service_id: str) -> dict:
        """
        关闭通道
        
        Args:
            service_id: 服务ID
            
        Returns:
            {status}
        """
        if service_id in self._channels:
            result = await self._send_request(
                "close_channel",
                {
                    "service_id": service_id,
                    "channel_id": self._channels[service_id].get("channel_id"),
                },
            )
            del self._channels[service_id]
            return result

        return {"status": "not_found"}

    # ==================== 通讯（异步通道） ====================

    def on_message(self, callback: Callable[[dict], None]):
        """
        注册消息回调
        
        Args:
            callback: 回调函数，接收消息字典
        """
        self._message_callback = callback
        self._chat_callbacks["message"].append(callback)

    async def send(self, target: str, content: str, service_id: str = None) -> dict:
        """
        发送消息
        
        Args:
            target: 目标用户ID
            content: 消息内容
            service_id: 关联服务ID（可选）
            
        Returns:
            {status, message_id}
        """
        return await self._send_request(
            "chat",
            {
                "target": target,
                "content": content,
                "service_id": service_id,
                "sender": self.client_id,
            },
        )

    async def request_chat(self, service_id: str, message: str = "") -> dict:
        """
        请求通讯
        
        Args:
            service_id: 服务ID
            message: 附加消息
            
        Returns:
            {status, channel_id}
        """
        return await self._send_request(
            "request_chat",
            {"service_id": service_id, "message": message, "consumer_id": self.client_id},
        )

    async def accept_chat(self, consumer_id: str, message: str = "") -> dict:
        """
        接受通讯
        
        Args:
            consumer_id: 消费者ID
            message: 附加消息
            
        Returns:
            {status, channel_id}
        """
        return await self._send_request(
            "accept_chat",
            {"consumer_id": consumer_id, "message": message, "provider_id": self.client_id},
        )

    async def reject_chat(self, consumer_id: str, reason: str = "") -> dict:
        """
        拒绝通讯
        
        Args:
            consumer_id: 消费者ID
            reason: 拒绝原因
            
        Returns:
            {status}
        """
        return await self._send_request(
            "reject_chat",
            {"consumer_id": consumer_id, "reason": reason, "provider_id": self.client_id},
        )

    async def end_chat(self, channel_id: str, reason: str = "") -> dict:
        """
        结束通讯
        
        Args:
            channel_id: 频道ID
            reason: 结束原因
            
        Returns:
            {status}
        """
        return await self._send_request(
            "end_chat",
            {"channel_id": channel_id, "reason": reason},
        )

    async def history(self, channel_id: str, limit: int = 50) -> List[dict]:
        """
        获取历史消息
        
        Args:
            channel_id: 频道ID
            limit: 数量限制
            
        Returns:
            消息列表
        """
        result = await self._send_request(
            "history",
            {"channel_id": channel_id, "limit": limit},
        )
        return result.get("messages", [])

    async def _handle_message(self, message: dict):
        """处理收到的消息"""
        for callback in self._chat_callbacks["message"]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"[HubClient] Callback error: {e}")

    async def _handle_chat_request(self, message: dict):
        """处理通讯请求"""
        for callback in self._chat_callbacks["chat_request"]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"[HubClient] Chat request callback error: {e}")

    async def _handle_trade_offer(self, message: dict):
        """处理交易报价"""
        for callback in self._chat_callbacks["trade_offer"]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"[HubClient] Trade offer callback error: {e}")

    async def _handle_request(self, message: dict):
        """处理服务请求"""
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})

        handler = self._request_handlers.get(method)

        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**params)
                else:
                    result = handler(**params)
                response = {"result": result}
            except Exception as e:
                response = {"error": str(e)}
        else:
            response = {"error": f"Unknown method: {method}"}

        await self.websocket.send(
            json.dumps(
                {"type": "response", "request_id": request_id, "response": response}
            )
        )

    async def _handle_key_request_from_server(self, message: dict):
        """处理来自服务器的 Key 请求（作为服务提供者）"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        consumer_id = message.get("consumer_id")
        purpose = message.get("purpose", "")

        # 获取生命周期策略
        policy = self._lifecycle_policy or {"duration_seconds": 3600, "max_calls": 100}

        # 自动批准请求
        response = {
            "type": "key_response",
            "request_id": request_id,
            "approved": True,
            "consumer_id": consumer_id,
            "service_id": service_id,
            "lifecycle": {
                "duration_seconds": policy.get("duration_seconds", 3600),
                "max_calls": policy.get("max_calls", 100),
            },
            "reason": "Auto-approved",
        }

        await self.websocket.send(json.dumps(response))
        print(f"[HubClient] Key request approved for {consumer_id}")

    def register_handler(self, method: str, handler: Callable):
        """
        注册请求处理器
        
        Args:
            method: 方法名
            handler: 处理函数
        """
        self._request_handlers[method] = handler

    # ==================== 交易 ====================

    async def list(
        self,
        title: str,
        description: str,
        price: float,
        floor_price: float = None,
        category: str = "service",
        mode: str = "fixed",
    ) -> dict:
        """
        创建挂牌
        
        Args:
            title: 挂牌标题
            description: 详细描述
            price: 挂牌价格
            floor_price: 底价
            category: 类别
            mode: 模式 (fixed/bidding)
            
        Returns:
            {listing_id}
        """
        return await self._send_request(
            "create_listing",
            {
                "title": title,
                "description": description,
                "price": price,
                "floor_price": floor_price,
                "category": category,
                "mode": mode,
                "provider_id": self.client_id,
            },
        )

    async def query_listings(
        self,
        query: str = "",
        category: str = None,
        min_price: float = None,
        max_price: float = None,
    ) -> List[dict]:
        """
        查询挂牌
        
        Args:
            query: 搜索关键词
            category: 类别过滤
            min_price: 最低价格
            max_price: 最高价格
            
        Returns:
            挂牌列表
        """
        result = await self._send_request(
            "query_listings",
            {
                "query": query,
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
            },
        )
        return result.get("listings", [])

    async def bid(self, listing_id: str, price: float) -> dict:
        """
        出价
        
        Args:
            listing_id: 挂牌ID
            price: 出价金额
            
        Returns:
            {bid_id, status}
        """
        return await self._send_request(
            "bid",
            {"listing_id": listing_id, "price": price, "bidder_id": self.client_id},
        )

    async def accept_bid(self, bid_id: str) -> dict:
        """
        接受出价
        
        Args:
            bid_id: 出价ID
            
        Returns:
            {status, transaction_id}
        """
        return await self._send_request("accept_bid", {"bid_id": bid_id})

    async def negotiate(
        self,
        listing_id: str,
        price: float,
        counter: bool = False,
        original_offer_id: str = None,
    ) -> dict:
        """
        议价/还价
        
        Args:
            listing_id: 挂牌ID
            price: 还价金额
            counter: 是否为还价
            original_offer_id: 原始议价ID
            
        Returns:
            {offer_id, status}
        """
        return await self._send_request(
            "negotiate",
            {
                "listing_id": listing_id,
                "price": price,
                "counter": counter,
                "original_offer_id": original_offer_id,
                "party_id": self.client_id,
            },
        )

    async def accept_offer(self, offer_id: str) -> dict:
        """
        接受议价
        
        Args:
            offer_id: 议价ID
            
        Returns:
            {status, transaction_id}
        """
        return await self._send_request("accept_offer", {"offer_id": offer_id})

    async def cancel_listing(self, listing_id: str) -> dict:
        """
        取消挂牌
        
        Args:
            listing_id: 挂牌ID
            
        Returns:
            {status}
        """
        return await self._send_request("cancel_listing", {"listing_id": listing_id})

    async def transactions(self, role: str = "consumer", limit: int = 20) -> List[dict]:
        """
        查询交易记录
        
        Args:
            role: 角色 (consumer/provider)
            limit: 数量限制
            
        Returns:
            交易记录列表
        """
        result = await self._send_request(
            "transactions",
            {"role": role, "limit": limit, "user_id": self.client_id},
        )
        return result.get("transactions", [])

    # ==================== 生命周期/授权 ====================

    async def set_lifecycle_policy(
        self,
        duration_seconds: int = 3600,
        max_calls: int = 100,
    ) -> dict:
        """
        设置生命周期策略
        
        Args:
            duration_seconds: 有效时长（秒）
            max_calls: 最大调用次数
            
        Returns:
            {status}
        """
        self._lifecycle_policy = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls,
        }

        return await self._send_request(
            "lifecycle_policy",
            {"policy": self._lifecycle_policy, "client_id": self.client_id},
        )

    async def renew_key(self, service_id: str) -> dict:
        """
        续期 Key
        
        Args:
            service_id: 服务ID
            
        Returns:
            {key, lifecycle}
        """
        return await self._send_request(
            "renew_key",
            {"service_id": service_id, "client_id": self.client_id},
        )

    # ==================== 评分 ====================

    async def rate(self, service_id: str, score: int, comment: str = "") -> dict:
        """
        评价服务
        
        Args:
            service_id: 服务ID
            score: 评分 (1-5)
            comment: 评价内容
            
        Returns:
            {status}
        """
        return await self._send_request(
            "rate",
            {
                "service_id": service_id,
                "score": score,
                "comment": comment,
                "user_id": self.client_id,
            },
        )

    async def get_rating(self, service_id: str) -> dict:
        """
        获取服务评分
        
        Args:
            service_id: 服务ID
            
        Returns:
            {avg_score, count}
        """
        return await self._send_request("get_rating", {"service_id": service_id})

    # ==================== 心跳 ====================

    async def heartbeat(self) -> dict:
        """
        发送心跳
        
        Returns:
            {status}
        """
        if self.websocket:
            await self.websocket.send(
                json.dumps({"type": "heartbeat", "client_id": self.client_id})
            )
            return {"status": "sent"}
        return {"status": "not_connected"}


# ==================== 便捷类 ====================

class HubServiceProvider:
    """
    服务提供者快速启动器
    
    示例:
        provider = HubServiceProvider(
            service_id="my-service",
            description="提供某种能力",
            price=10
        )
        
        @provider.handler("query")
        async def handle_query(**params):
            return {"result": "..."}
        
        await provider.run()
    """

    def __init__(
        self,
        service_id: str,
        description: str,
        price: float = 0,
        hub_url: str = "ws://localhost:8765",
        **kwargs,
    ):
        self.client = HubClient(url=hub_url)
        self.service_id = service_id
        self.description = description
        self.price = price
        self.kwargs = kwargs

    def handler(self, method: str):
        """装饰器：注册方法处理器"""
        def decorator(func):
            self.client.register_handler(method, func)
            return func
        return decorator

    async def run(self):
        """启动服务"""
        await self.client.connect()
        await self.client.provide(
            service_id=self.service_id,
            description=self.description,
            price=self.price,
            **self.kwargs,
        )

        while self.client.running:
            await asyncio.sleep(1)

    async def stop(self):
        """停止服务"""
        await self.client.disconnect()


class HubConsumer:
    """
    服务消费者快速启动器
    
    示例:
        async with HubConsumer() as consumer:
            services = await consumer.search(query="关键词")
            result = await consumer.call(services[0]["service_id"], "query", {})
    """

    def __init__(self, hub_url: str = "ws://localhost:8765"):
        self.client = HubClient(url=hub_url)

    async def __aenter__(self):
        await self.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()

    def __getattr__(self, name):
        return getattr(self.client, name)
