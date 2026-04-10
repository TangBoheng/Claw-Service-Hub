"""Skill Query Client for Claw Service Hub.

Skill 查询客户端，用于发现和调用服务。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import BaseClient
from ..utils import serialize_message


class SkillQueryClient(BaseClient):
    """
    Skill 查询客户端 - 用于 subagent2 场景

    功能:
    - discover: 发现可用服务
    - get_docs: 获取服务文档
    - establish_channel: 建立服务通道
    - call_service: 调用服务

    用法:
        client = SkillQueryClient()
        async with client:
            services = await client.discover(tags=["image", "coco"])
            docs = await client.get_docs(service_id)
            channel = await client.establish_channel(service_id)
            result = await client.call_service(channel, "get_image", {"id": "123"})
    """

    def __init__(
        self,
        hub_url: str = "ws://localhost:8765",
        client_type: str = "skill_consumer",
        heartbeat_interval: int = 15,
    ):
        """
        初始化 Skill 查询客户端。

        Args:
            hub_url: Hub 服务地址
            client_type: 客户端类型
            heartbeat_interval: 心跳间隔（秒）
        """
        super().__init__(url=hub_url, heartbeat_interval=heartbeat_interval)
        self.client_type = client_type
        self._connected_services: Dict[str, dict] = {}
        self._stored_keys: Dict[str, str] = {}

    async def _on_connected(self):
        """连接建立后的处理。"""
        # 发送连接消息（消费者身份）
        connect_msg = {
            "type": "connect",
            "client_type": self.client_type,
            "client_id": self.client_id,
        }
        await self.websocket.send(serialize_message(connect_msg))
        print(f"[SkillQueryClient] Connected as consumer: {self.client_id}")

    async def _on_disconnected(self):
        """断开连接后的处理。"""
        self._connected_services.clear()
        self._stored_keys.clear()
        print("[SkillQueryClient] Disconnected")

    async def _handle_message(self, message: Dict[str, Any]):
        """处理特定类型的消息。"""
        msg_type = message.get("type")
        request_id = message.get("request_id")

        if msg_type == "skill_list":
            self._resolve_future(request_id, message.get("skills", []))

        elif msg_type == "service_docs":
            self._resolve_future(request_id, message)

        elif msg_type == "channel_established":
            service_id = message.get("service_id")
            self._connected_services[service_id] = {
                "channel_id": message.get("channel_id"),
                "tunnel_id": message.get("tunnel_id"),
                "established_at": datetime.now().isoformat(),
            }
            self._resolve_future(request_id, message)

        elif msg_type == "service_response":
            self._resolve_future(request_id, message.get("response", {}))

        elif msg_type == "error":
            self._resolve_future(request_id, {"error": message.get("message", "Unknown error")})

        elif msg_type == "key_request_response":
            self._resolve_future(request_id, message)

        elif msg_type == "ping":
            await self.websocket.send(serialize_message({"type": "pong"}))

    def _resolve_future(self, request_id: str, result: Any):
        """解析等待中的 future"""
        if request_id and request_id in self._response_futures:
            future = self._response_futures.pop(request_id)
            if not future.done():
                future.set_result(result)

    # ==================== 服务发现 ====================

    async def discover(
        self,
        query: str = "",
        tags: List[str] = None,
        execution_mode: str = None,
        owner: str = None,
        min_price: float = None,
        max_price: float = None,
        sort_by: str = None,
        sort_order: str = "asc",
        fuzzy: bool = True,
        timeout: float = 30.0,
    ) -> List[dict]:
        """
        发现服务。

        Args:
            query: 搜索关键词
            tags: 标签过滤
            execution_mode: 执行模式过滤
            owner: 服务所有者过滤
            min_price: 最低价格
            max_price: 最高价格
            sort_by: 排序字段 (name/price/time)
            sort_order: 排序方向 (asc/desc)
            fuzzy: 是否模糊搜索
            timeout: 超时时间

        Returns:
            服务列表
        """
        payload = {"query": query, "fuzzy": fuzzy}
        if tags:
            payload["tags"] = tags
        if execution_mode:
            payload["execution_mode"] = execution_mode
        if owner:
            payload["owner"] = owner
        if min_price is not None:
            payload["min_price"] = min_price
        if max_price is not None:
            payload["max_price"] = max_price
        if sort_by:
            payload["sort_by"] = sort_by
            payload["sort_order"] = sort_order

        response = await self._send_request("skill_discover", payload, timeout=timeout)
        return response.get("skills", [])

    async def get_docs(self, service_id: str, timeout: float = 30.0) -> dict:
        """获取服务文档"""
        response = await self._send_request("get_service_docs", {"service_id": service_id}, timeout=timeout)
        return response

    async def get_skill_doc(self, service_id: str, timeout: float = 30.0) -> Optional[str]:
        """获取 SKILL.md 文档"""
        response = await self._send_request("get_skill_doc", {"service_id": service_id}, timeout=timeout)
        return response.get("skill_doc")

    # ==================== 通道管理 ====================

    async def establish_channel(self, service_id: str, timeout: float = 30.0) -> dict:
        """建立服务通道"""
        response = await self._send_request("establish_channel", {"service_id": service_id}, timeout=timeout)
        return response

    async def close_channel(self, service_id: str):
        """关闭服务通道"""
        if service_id in self._connected_services:
            del self._connected_services[service_id]

    # ==================== 服务调用 ====================

    async def call_service(
        self,
        channel_info: dict,
        method: str,
        params: dict = None,
        timeout: float = 30.0,
    ) -> dict:
        """
        调用服务。

        Args:
            channel_info: 通道信息（from establish_channel）
            method: 方法名
            params: 方法参数
            timeout: 超时时间

        Returns:
            服务响应
        """
        tunnel_id = channel_info.get("tunnel_id")
        if not tunnel_id:
            return {"error": "No tunnel_id in channel_info"}

        return await self._send_request(
            msg_type="call_service",
            payload={"tunnel_id": tunnel_id, "method": method, "params": params or {}},
            timeout=timeout,
        )

    async def call_with_channel(
        self,
        service_id: str,
        method: str,
        params: dict = None,
        timeout: float = 60.0,
    ) -> dict:
        """
        自动建立通道并调用服务。

        Args:
            service_id: 服务 ID
            method: 方法名
            params: 方法参数
            timeout: 总超时时间

        Returns:
            服务响应
        """
        # 建立通道
        channel_info = await self.establish_channel(service_id, timeout=timeout / 2)
        if "error" in channel_info:
            return channel_info

        # 调用服务
        result = await self.call_service(channel_info, method, params, timeout=timeout / 2)

        # 关闭通道
        await self.close_channel(service_id)

        return result

    # ==================== Key 管理 ====================

    async def request_key(self, service_id: str, purpose: str = "", timeout: float = 30.0) -> dict:
        """请求 API Key"""
        response = await self._send_request(
            "key_request",
            {"service_id": service_id, "purpose": purpose},
            timeout=timeout,
        )
        if response.get("success") and response.get("key"):
            self._stored_keys[service_id] = response["key"]
        return response

    def get_stored_key(self, service_id: str) -> Optional[str]:
        """获取存储的 Key"""
        return self._stored_keys.get(service_id)

    def store_key(self, service_id: str, key: str):
        """存储 Key"""
        self._stored_keys[service_id] = key

    # ==================== 上下文管理器 ====================

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
