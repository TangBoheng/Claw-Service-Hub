"""Tool Service Client for Claw Service Hub.

服务提供者客户端，用于发布和管理服务。
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from ..base import BaseClient
from ..utils import serialize_message


class ToolServiceClient(BaseClient):
    """
    工具服务客户端 - 运行在 OpenClaw 节点上，连接到云端并注册服务

    用法:
        client = ToolServiceClient(
            name="my-data-processor",
            description="处理本地 CSV 数据",
            endpoint="http://localhost:8080"
        )
        async with client:
            # 服务已注册并运行
            await asyncio.sleep(3600)
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        endpoint: str = "",
        tags: List[str] = None,
        metadata: dict = None,
        emoji: str = "🔧",
        requires: dict = None,
        skill_dir: str = None,
        hub_url: str = "ws://localhost:8765",
        heartbeat_interval: int = 15,
    ):
        """
        初始化工具服务客户端。

        Args:
            name: 服务名称
            description: 服务描述
            version: 服务版本
            endpoint: 服务端点 URL
            tags: 服务标签列表
            metadata: 服务元数据
            emoji: 服务图标 emoji
            requires: 依赖要求 (bins, env 等)
            skill_dir: SKILL.md 所在目录
            hub_url: Hub 服务地址
            heartbeat_interval: 心跳间隔（秒）
        """
        super().__init__(url=hub_url, heartbeat_interval=heartbeat_interval)

        # 服务信息
        self.name = name
        self.description = description
        self.version = version
        self.endpoint = endpoint
        self.tags = tags or []
        self.metadata = metadata or {}
        self.emoji = emoji
        self.requires = requires or {}
        self.skill_dir = skill_dir
        self.skill_doc = self._load_skill_doc() if skill_dir else None

        # 运行时状态
        self.service_id: Optional[str] = None
        self.tunnel_id: Optional[str] = None

        # 生命周期策略
        self.lifecycle_policy: Optional[Dict[str, Any]] = None
        self.custom_policies: Dict[str, Any] = {}

    def _load_skill_doc(self) -> Optional[str]:
        """从 skill_dir 加载 SKILL.md 文件内容"""
        skill_md_path = os.path.join(self.skill_dir, "SKILL.md")
        if os.path.exists(skill_md_path):
            try:
                with open(skill_md_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[ToolServiceClient] Warning: Failed to load {skill_md_path}: {e}")
        return None

    async def _on_connected(self):
        """连接建立后的处理。"""
        # 发送注册消息
        register_msg = {
            "type": "register",
            "service": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "endpoint": self.endpoint,
                "tags": self.tags,
                "metadata": self.metadata,
                "emoji": self.emoji,
                "requires": self.requires,
            },
        }
        if self.skill_doc:
            register_msg["skill_doc"] = self.skill_doc

        await self.websocket.send(serialize_message(register_msg))
        print(f"[ToolServiceClient] Connecting to {self.url}...")

    async def _on_disconnected(self):
        """断开连接后的处理。"""
        print(f"[ToolServiceClient] Disconnected, service_id={self.service_id}")

    async def _handle_message(self, message: Dict[str, Any]):
        """处理特定类型的消息。"""
        msg_type = message.get("type")

        if msg_type == "registered":
            self.service_id = message.get("service_id")
            self.tunnel_id = message.get("tunnel_id")
            print(f"[ToolServiceClient] Registered! service_id={self.service_id}, tunnel_id={self.tunnel_id}")

            # 发送生命周期策略
            if self.lifecycle_policy:
                policy_msg = {
                    "type": "lifecycle_policy",
                    "service_id": self.service_id,
                    "policy": self.lifecycle_policy,
                }
                if self.custom_policies:
                    policy_msg["policy"]["custom_policies"] = self.custom_policies
                await self.websocket.send(serialize_message(policy_msg))
                print(f"[ToolServiceClient] Lifecycle policy sent: {self.lifecycle_policy}")

        elif msg_type == "service_list":
            services = message.get("services", [])
            print(f"[ToolServiceClient] Service list updated: {len(services)} services")

        elif msg_type == "metadata_list":
            services = message.get("services", [])
            print(f"[ToolServiceClient] Metadata list updated: {len(services)} services")

        elif msg_type == "request":
            await self._handle_request(message)

        elif msg_type == "response" or msg_type == "service_response":
            request_id = message.get("request_id")
            response_data = message.get("response", {})
            if request_id and request_id in self._response_futures:
                future = self._response_futures.pop(request_id)
                if not future.done():
                    future.set_result(response_data)

        elif msg_type == "ping":
            await self.websocket.send(serialize_message({"type": "pong"}))

        elif msg_type == "key_request":
            await self._handle_key_request(message)

    async def _handle_request(self, message: Dict[str, Any]):
        """处理云端发来的请求。"""
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})

        print(f"[ToolServiceClient] Request: {method}({params})")

        handler = self._request_handlers.get(method)
        if handler:
            try:
                result = await handler(**params) if asyncio.iscoroutinefunction(handler) else handler(**params)
                response = {"result": result}
            except Exception as e:
                response = {"error": str(e)}
        else:
            response = {"error": f"Unknown method: {method}"}

        await self.websocket.send(serialize_message({
            "type": "response",
            "request_id": request_id,
            "response": response,
        }))

    async def _handle_key_request(self, message: Dict[str, Any]):
        """处理 Key 请求。"""
        request_id = message.get("request_id")
        consumer_id = message.get("consumer_id")
        service_id = message.get("service_id")
        purpose = message.get("purpose", "")

        print(f"[ToolServiceClient] Key request from {consumer_id}: {purpose}")

        policy = self.lifecycle_policy or {"duration_seconds": 3600, "max_calls": 100}

        await self.websocket.send(serialize_message({
            "type": "key_response",
            "request_id": request_id,
            "approved": True,
            "consumer_id": consumer_id,
            "service_id": service_id,
            "lifecycle": {
                "duration_seconds": policy.get("duration_seconds", 3600),
                "max_calls": policy.get("max_calls", 100),
            },
            "reason": "Approved",
        }))
        print(f"[ToolServiceClient] Key request approved for {consumer_id}")

    async def _send_heartbeat(self):
        """发送心跳消息。"""
        if self.websocket and self.websocket.open and self.service_id:
            await self.websocket.send(serialize_message({
                "type": "heartbeat",
                "service_id": self.service_id,
            }))

    def set_lifecycle_policy(self, duration_seconds: int = 3600, max_calls: int = 100):
        """设置默认生命周期策略。"""
        self.lifecycle_policy = {"duration_seconds": duration_seconds, "max_calls": max_calls}

    def set_custom_policy(self, condition: str, duration_seconds: int, max_calls: int):
        """设置自定义策略。"""
        self.custom_policies[condition] = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls,
        }

    async def call_remote_service(
        self,
        tunnel_id: str,
        method: str,
        params: dict,
        timeout: float = 30.0,
    ) -> dict:
        """调用远程服务。"""
        return await self._send_request(
            msg_type="call_service",
            payload={"tunnel_id": tunnel_id, "method": method, "params": params},
            timeout=timeout,
        )
