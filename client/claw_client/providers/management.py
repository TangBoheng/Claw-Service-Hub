"""Management Only Client for Claw Service Hub.

纯管理型客户端，只管理服务，不执行业务请求。
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from ..base import BaseClient
from ..utils import serialize_message


class ManagementOnlyClient(BaseClient):
    """
    纯管理型客户端 - 用于 subagent1 场景

    与 ToolServiceClient 的区别：
    - 只管理服务注册和元数据
    - 不监听和处理业务请求
    - 服务请求转发到外部执行器（external endpoint）

    用法:
        client = ManagementOnlyClient(
            name="coco-image-service",
            description="提供 COCO 数据集图片访问服务",
            endpoint="http://localhost:8080",
            execution_mode="external"
        )
        async with client:
            # 服务已注册
            pass
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
        execution_mode: str = "external",
        interface_spec: dict = None,
    ):
        """
        初始化纯管理型客户端。

        Args:
            name: 服务名称
            description: 服务描述
            version: 服务版本
            endpoint: 外部执行器地址
            tags: 服务标签列表
            metadata: 服务元数据
            emoji: 服务图标 emoji
            requires: 依赖要求
            skill_dir: SKILL.md 所在目录
            hub_url: Hub 服务地址
            heartbeat_interval: 心跳间隔（秒）
            execution_mode: 执行模式 (external/remote)
            interface_spec: 接口规范
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
        self.execution_mode = execution_mode
        self.interface_spec = interface_spec or {}
        self.skill_dir = skill_dir
        self.skill_doc = self._load_skill_doc() if skill_dir else None

        # 运行时状态
        self.service_id: Optional[str] = None
        self.tunnel_id: Optional[str] = None

        # 回调
        self._callbacks: Dict[str, List[Callable]] = {
            "registered": [],
            "channel_request": [],
            "disconnected": [],
        }

    def _load_skill_doc(self) -> Optional[str]:
        """从 skill_dir 加载 SKILL.md 文件内容"""
        import os

        skill_md_path = os.path.join(self.skill_dir, "SKILL.md")
        if os.path.exists(skill_md_path):
            try:
                with open(skill_md_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[ManagementOnlyClient] Warning: Failed to load {skill_md_path}: {e}")
        return None

    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    async def _on_connected(self):
        """连接建立后的处理。"""
        # 发送注册消息
        register_msg = {
            "type": "register",
            "client_type": "management_only",
            "service": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "endpoint": self.endpoint,
                "tags": self.tags,
                "metadata": self.metadata,
                "emoji": self.emoji,
                "requires": self.requires,
                "execution_mode": self.execution_mode,
                "interface_spec": self.interface_spec,
            },
        }
        if self.skill_doc:
            register_msg["skill_doc"] = self.skill_doc

        await self.websocket.send(serialize_message(register_msg))
        print(f"[ManagementOnlyClient] Connecting to {self.url}...")

    async def _on_disconnected(self):
        """断开连接后的处理。"""
        await self._trigger_callback("disconnected")
        print("[ManagementOnlyClient] Disconnected")

    async def _handle_message(self, message: Dict[str, Any]):
        """处理特定类型的消息。"""
        msg_type = message.get("type")

        if msg_type == "registered":
            self.service_id = message.get("service_id")
            self.tunnel_id = message.get("tunnel_id")
            print(f"[ManagementOnlyClient] Registered! service_id={self.service_id}, tunnel_id={self.tunnel_id}")
            await self._trigger_callback("registered", message)

        elif msg_type == "channel_request":
            # 用户请求建立通道
            await self._trigger_callback("channel_request", message)

        elif msg_type == "request":
            await self._handle_request(message)

        elif msg_type == "ping":
            await self.websocket.send(serialize_message({"type": "pong"}))

    async def _handle_request(self, message: Dict[str, Any]):
        """处理远程调用请求。"""
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})

        print(f"[ManagementOnlyClient] Request received: {method}({params})")

        handler = self._request_handlers.get(method)
        if handler:
            try:
                result = await handler(**params) if asyncio.iscoroutinefunction(handler) else handler(**params)
                response = {"result": result}
            except Exception as e:
                print(f"[ManagementOnlyClient] Handler error: {e}")
                response = {"error": str(e)}
        else:
            response = {"error": f"Unknown method: {method}"}

        await self.websocket.send(serialize_message({
            "type": "response",
            "request_id": request_id,
            "response": response,
        }))

    async def _trigger_callback(self, event: str, data: Any = None):
        """触发事件回调"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                print(f"[ManagementOnlyClient] Callback error for {event}: {e}")

    async def update_service_info(self, **kwargs):
        """更新服务信息"""
        if not self.service_id:
            print("[ManagementOnlyClient] Not registered yet")
            return

        await self.websocket.send(serialize_message({
            "type": "update_service",
            "service_id": self.service_id,
            "info": kwargs,
        }))

    async def confirm_channel(self, request_id: str, accepted: bool = True, message: str = ""):
        """确认通道请求"""
        await self.websocket.send(serialize_message({
            "type": "channel_confirm",
            "request_id": request_id,
            "accepted": accepted,
            "message": message,
        }))
