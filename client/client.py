"""
服务节点客户端
运行在 OpenClaw 节点上，连接到云端并注册服务
"""
import asyncio
import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Callable

import websockets
from websockets.client import WebSocketClientProtocol


class ToolServiceClient:
    """
    工具服务客户端
    
    用法:
        client = ToolServiceClient(
            name="my-data-processor",
            description="处理本地CSV数据",
            endpoint="http://localhost:8080"
        )
        await client.connect("ws://cloud.example.com:8765")
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
        heartbeat_interval: int = 15
    ):
        self.name = name
        self.description = description
        self.version = version
        self.endpoint = endpoint
        self.tags = tags or []
        self.metadata = metadata or {}
        self.emoji = emoji
        self.requires = requires or {}
        self.hub_url = hub_url
        self.heartbeat_interval = heartbeat_interval
        self.skill_dir = skill_dir
        self.skill_doc = self._load_skill_doc() if skill_dir else None

        # 运行时状态
        self.service_id: Optional[str] = None
        self.tunnel_id: Optional[str] = None
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.client_id = str(uuid.uuid4())[:8]

        # 处理器
        self._request_handlers: Dict[str, Callable] = {}
        self._response_futures: Dict[str, asyncio.Future] = {}
    
    def _load_skill_doc(self) -> Optional[str]:
        """从 skill_dir 加载 SKILL.md 文件内容"""
        if not self.skill_dir:
            return None
        skill_md_path = os.path.join(self.skill_dir, "SKILL.md")
        if os.path.exists(skill_md_path):
            try:
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"[Client] Warning: Failed to load {skill_md_path}: {e}")
                return None
        return None

    def register_handler(self, method: str, handler: Callable):
        """注册请求处理器"""
        self._request_handlers[method] = handler
    
    async def connect(self):
        """连接到云端并注册服务"""
        print(f"[Client] Connecting to {self.hub_url}...")
        
        self.websocket = await websockets.connect(
            self.hub_url,
            ping_interval=None  # 我们自己发送心跳
        )
        
        self.running = True
        
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
                "requires": self.requires
            }
        }
        # 如果有 skill.md，一并发送
        if self.skill_doc:
            register_msg["skill_doc"] = self.skill_doc

        await self.websocket.send(json.dumps(register_msg))
        
        # 启动后台任务
        asyncio.create_task(self._receive_loop())
        asyncio.create_task(self._heartbeat_loop())
        
        print(f"[Client] Connected and registered as: {self.name}")
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        print(f"[Client] Disconnected")
    
    async def _receive_loop(self):
        """接收并处理云端消息"""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[Client] Connection closed")
            self.running = False
        except Exception as e:
            print(f"[Client] Receive error: {e}")
    
    async def _process_message(self, raw_message: str):
        """处理接收到的消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            
            if msg_type == "registered":
                # 注册确认
                self.service_id = message.get("service_id")
                self.tunnel_id = message.get("tunnel_id")
                print(f"[Client] Registered! service_id={self.service_id}, tunnel_id={self.tunnel_id}")
                
                # 注册确认后，发送生命周期策略
                if hasattr(self, 'lifecycle_policy') and self.lifecycle_policy:
                    policy_msg = {
                        "type": "lifecycle_policy",
                        "service_id": self.service_id,
                        "policy": self.lifecycle_policy
                    }
                    if hasattr(self, 'custom_policies') and self.custom_policies:
                        policy_msg["policy"]["custom_policies"] = self.custom_policies
                    await self.websocket.send(json.dumps(policy_msg))
                    print(f"[Client] 发送生命周期策略: {self.lifecycle_policy}")
            
            elif msg_type == "service_list":
                # 服务列表更新（向后兼容）
                services = message.get("services", [])
                print(f"[Client] Service list updated: {len(services)} services")

            elif msg_type == "metadata_list":
                # 轻量级 metadata 列表更新
                services = message.get("services", [])
                print(f"[Client] Metadata list updated: {len(services)} services")
            
            elif msg_type == "request":
                # 云端发来的请求
                await self._handle_request(message)
            
            elif msg_type == "response":
                # 响应消息 - 唤醒等待中的 call_remote_service
                request_id = message.get("request_id")
                response_data = message.get("response", {})
                if request_id and request_id in self._response_futures:
                    future = self._response_futures.pop(request_id)
                    if not future.done():
                        future.set_result(response_data)

            elif msg_type == "ping":
                await self.websocket.send(json.dumps({"type": "pong"}))
            
            elif msg_type == "key_request":
                # Consumer 请求 Key
                await self._handle_key_request(message)
            
            elif msg_type == "service_response":
                # 服务响应 - 唤醒等待的请求
                request_id = message.get("request_id")
                response_data = message.get("response", {})
                if request_id and request_id in self._response_futures:
                    future = self._response_futures.pop(request_id)
                    if not future.done():
                        future.set_result(response_data)
            
            else:
                print(f"[Client] Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            print(f"[Client] Invalid JSON: {raw_message[:100]}")
        except Exception as e:
            print(f"[Client] Error processing message: {e}")
    
    async def _handle_request(self, message: dict):
        """处理云端发来的请求"""
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})
        
        print(f"[Client] Request: {method}({params})")
        
        # 调用注册的处理器
        handler = self._request_handlers.get(method)
        
        if handler:
            try:
                result = await handler(**params)
                response = {"result": result}
            except Exception as e:
                response = {"error": str(e)}
        else:
            response = {"error": f"Unknown method: {method}"}
        
        # 发送响应
        await self.websocket.send(json.dumps({
            "type": "response",
            "request_id": request_id,
            "response": response
        }))
    
    async def _handle_key_request(self, message: dict):
        """处理 Key 请求"""
        request_id = message.get("request_id")
        consumer_id = message.get("consumer_id")
        service_id = message.get("service_id")
        purpose = message.get("purpose", "")
        
        print(f"[Client] Key request from {consumer_id}: {purpose}")
        
        # 获取生命周期策略
        policy = getattr(self, 'lifecycle_policy', None)
        if not policy:
            policy = {"duration_seconds": 3600, "max_calls": 100}
        
        # 批准请求，返回生命周期信息
        response = {
            "type": "key_response",
            "request_id": request_id,
            "approved": True,
            "consumer_id": consumer_id,
            "service_id": service_id,
            "lifecycle": {
                "duration_seconds": policy.get("duration_seconds", 3600),
                "max_calls": policy.get("max_calls", 100)
            },
            "reason": "Approved"
        }
        
        await self.websocket.send(json.dumps(response))
        print(f"[Client] Key request approved for {consumer_id}")
    
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
                    print(f"[Client] Heartbeat error: {e}")
                    self.running = False
                    break
    
    async def call_remote_service(
        self, 
        tunnel_id: str, 
        method: str, 
        params: dict,
        timeout: float = 30.0
    ) -> dict:
        """
        调用远程服务 (通过云端代理)
        
        注意：这是客户端调用其他服务的功能
        云端需要实现对应的转发逻辑
        """
        request_id = str(uuid.uuid4())[:12]
        
        # 创建 future 等待响应
        future = asyncio.Future()
        self._response_futures[request_id] = future
        
        # 发送请求 (云端需要实现转发)
        await self.websocket.send(json.dumps({
            "type": "call_service",
            "tunnel_id": tunnel_id,
            "request_id": request_id,
            "method": method,
            "params": params
        }))
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._response_futures.pop(request_id, None)
            return {"error": "Request timeout"}
        except Exception as e:
            self._response_futures.pop(request_id, None)
            return {"error": str(e)}


class LocalServiceRunner:
    """
    本地服务运行器 - 用于快速启动一个工具服务
    
    示例:
        async def handle_process_data(**params):
            # 处理数据
            return {"result": "processed", "count": 10}
        
        runner = LocalServiceRunner(
            name="csv-processor",
            description="处理CSV文件",
            endpoint="http://localhost:8080"
        )
        runner.register_handler("process_data", handle_process_data)
        
        await runner.run("ws://localhost:8765")
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
        hub_url: str = "ws://localhost:8765"
    ):
        self.client = ToolServiceClient(
            name=name,
            description=description,
            version=version,
            endpoint=endpoint,
            tags=tags,
            metadata=metadata,
            emoji=emoji,
            requires=requires,
            skill_dir=skill_dir,
            hub_url=hub_url
        )
        # 生命周期策略
        self.lifecycle_policy = None
        self.custom_policies = {}
    
    def set_lifecycle_policy(self, duration_seconds: int = 3600, max_calls: int = 100):
        """设置默认生命周期策略"""
        self.lifecycle_policy = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls
        }
        # 传递给 client
        self.client.lifecycle_policy = self.lifecycle_policy
        self.client.custom_policies = self.custom_policies
    
    def set_custom_policy(self, condition: str, duration_seconds: int, max_calls: int):
        """设置自定义策略"""
        if not hasattr(self, 'custom_policies'):
            self.custom_policies = {}
        self.custom_policies[condition] = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls
        }
        if hasattr(self.client, 'custom_policies'):
            self.client.custom_policies = self.custom_policies
    
    def register_handler(self, method: str, handler: Callable):
        """注册方法处理器"""
        self.client.register_handler(method, handler)
    
    def set_lifecycle_policy(self, duration_seconds: int = 3600, max_calls: int = 100):
        """
        设置默认生命周期策略
        
        Args:
            duration_seconds: 有效时长（秒），默认1小时
            max_calls: 最大调用次数，默认100次
        """
        self.lifecycle_policy = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls
        }
        # 传递给底层 client
        if hasattr(self, 'client'):
            self.client.lifecycle_policy = self.lifecycle_policy
    
    def set_custom_policy(self, condition: str, duration_seconds: int, max_calls: int):
        """
        设置自定义策略
        
        Args:
            condition: 策略名称（如 "premium", "basic"）
            duration_seconds: 有效时长
            max_calls: 最大调用次数
        """
        if not hasattr(self, 'custom_policies'):
            self.custom_policies = {}
        self.custom_policies[condition] = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls
        }
    
    async def run(self):
        """启动服务并连接云端"""
        await self.client.connect()
        
        # 保持运行
        while self.client.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """停止服务"""
        await self.client.disconnect()


# 便捷函数
async def run_service(
    name: str,
    description: str,
    handlers: Dict[str, Callable],
    hub_url: str = "ws://localhost:8765",
    **kwargs
):
    """快速启动一个工具服务"""
    runner = LocalServiceRunner(
        name=name,
        description=description,
        hub_url=hub_url,
        **kwargs
    )
    
    for method, handler in handlers.items():
        runner.register_handler(method, handler)
    
    await runner.run()