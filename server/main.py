"""
服务撮合云端 - WebSocket 服务器
Phase 1: 服务注册、发现、隧道、评分
"""
print("[Server] Module loading...", flush=True)
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Set, Dict

import websockets
from websockets.asyncio.server import ServerConnection

# 本地模块 - 支持两种运行方式
# 1. python -m server.main (需要 PYTHONPATH 包含项目根目录)
# 2. python server/main.py (直接运行)
import sys
import os
if __name__ == "__main__":
    # 当直接运行 server/main.py 时，添加父目录到 path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from server.registry import ServiceRegistry, ToolService, get_registry
    from server.tunnel import TunnelManager, get_tunnel_manager
    from server.rating import RatingManager, get_rating_manager
    from server.key_manager import key_manager, KeyManager
except ImportError:
    # 备用: 直接导入 (当 PYTHONPATH 正确设置时)
    from registry import ServiceRegistry, ToolService, get_registry
    from tunnel import TunnelManager, get_tunnel_manager
    from rating import RatingManager, get_rating_manager
    from key_manager import key_manager, KeyManager


# 新增：导入管理客户端和通道管理
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'client'))


# 配置
HOST = "0.0.0.0"
PORT = 8765
HEARTBEAT_INTERVAL = 30  # 秒
CLEANUP_INTERVAL = 10  # 秒


class HubServer:
    """服务撮合云端服务器"""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.registry = get_registry()
        self.tunnel_mgr = get_tunnel_manager()
        self.rating_mgr = get_rating_manager()
        self.clients: Set[ServerConnection] = set()
        self.running = False

        # 注册隧道转发回调
        self._client_websockets: Dict[str, ServerConnection] = {}
        self._client_info: Dict[str, dict] = {}  # client_id -> {type, service_id}
        self._pending_channels: Dict[str, dict] = {}  # request_id -> channel_request
        self.tunnel_mgr.on("request", self._on_tunnel_request)
    
    async def start(self):
        """启动服务器（WebSocket + HTTP REST API）"""
        self.running = True

        # 启动后台任务
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._cleanup_loop())

        print(f"\n{'='*50}")
        print(f"🛠️  Tool Service Hub Started")
        print(f"{'='*50}")
        print(f"   WebSocket: ws://{self.host}:{self.port}")
        print(f"   REST API:  http://{self.host}:{self.port - 5000}")
        print(f"{'='*50}\n")

        # 启动 WebSocket 服务器
        ws_server = websockets.serve(self._handle_client, self.host, self.port)

        # 尝试启动 HTTP REST API（可选）
        try:
            from aiohttp import web

            app = web.Application()
            app.router.add_get("/api/services", self._handle_api_services)
            app.router.add_get("/api/services/{service_id}", self._handle_api_service_detail)
            app.router.add_get("/api/services/{service_id}/skill.md", self._handle_api_skill_doc)
            app.router.add_get("/api/tunnels", self._handle_api_tunnels)
            app.router.add_get("/api/services/{service_id}/ratings", self._handle_api_service_ratings)
            app.router.add_post("/api/ratings", self._handle_api_add_rating)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self.host, self.port - 5000)
            await site.start()

            print(f"[Server] HTTP REST API started on http://{self.host}:{self.port - 5000}")
        except ImportError:
            print("[Server] aiohttp not installed, HTTP REST API disabled")
        except Exception as e:
            print(f"[Server] Failed to start HTTP REST API: {e}")

        async with ws_server:
            await asyncio.Future()  # 永远运行
    
    async def stop(self):
        """停止服务器"""
        self.running = False
        for client in self.clients:
            await client.close()
    
    async def _handle_client(self, websocket: ServerConnection):
        """处理客户端连接"""
        # 新的 websockets 库不再传递 path 参数
        path = ""
        client_id = str(uuid.uuid4())[:8]
        print(f"[Server] Client connected: {client_id}")
        
        self.clients.add(websocket)

        # 存储 client_id 到 websocket 的映射（用于隧道转发）
        self._client_websockets[client_id] = websocket

        try:
            async for message in websocket:
                await self._process_message(websocket, client_id, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[Server] Client disconnected: {client_id}")
        except Exception as e:
            print(f"[Server] Error: {e}")
        finally:
            self.clients.discard(websocket)
            # 清理 client_id 映射
            self._client_websockets.pop(client_id, None)
            # 清理该客户端的隧道
            tunnel = self.tunnel_mgr.get_tunnel_by_client(client_id)
            if tunnel:
                await self.tunnel_mgr.close_tunnel(tunnel.id)
    
    async def _process_message(
        self,
        websocket: ServerConnection,
        client_id: str, 
        raw_message: str
    ):
        """处理客户端消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            
            # 调试：打印所有消息类型
            if msg_type not in ["heartbeat", "ping"]:
                print(f"[Server] Received from {client_id}: type={msg_type}", flush=True)
            
            if msg_type == "register":
                # 注册服务
                await self._handle_register(websocket, client_id, message)
            
            elif msg_type == "heartbeat":
                # 心跳
                await self._handle_heartbeat(client_id, message)
            
            elif msg_type == "request":
                # 转发请求响应
                await self._handle_request_response(client_id, message)
            
            elif msg_type == "response":
                # 处理 Provider 返回的响应
                await self._handle_response(message)
            
            elif msg_type == "call_service":
                # 转发请求到目标服务
                await self._handle_call_service(message)

            elif msg_type == "connect":
                # 消费者客户端连接（subagent2）
                await self._handle_connect(websocket, client_id, message)

            elif msg_type == "skill_discover":
                # Skill 方式查询服务
                await self._handle_skill_discover(websocket, client_id, message)

            elif msg_type == "get_service_docs":
                # 获取服务文档
                await self._handle_get_service_docs(websocket, client_id, message)

            elif msg_type == "get_skill_doc":
                # 获取 SKILL.md
                await self._handle_get_skill_doc(websocket, client_id, message)

            elif msg_type == "establish_channel":
                # 建立服务通道
                await self._handle_establish_channel(websocket, client_id, message)

            elif msg_type == "channel_confirm":
                # 服务提供者确认通道
                await self._handle_channel_confirm(websocket, client_id, message)

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
            
            # === Key 授权相关 ===
            elif msg_type == "lifecycle_policy":
                # Provider 注册生命周期策略
                await self._handle_lifecycle_policy(client_id, message)
            
            elif msg_type == "key_request":
                # Consumer 请求 Key
                await self._handle_key_request(websocket, client_id, message)
            
            elif msg_type == "key_response":
                # Provider 返回 Key（批准/拒绝）
                await self._handle_key_response(websocket, client_id, message)
            
            elif msg_type == "key_revoke":
                # Provider 撤销 Key
                await self._handle_key_revoke(client_id, message)
            
            elif msg_type == "key_list":
                # 查询 Key 列表
                await self._handle_key_list(websocket, client_id, message)
            
            else:
                print(f"[Server] Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            print(f"[Server] Invalid JSON: {raw_message[:100]}")
        except Exception as e:
            print(f"[Server] Error processing message: {e}")
    
    async def _handle_register(
        self,
        websocket: ServerConnection,
        client_id: str,
        message: dict
    ):
        """处理服务注册"""
        service_data = message.get("service", {})
        skill_doc = message.get("skill_doc")  # 获取 skill.md 内容

        service = ToolService(
            id=service_data.get("id", ""),
            name=service_data.get("name", "Unknown"),
            description=service_data.get("description", ""),
            version=service_data.get("version", "1.0.0"),
            endpoint=service_data.get("endpoint", ""),
            tags=service_data.get("tags", []),
            metadata=service_data.get("metadata", {}),
            emoji=service_data.get("emoji", "🔧"),
            requires=service_data.get("requires", {}),
            execution_mode=service_data.get("execution_mode", "local"),
            interface_spec=service_data.get("interface_spec", {})
        )

        # 设置提供者信息
        service.provider_client_id = client_id
        client_type = message.get("client_type", "full")  # "management_only" | "full"

        # 注册到服务注册表（包含 skill_doc）
        service_id = await self.registry.register(service, skill_doc)

        # 创建隧道
        tunnel = await self.tunnel_mgr.create_tunnel(service_id, client_id)
        service.tunnel_id = tunnel.id

        # 更新注册表中的服务
        service.id = service_id
        self.registry._services[service_id] = service

        # 响应客户端
        await websocket.send(json.dumps({
            "type": "registered",
            "service_id": service_id,
            "tunnel_id": tunnel.id,
            "status": "online"
        }))

        print(f"[Server] Service registered: {service.name} -> tunnel {tunnel.id}")
        print(f"[Server]   Execution mode: {service.execution_mode}, Client type: {client_type}")

    async def _handle_connect(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理消费者客户端连接"""
        client_type = message.get("client_type", "consumer")
        self._client_info[client_id] = {
            "type": client_type,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }

        await websocket.send(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "client_type": client_type
        }))

        print(f"[Server] Consumer connected: {client_id} ({client_type})")

    async def _handle_skill_discover(
        self,
        websocket: ServerConnection,
        client_id: str,
        message: dict
    ):
        """处理 skill 方式服务发现"""
        request_id = message.get("request_id")
        query = message.get("query", "")
        tags = message.get("tags", [])
        execution_mode = message.get("execution_mode")
        status = message.get("status", "online")

        # 查找服务
        services = self.registry.find(
            name=query,
            tags=tags if tags else None,
            status=status,
            execution_mode=execution_mode
        )

        # 转换为 skill 描述符
        skill_list = [s.to_skill_descriptor() for s in services]

        await websocket.send(json.dumps({
            "type": "skill_list",
            "request_id": request_id,
            "skills": skill_list,
            "total": len(skill_list)
        }))

        print(f"[Server] Skill discover from {client_id}: found {len(skill_list)} services")

    async def _handle_get_service_docs(
        self,
        websocket: ServerConnection,
        client_id: str,
        message: dict
    ):
        """处理获取服务文档请求"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")

        service = self.registry.get(service_id)

        if service:
            response = {
                "type": "service_docs",
                "request_id": request_id,
                "service_id": service_id,
                "name": service.name,
                "description": service.description,
                "documentation": service.description,  # 可扩展完整文档
                "interface_spec": service.interface_spec,
                "endpoint": service.endpoint,
                "execution_mode": service.execution_mode,
                "tags": service.tags
            }
        else:
            response = {
                "type": "error",
                "request_id": request_id,
                "message": f"Service not found: {service_id}"
            }

        await websocket.send(json.dumps(response))

    async def _handle_get_skill_doc(
        self,
        websocket: ServerConnection,
        client_id: str,
        message: dict
    ):
        """处理获取 SKILL.md 请求"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")

        skill_doc = self.registry.get_skill_doc(service_id)

        if skill_doc:
            response = {
                "type": "skill_doc",
                "request_id": request_id,
                "service_id": service_id,
                "skill_doc": skill_doc
            }
        else:
            response = {
                "type": "error",
                "request_id": request_id,
                "message": f"Skill doc not found for service: {service_id}"
            }

        await websocket.send(json.dumps(response))

    async def _handle_establish_channel(
        self,
        websocket: ServerConnection,
        client_id: str,
        message: dict
    ):
        """处理建立通道请求"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        consumer_client_id = client_id  # 使用实际的 WebSocket client_id，而不是消息中的

        service = self.registry.get(service_id)

        if not service:
            await websocket.send(json.dumps({
                "type": "error",
                "request_id": request_id,
                "message": f"Service not found: {service_id}"
            }))
            return

        # 检查服务是否在线
        if service.status != "online":
            await websocket.send(json.dumps({
                "type": "error",
                "request_id": request_id,
                "message": f"Service is offline: {service_id}"
            }))
            return

        # 对于管理型服务，需要通知提供者确认
        if service.execution_mode == "external" and service.provider_client_id:
            # 存储待确认的通道请求
            channel_request_id = str(uuid.uuid4())[:12]
            self._pending_channels[channel_request_id] = {
                "request_id": request_id,
                "service_id": service_id,
                "consumer_client_id": consumer_client_id,
                "provider_client_id": service.provider_client_id,
                "tunnel_id": service.tunnel_id
            }

            # 通知提供者
            provider_ws = self._client_websockets.get(service.provider_client_id)
            if provider_ws:
                await provider_ws.send(json.dumps({
                    "type": "channel_request",
                    "request_id": channel_request_id,
                    "service_id": service_id,
                    "user_client_id": consumer_client_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))

            print(f"[Server] Channel request {channel_request_id} sent to provider {service.provider_client_id}")

        else:
            # 本地执行模式，直接建立通道
            await websocket.send(json.dumps({
                "type": "channel_established",
                "request_id": request_id,
                "service_id": service_id,
                "channel_id": service.tunnel_id,
                "tunnel_id": service.tunnel_id,
                "execution_mode": service.execution_mode,
                "endpoint": service.endpoint
            }))

            print(f"[Server] Channel established for {service_id} (local mode)")

    async def _handle_channel_confirm(
        self,
        websocket: ServerConnection,
        client_id: str,
        message: dict
    ):
        """处理服务提供者通道确认"""
        request_id = message.get("request_id")  # channel_request_id
        accepted = message.get("accepted", False)
        service_id = message.get("service_id")
        tunnel_id = message.get("tunnel_id")

        print(f"[Server] Channel confirm received: request_id={request_id}, accepted={accepted}", flush=True)
        print(f"[Server] Pending channels: {list(self._pending_channels.keys())}", flush=True)

        # 查找对应的消费者请求
        channel_req = self._pending_channels.pop(request_id, None)

        if not channel_req:
            print(f"[Server] ❌ Channel request {request_id} not found or expired", flush=True)
            return

        print(f"[Server] Found channel_req: {channel_req}", flush=True)

        consumer_ws = self._client_websockets.get(channel_req["consumer_client_id"])
        print(f"[Server] Consumer websocket: {consumer_ws is not None}", flush=True)

        if accepted:
            # 通道建立成功
            if consumer_ws:
                await consumer_ws.send(json.dumps({
                    "type": "channel_established",
                    "request_id": channel_req["request_id"],
                    "service_id": service_id,
                    "channel_id": request_id,
                    "tunnel_id": tunnel_id,
                    "execution_mode": "external"
                }))

            print(f"[Server] Channel {request_id} established (external mode)")
        else:
            # 通道被拒绝
            if consumer_ws:
                await consumer_ws.send(json.dumps({
                    "type": "error",
                    "request_id": channel_req["request_id"],
                    "message": "Channel request rejected by service provider"
                }))

            print(f"[Server] Channel {request_id} rejected")
    
    async def _handle_heartbeat(self, client_id: str, message: dict):
        """处理心跳"""
        service_id = message.get("service_id")
        if service_id:
            await self.registry.heartbeat(service_id)
            
            # 更新隧道活跃时间
            tunnel = self.tunnel_mgr.get_tunnel_by_client(client_id)
            if tunnel:
                await self.tunnel_mgr.update_activity(tunnel.id)
    
    async def _on_tunnel_request(self, client_id: str, message: dict):
        """隧道请求回调 - 将请求转发到对应客户端"""
        websocket = self._client_websockets.get(client_id)
        if websocket:
            try:
                await websocket.send(json.dumps(message))
            except Exception as e:
                print(f"[Server] Failed to forward request to {client_id}: {e}")
        else:
            print(f"[Server] Client {client_id} not found for forwarding")

    async def _handle_call_service(self, message: dict):
        """处理服务调用请求，转发到目标客户端"""
        tunnel_id = message.get("tunnel_id")
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})

        if not tunnel_id or not request_id:
            print(f"[Server] Invalid call_service message: {message}")
            return

        # 通过 tunnel manager 转发请求
        success = await self.tunnel_mgr.forward_request(
            tunnel_id=tunnel_id,
            request_id=request_id,
            method=method,
            params=params
        )

        if not success:
            print(f"[Server] Failed to forward request to tunnel {tunnel_id}")

    async def _handle_request_response(
        self,
        client_id: str,
        message: dict
    ):
        """处理节点的请求响应"""
        request_id = message.get("request_id")
        if request_id:
            await self.tunnel_mgr.handle_response(request_id, message.get("response", {}))

    async def _handle_response(self, message: dict):
        """处理 Provider 返回的 response 消息"""
        request_id = message.get("request_id")
        if request_id:
            # 查找对应的消费者 websocket
            # 需要从 pending_channels 或其他地方找到 consumer_client_id
            # 暂时遍历所有客户端找到匹配的 request_id
            response_data = message.get("response", {})
            
            # 通过 tunnel manager 找到对应的 consumer 并发送响应
            await self.tunnel_mgr.handle_response(request_id, response_data)
            
            # 发送 service_response 消息给 Consumer
            for client_id, websocket in self._client_websockets.items():
                try:
                    await websocket.send(json.dumps({
                        "type": "service_response",
                        "request_id": request_id,
                        "response": response_data
                    }))
                except Exception:
                    pass
            
            print(f"[Server] Response forwarded for request {request_id}")

    async def _heartbeat_loop(self):
        """心跳检查循环"""
        while self.running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await self._broadcast_service_list()
    
    async def _cleanup_loop(self):
        """清理过期服务"""
        while self.running:
            await asyncio.sleep(CLEANUP_INTERVAL)
            await self.registry.cleanup_stale()
    
    async def _broadcast_service_list(self):
        """广播服务列表给所有客户端 - 仅发送轻量级 metadata"""
        # 使用轻量级 metadata 进行广播
        service_list = self.registry.list_all_metadata()

        message = json.dumps({
            "type": "metadata_list",  # 更名为 metadata_list 以区分完整服务列表
            "services": service_list,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # 广播给所有客户端
        if self.clients:
            await asyncio.gather(
                *[c.send(message) for c in self.clients],
                return_exceptions=True
            )


    async def _handle_api_services(self, request):
        """GET /api/services - 列出所有服务"""
        from aiohttp import web
        services = self.registry.list_all()
        return web.json_response([
            s.to_metadata_dict() for s in services
        ])

    async def _handle_api_service_detail(self, request):
        """GET /api/services/{service_id} - 获取服务详情"""
        from aiohttp import web
        service_id = request.match_info.get("service_id")
        service = self.registry.get(service_id)
        if service:
            return web.json_response(service.to_dict())
        return web.json_response({"error": "Service not found"}, status=404)

    async def _handle_api_skill_doc(self, request):
        """GET /api/services/{service_id}/skill.md - 获取技能文档"""
        from aiohttp import web
        service_id = request.match_info.get("service_id")
        skill_doc = self.registry.get_skill_doc(service_id)
        if skill_doc:
            return web.Response(text=skill_doc, content_type="text/markdown")
        return web.json_response({"error": "Skill doc not found"}, status=404)

    async def _handle_api_tunnels(self, request):
        """GET /api/tunnels - 列出所有隧道"""
        from aiohttp import web
        tunnels = self.tunnel_mgr.list_tunnels()
        return web.json_response([t.to_dict() for t in tunnels])

    async def _handle_api_service_ratings(self, request):
        """GET /api/services/{service_id}/ratings - 获取服务评分"""
        from aiohttp import web
        service_id = request.match_info.get("service_id")
        stats = self.rating_mgr.get_stats(service_id)
        return web.json_response(stats)

    async def _handle_api_add_rating(self, request):
        """POST /api/ratings - 添加评分"""
        from aiohttp import web
        data = await request.json()
        rating = await self.rating_mgr.add_rating(
            service_id=data.get("service_id"),
            score=data.get("score"),
            comment=data.get("comment", ""),
            tags=data.get("tags", [])
        )
        return web.json_response(rating.to_dict())



    # ========== Key 授权处理函数 ==========
    
    async def _handle_lifecycle_policy(self, client_id: str, message: dict):
        """处理 Provider 注册生命周期策略"""
        service_id = message.get("service_id")
        policy = message.get("policy", {})
        
        if not service_id:
            print(f"[Server] lifecycle_policy: 缺少 service_id")
            return
        
        # 注册策略
        key_manager.register_policy(service_id, policy)
        
        print(f"[Server] 注册生命周期策略: {service_id}, {policy}")
    
    async def _handle_key_request(self, websocket, client_id: str, message: dict):
        """处理 Consumer 请求 Key"""
        service_id = message.get("service_id")
        purpose = message.get("purpose", "")
        
        if not service_id:
            await websocket.send(json.dumps({
                "type": "key_request_response",
                "success": False,
                "reason": "缺少 service_id"
            }))
            return
        
        # 查找服务提供者
        service = self.registry.get_service(service_id)
        if not service:
            await websocket.send(json.dumps({
                "type": "key_request_response",
                "success": False,
                "reason": "服务不存在"
            }))
            return
        
        # 转发请求给 Provider
        provider_client_id = service.client_id
        provider_ws = self._client_websockets.get(provider_client_id)
        
        if not provider_ws:
            await websocket.send(json.dumps({
                "type": "key_request_response",
                "success": False,
                "reason": "服务提供者离线"
            }))
            return
        
        # 构造转发请求
        forward_msg = {
            "type": "key_request",
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "service_id": service_id,
            "consumer_id": client_id,
            "purpose": purpose,
            "service_name": service.name
        }
        
        await provider_ws.send(json.dumps(forward_msg))
        print(f"[Server] 转发 Key 请求: {client_id} -> {provider_client_id}")
    
    async def _handle_key_response(self, websocket, client_id: str, message: dict):
        """处理 Provider 返回 Key（批准/拒绝）"""
        request_id = message.get("request_id")
        approved = message.get("approved", False)
        
        if not approved:
            # 拒绝 - 通知 Consumer
            for ws in self._client_websockets.values():
                try:
                    await ws.send(json.dumps({
                        "type": "key_request_response",
                        "request_id": request_id,
                        "success": False,
                        "reason": message.get("reason", "Provider 拒绝")
                    }))
                except:
                    pass
            return
        
        # 批准 - 生成 Key 并存储
        service_id = message.get("service_id")
        consumer_id = message.get("consumer_id")
        lifecycle = message.get("lifecycle", {})
        
        # 生成 Key
        key = key_manager.generate_key(
            service_id=service_id,
            consumer_id=consumer_id,
            duration_seconds=lifecycle.get("duration_seconds"),
            max_calls=lifecycle.get("max_calls")
        )
        
        key_info = key_manager.get_key_info(key)
        
        # 通知 Consumer
        for ws in self._client_websockets.values():
            try:
                await ws.send(json.dumps({
                    "type": "key_request_response",
                    "request_id": request_id,
                    "success": True,
                    "key": key,
                    "lifecycle": key_info
                }))
            except:
                pass
        
        print(f"[Server] Key 已生成: {key[:12]}... 服务:{service_id} 消费者:{consumer_id}")
    
    async def _handle_key_revoke(self, client_id: str, message: dict):
        """处理撤销 Key"""
        key = message.get("key")
        if key:
            key_manager.revoke_key(key)
            print(f"[Server] Key 已撤销: {key[:12]}...")
    
    async def _handle_key_list(self, websocket, client_id: str, message: dict):
        """处理查询 Key 列表"""
        service_id = message.get("service_id")
        
        keys = key_manager.list_keys(service_id=service_id, active_only=True)
        
        await websocket.send(json.dumps({
            "type": "key_list_response",
            "keys": keys
        }))
    
    def _verify_key_for_call(self, service_id: str, key: str = None) -> dict:
        """验证 Key（用于 call_service 前）"""
        if not key:
            return {"valid": False, "reason": "需要 Key"}
        
        return key_manager.verify_key(key, service_id)


def main():
    """入口"""
    server = HubServer()
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        asyncio.run(server.stop())


if __name__ == "__main__":
    main()