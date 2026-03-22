"""
Skill 查询客户端 - 用于 subagent2 通过 skill 方式发现和使用服务

支持 OpenClaw 风格的 skill 查询：
- discover: 发现可用服务
- get_docs: 获取服务文档
- establish_channel: 建立服务通道
- call_service: 调用服务
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol


class SkillQueryClient:
    """
    Skill 查询客户端

    用于 subagent2 场景：
    - 通过 skill 方式查询可用服务
    - 获取服务文档和接口描述
    - 建立服务通道
    - 调用远程服务

    用法:
        client = SkillQueryClient()
        await client.connect("ws://localhost:8765")

        # 发现服务
        services = await client.discover(tags=["image", "coco"])

        # 获取文档
        docs = await client.get_docs(service_id)

        # 建立通道并调用
        channel = await client.establish_channel(service_id)
        result = await client.call_service(channel, "get_image", {"id": "123"})
    """

    def __init__(self, hub_url: str = "ws://localhost:8765", client_type: str = "skill_consumer"):
        self.hub_url = hub_url
        self.client_type = client_type
        self.client_id = str(uuid.uuid4())[:8]

        # 运行时状态
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self._connected_services: Dict[str, dict] = {}  # service_id -> connection_info

        # 用于等待响应
        self._response_futures: Dict[str, asyncio.Future] = {}

    async def connect(self):
        """连接到云端"""
        print(f"[SkillClient] Connecting to {self.hub_url}...")

        self.websocket = await websockets.connect(self.hub_url, ping_interval=None)

        self.running = True

        # 发送连接消息（消费者身份）
        connect_msg = {
            "type": "connect",
            "client_type": self.client_type,
            "client_id": self.client_id,
        }

        await self.websocket.send(json.dumps(connect_msg))

        # 启动接收循环
        asyncio.create_task(self._receive_loop())

        print(f"[SkillClient] Connected as consumer: {self.client_id}")

    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        print(f"[SkillClient] Disconnected")

    async def _receive_loop(self):
        """接收并处理云端消息"""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[SkillClient] Connection closed")
            self.running = False
        except Exception as e:
            print(f"[SkillClient] Receive error: {e}")

    async def _process_message(self, raw_message: str):
        """处理接收到的消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            request_id = message.get("request_id")

            if msg_type == "skill_list":
                # 服务列表响应
                self._resolve_future(request_id, message.get("skills", []))

            elif msg_type == "service_docs":
                # 服务文档响应
                self._resolve_future(request_id, message)

            elif msg_type == "channel_established":
                # 通道建立成功
                service_id = message.get("service_id")
                self._connected_services[service_id] = {
                    "channel_id": message.get("channel_id"),
                    "tunnel_id": message.get("tunnel_id"),
                    "established_at": datetime.now().isoformat(),
                }
                self._resolve_future(request_id, message)

            elif msg_type == "service_response":
                # 服务调用响应
                self._resolve_future(request_id, message.get("response", {}))

            elif msg_type == "error":
                # 错误响应
                self._resolve_future(request_id, {"error": message.get("message", "Unknown error")})

            elif msg_type == "key_request_response":
                # Key 请求响应
                self._resolve_future(request_id, message)

            elif msg_type == "ping":
                await self.websocket.send(json.dumps({"type": "pong"}))

        except json.JSONDecodeError:
            print(f"[SkillClient] Invalid JSON: {raw_message[:100]}")
        except Exception as e:
            print(f"[SkillClient] Error processing message: {e}")

    def _resolve_future(self, request_id: str, result: Any):
        """解析等待中的 future"""
        if request_id and request_id in self._response_futures:
            future = self._response_futures.pop(request_id)
            if not future.done():
                future.set_result(result)

    async def _send_request(self, msg_type: str, payload: dict, timeout: float = 30.0) -> Any:
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

    # ===== Skill 查询接口 =====

    async def discover(
        self,
        query: str = "",
        tags: List[str] = None,
        execution_mode: str = None,
        status: str = "online",
    ) -> List[dict]:
        """
        发现可用服务（OpenClaw 风格的 skill 发现）

        Args:
            query: 搜索关键词
            tags: 标签过滤
            execution_mode: 执行模式过滤 ("external", "remote", "local")
            status: 服务状态过滤

        Returns:
            服务描述符列表
        """
        result = await self._send_request(
            "skill_discover",
            {
                "query": query,
                "tags": tags or [],
                "execution_mode": execution_mode,
                "status": status,
            },
        )

        if isinstance(result, list):
            return result
        return result.get("skills", [])

    async def get_docs(self, service_id: str) -> dict:
        """
        获取服务文档和接口描述

        Args:
            service_id: 服务ID

        Returns:
            包含 documentation, interface_spec 的字典
        """
        result = await self._send_request("get_service_docs", {"service_id": service_id})

        return result

    async def get_skill_doc(self, service_id: str) -> Optional[str]:
        """
        获取服务的 SKILL.md 完整内容

        Args:
            service_id: 服务ID

        Returns:
            SKILL.md 内容或 None
        """
        result = await self._send_request("get_skill_doc", {"service_id": service_id})

        if isinstance(result, str):
            return result
        return result.get("skill_doc")

    # ===== 通道管理 =====

    async def establish_channel(self, service_id: str, timeout: float = 30.0) -> dict:
        """
        建立到服务的通道

        Args:
            service_id: 目标服务ID
            timeout: 超时时间

        Returns:
            包含 channel_id, tunnel_id 的字典
        """
        result = await self._send_request(
            "establish_channel",
            {"service_id": service_id, "consumer_client_id": self.client_id},
            timeout=timeout,
        )

        return result

    async def close_channel(self, service_id: str):
        """关闭服务通道"""
        if service_id in self._connected_services:
            await self._send_request(
                "close_channel",
                {
                    "service_id": service_id,
                    "channel_id": self._connected_services[service_id].get("channel_id"),
                },
            )
            del self._connected_services[service_id]

    # ===== 服务调用 =====

    async def call_service(
        self,
        service_id: str,
        method: str,
        params: dict = None,
        key: str = None,
        timeout: float = 60.0,
    ) -> dict:
        """
        调用远程服务

        Args:
            service_id: 服务ID（会自动使用已建立的通道）
            method: 调用方法名
            params: 方法参数
            key: 可选的访问 Key
            timeout: 超时时间

        Returns:
            服务响应
        """
        # 检查是否已建立通道
        if service_id not in self._connected_services:
            # 自动建立通道
            channel_result = await self.establish_channel(service_id)
            if "error" in channel_result:
                return channel_result

        connection_info = self._connected_services.get(service_id, {})
        tunnel_id = connection_info.get("tunnel_id")

        if not tunnel_id:
            return {"error": "Failed to get tunnel_id"}

        # 发送服务调用请求
        payload = {
            "service_id": service_id,
            "tunnel_id": tunnel_id,
            "method": method,
            "params": params or {},
        }
        if key:
            payload["key"] = key

        result = await self._send_request("call_service", payload, timeout=timeout)

        return result

    async def call_with_channel(
        self, channel: dict, method: str, params: dict = None, timeout: float = 60.0
    ) -> dict:
        """
        使用指定的通道调用服务

        Args:
            channel: 通道信息（establish_channel 返回的结果）
            method: 调用方法名
            params: 方法参数
            timeout: 超时时间

        Returns:
            服务响应
        """
        tunnel_id = channel.get("tunnel_id")
        service_id = channel.get("service_id")

        if not tunnel_id:
            return {"error": "Invalid channel: missing tunnel_id"}

        result = await self._send_request(
            "call_service",
            {
                "service_id": service_id,
                "tunnel_id": tunnel_id,
                "method": method,
                "params": params or {},
            },
            timeout=timeout,
        )

        return result

    async def request_key(self, service_id: str, purpose: str = "") -> dict:
        """
        请求服务的访问 Key

        Args:
            service_id: 服务ID
            purpose: 用途说明

        Returns:
            {"success": True, "key": "...", "lifecycle": {...}}
            或 {"success": False, "reason": "..."}
        """
        print(f"[SkillClient] request_key: service_id={service_id}, purpose={purpose}")

        # 发送 key_request 消息
        result = await self._send_request(
            "key_request", {"service_id": service_id, "purpose": purpose}, timeout=30.0
        )

        print(f"[SkillClient] request_key result: {result}")

        # 如果成功，存储 key
        if result.get("success") and result.get("key"):
            if not hasattr(self, "_keys"):
                self._keys = {}
            self._keys[service_id] = result["key"]
            result["lifecycle"] = result.get("lifecycle", {})

        return result

    def get_stored_key(self, service_id: str) -> str:
        """获取已存储的 Key"""
        if hasattr(self, "_keys"):
            return self._keys.get(service_id)
        return None

    def store_key(self, service_id: str, key: str):
        """存储 Key"""
        if not hasattr(self, "_keys"):
            self._keys = {}
        self._keys[service_id] = key


class SkillConsumer:
    """
    Skill 消费者 - 简化版使用示例

    示例:
        consumer = SkillConsumer(hub_url="ws://localhost:8765")

        # 使用 async with
        async with consumer:
            # 发现 COCO 服务
            services = await consumer.discover(query="coco")

            if services:
                service = services[0]
                # 获取文档
                docs = await consumer.get_docs(service["skill_id"])
                print(f"Service docs: {docs['documentation']}")

                # 调用服务
                result = await consumer.call(
                    service["skill_id"],
                    "list_images",
                    {"limit": 10}
                )
                print(f"Result: {result}")
    """

    def __init__(self, hub_url: str = "ws://localhost:8765"):
        self.client = SkillQueryClient(hub_url=hub_url)

    async def __aenter__(self):
        await self.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()

    async def discover(self, **kwargs) -> List[dict]:
        """发现服务"""
        return await self.client.discover(**kwargs)

    async def get_docs(self, service_id: str) -> dict:
        """获取文档"""
        return await self.client.get_docs(service_id)

    async def get_skill_doc(self, service_id: str) -> Optional[str]:
        """获取 SKILL.md"""
        return await self.client.get_skill_doc(service_id)

    async def establish_channel(self, service_id: str) -> dict:
        """建立通道"""
        return await self.client.establish_channel(service_id)

    async def call(self, service_id: str, method: str, params: dict = None) -> dict:
        """调用服务"""
        return await self.client.call_service(service_id, method, params)
