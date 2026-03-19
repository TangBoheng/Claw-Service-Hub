"""
纯管理型客户端 - 只管理服务，不执行业务

用于 subagent1 场景：
- 注册数据服务到撮合系统
- 管理服务的生命周期（注册、更新、注销）
- 不处理业务请求，请求转发到外部执行器（如 n8n、python 服务）
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable

import websockets
from websockets.client import WebSocketClientProtocol


class ManagementOnlyClient:
    """
    纯管理型客户端

    与 ToolServiceClient 的区别：
    - 只管理服务注册和元数据
    - 不监听和处理业务请求
    - 服务请求转发到外部执行器（external endpoint）

    用法:
        client = ManagementOnlyClient(
            name="coco-image-service",
            description="提供COCO数据集图片访问服务",
            endpoint="http://localhost:8080",  # 外部执行器地址
            execution_mode="external"
        )
        await client.connect("ws://localhost:8765")
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        endpoint: str = "",  # 外部执行器地址
        tags: List[str] = None,
        metadata: dict = None,
        emoji: str = "🔧",
        requires: dict = None,
        skill_dir: str = None,
        hub_url: str = "ws://localhost:8765",
        heartbeat_interval: int = 15,
        execution_mode: str = "external",  # "external" | "remote"
        interface_spec: dict = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.endpoint = endpoint  # 外部执行器地址
        self.tags = tags or []
        self.metadata = metadata or {}
        self.emoji = emoji
        self.requires = requires or {}
        self.hub_url = hub_url
        self.heartbeat_interval = heartbeat_interval
        self.execution_mode = execution_mode
        self.interface_spec = interface_spec or {}
        self.skill_dir = skill_dir
        self.skill_doc = self._load_skill_doc() if skill_dir else None

        # 运行时状态
        self.service_id: Optional[str] = None
        self.tunnel_id: Optional[str] = None
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.client_id = str(uuid.uuid4())[:8]

        # 回调
        self._callbacks: Dict[str, List[Callable]] = {
            "registered": [],
            "channel_request": [],  # 用户请求建立通道
            "disconnected": [],
        }

        # 请求处理器 (method_name -> handler)
        self._request_handlers: Dict[str, Callable] = {}

    def _load_skill_doc(self) -> Optional[str]:
        """从 skill_dir 加载 SKILL.md 文件内容"""
        if not self.skill_dir:
            return None
        import os
        skill_md_path = os.path.join(self.skill_dir, "SKILL.md")
        if os.path.exists(skill_md_path):
            try:
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"[ManagementClient] Warning: Failed to load {skill_md_path}: {e}")
                return None
        return None

    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def register_handler(self, method: str, handler: Callable):
        """注册请求处理器

        用于处理消费者通过 call_service 发送的请求。
        handler 应该是 async 函数，接收 **params 参数，返回 dict。

        示例:
            async def list_images(limit: int = 10):
                return {"images": [...], "total": 100}

            client.register_handler("list_images", list_images)
        """
        self._request_handlers[method] = handler
        print(f"[ManagementClient] Handler registered for method: {method}")

    async def _handle_request(self, message: dict):
        """处理远程调用请求"""
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})

        print(f"[ManagementClient] Request received: {method}({params})")

        handler = self._request_handlers.get(method)

        if handler:
            try:
                result = await handler(**params)
                response = {"result": result}
            except Exception as e:
                print(f"[ManagementClient] Handler error: {e}")
                response = {"error": str(e)}
        else:
            response = {"error": f"Unknown method: {method}"}

        # 发送响应
        await self.websocket.send(json.dumps({
            "type": "response",
            "request_id": request_id,
            "response": response
        }))
        print(f"[ManagementClient] Response sent for {method}")

    async def connect(self):
        """连接到云端并注册服务"""
        print(f"[ManagementClient] Connecting to {self.hub_url}...")

        self.websocket = await websockets.connect(
            self.hub_url,
            ping_interval=None
        )

        self.running = True

        # 发送注册消息（管理型服务）
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
                "execution_mode": self.execution_mode,
                "interface_spec": self.interface_spec
            },
            "client_type": "management_only",  # 标识为纯管理型客户端
            "client_id": self.client_id
        }

        if self.skill_doc:
            register_msg["skill_doc"] = self.skill_doc

        await self.websocket.send(json.dumps(register_msg))

        # 启动后台任务
        asyncio.create_task(self._receive_loop())
        asyncio.create_task(self._heartbeat_loop())

        print(f"[ManagementClient] Connected and registered as: {self.name}")
        print(f"[ManagementClient] Execution mode: {self.execution_mode}")
        print(f"[ManagementClient] External endpoint: {self.endpoint}")

    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        print(f"[ManagementClient] Disconnected")

    async def _receive_loop(self):
        """接收并处理云端消息"""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[ManagementClient] Connection closed")
            self.running = False
        except Exception as e:
            print(f"[ManagementClient] Receive error: {e}")

    async def _process_message(self, raw_message: str):
        """处理接收到的消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")

            if msg_type == "registered":
                # 注册确认
                self.service_id = message.get("service_id")
                self.tunnel_id = message.get("tunnel_id")
                print(f"[ManagementClient] Registered! service_id={self.service_id}, tunnel_id={self.tunnel_id}")

                # 触发回调
                for cb in self._callbacks["registered"]:
                    await cb(self.service_id, self.tunnel_id)

            elif msg_type == "channel_request":
                # 用户请求建立服务通道
                print(f"[ManagementClient] Channel request from user: {message.get('user_client_id')}")
                for cb in self._callbacks["channel_request"]:
                    await cb(message)

            elif msg_type == "request":
                # 处理远程调用请求 (external 模式)
                await self._handle_request(message)

            elif msg_type == "heartbeat_ack":
                # 心跳确认
                pass

            elif msg_type == "ping":
                await self.websocket.send(json.dumps({"type": "pong"}))

            else:
                print(f"[ManagementClient] Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            print(f"[ManagementClient] Invalid JSON: {raw_message[:100]}")
        except Exception as e:
            print(f"[ManagementClient] Error processing message: {e}")

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)
            if self.websocket and self.service_id:
                try:
                    await self.websocket.send(json.dumps({
                        "type": "heartbeat",
                        "service_id": self.service_id
                    }))
                except Exception as e:
                    print(f"[ManagementClient] Heartbeat error: {e}")
                    self.running = False
                    break

    async def update_service_info(self, **kwargs):
        """更新服务信息"""
        if not self.websocket:
            raise RuntimeError("Not connected")

        update_msg = {
            "type": "update_service",
            "service_id": self.service_id,
            "updates": kwargs
        }

        await self.websocket.send(json.dumps(update_msg))
        print(f"[ManagementClient] Service info updated: {kwargs.keys()}")

    async def confirm_channel(self, request_id: str, accepted: bool = True, message: str = ""):
        """确认或拒绝通道建立请求"""
        if not self.websocket:
            raise RuntimeError("Not connected")

        confirm_msg = {
            "type": "channel_confirm",
            "request_id": request_id,
            "accepted": accepted,
            "message": message,
            "service_id": self.service_id,
            "tunnel_id": self.tunnel_id
        }

        await self.websocket.send(json.dumps(confirm_msg))
        print(f"[ManagementClient] Channel {request_id} {'accepted' if accepted else 'rejected'}")


class ServiceRegistrar:
    """
    服务注册器 - 用于快速注册一个管理型服务

    示例:
        registrar = ServiceRegistrar(
            name="coco-image-service",
            description="COCO数据集图片服务",
            endpoint="http://localhost:8080"
        )
        await registrar.run("ws://localhost:8765")
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
        execution_mode: str = "external",
        interface_spec: dict = None,
    ):
        self.client = ManagementOnlyClient(
            name=name,
            description=description,
            version=version,
            endpoint=endpoint,
            tags=tags,
            metadata=metadata,
            emoji=emoji,
            requires=requires,
            skill_dir=skill_dir,
            hub_url=hub_url,
            execution_mode=execution_mode,
            interface_spec=interface_spec
        )

        # 默认自动接受通道请求
        self.client.on("channel_request", self._on_channel_request)

    def register_handler(self, method: str, handler: Callable):
        """注册请求处理器"""
        self.client.register_handler(method, handler)

    async def _on_channel_request(self, message: dict):
        """默认自动接受通道请求"""
        request_id = message.get("request_id")
        await self.client.confirm_channel(request_id, accepted=True)

    async def run(self):
        """启动服务注册"""
        await self.client.connect()

        # 保持运行
        while self.client.running:
            await asyncio.sleep(1)

    async def stop(self):
        """停止服务"""
        await self.client.disconnect()


# 便捷函数
async def register_service(
    name: str,
    description: str,
    endpoint: str,
    hub_url: str = "ws://localhost:8765",
    **kwargs
):
    """快速注册一个管理型服务"""
    registrar = ServiceRegistrar(
        name=name,
        description=description,
        endpoint=endpoint,
        hub_url=hub_url,
        **kwargs
    )
    await registrar.run()
