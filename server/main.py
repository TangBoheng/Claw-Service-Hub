"""
服务撮合云端 - WebSocket 服务器
Phase 1: 服务注册、发现、隧道、评分
"""
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
except ImportError:
    # 备用: 直接导入 (当 PYTHONPATH 正确设置时)
    from registry import ServiceRegistry, ToolService, get_registry
    from tunnel import TunnelManager, get_tunnel_manager
    from rating import RatingManager, get_rating_manager


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
            
            if msg_type == "register":
                # 注册服务
                await self._handle_register(websocket, client_id, message)
            
            elif msg_type == "heartbeat":
                # 心跳
                await self._handle_heartbeat(client_id, message)
            
            elif msg_type == "request":
                # 转发请求响应
                await self._handle_request_response(client_id, message)
            
            elif msg_type == "call_service":
                # 转发请求到目标服务
                await self._handle_call_service(message)

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
            
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
            requires=service_data.get("requires", {})
        )

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