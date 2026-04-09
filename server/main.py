"""
服务撮合云端 - WebSocket 服务器
Phase 1: 服务注册、发现、隧道、评分
"""

print("[Server] Module loading...", flush=True)

import asyncio
import json
import os
# 本地模块 - 支持两种运行方式
# 1. python -m server.main (需要 PYTHONPATH 包含项目根目录)
# 2. python server/main.py (直接运行)
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Set

import websockets
from websockets.asyncio.server import ServerConnection

# 导入版本号
from server import __version__
# 配置日志
from server.utils.logging_config import configure_logging, logger

if __name__ == "__main__":
    # 当直接运行 server/main.py 时，添加父目录到 path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from server.auth.key_manager import KeyManager, key_manager
    from server.rating import RatingManager, get_rating_manager
    from server.core.registry import ServiceRegistry, ToolService, get_registry
    from server.core.tunnel import TunnelManager, get_tunnel_manager
    from server.auth.user_manager import UserManager, user_manager
    from server.chat.channel import ChatChannelManager, get_channel_manager
    from server.trade.listing import ListingManager, get_listing_manager
    from server.trade.bid import BidManager, get_bid_manager
    from server.trade.negotiation import NegotiationManager, get_negotiation_manager
    from server.trade.transaction import TransactionManager, get_transaction_manager
except ImportError:
    # 备用: 直接导入 (当 PYTHONPATH 正确设置时)
    from auth.key_manager import KeyManager, key_manager
    from rating import RatingManager, get_rating_manager
    from core.registry import ServiceRegistry, ToolService, get_registry
    from core.tunnel import TunnelManager, get_tunnel_manager
    from auth.user_manager import UserManager, user_manager
    from chat.channel import ChatChannelManager, get_channel_manager
    from trade.listing import ListingManager, get_listing_manager
    from trade.bid import BidManager, get_bid_manager
    from trade.negotiation import NegotiationManager, get_negotiation_manager
    from trade.transaction import TransactionManager, get_transaction_manager


# 新增：导入管理客户端和通道管理
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client")
)


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
        self.user_mgr = user_manager  # 用户管理器
        self.chat_channel_mgr = get_channel_manager()  # Chat 频道管理器

        # Trade 管理器
        self.listing_mgr = get_listing_manager()
        self.bid_mgr = get_bid_manager()
        self.negotiation_mgr = get_negotiation_manager()
        self.transaction_mgr = get_transaction_manager()

        self.clients: Set[ServerConnection] = set()
        self.running = False

        # 注册隧道转发回调
        self._client_websockets: Dict[str, ServerConnection] = {}
        self._key_request_map: Dict[str, str] = {}  # forward_request_id -> original_request_id
        self._client_info: Dict[str, dict] = {}  # client_id -> {type, service_id}
        self._pending_channels: Dict[str, dict] = {}  # request_id -> channel_request
        # 用户会话：client_id -> user_id (用于追踪连接的用户身份)
        self._client_user_map: Dict[str, str] = {}
        # Chat 消息队列：message_id -> message data
        self._chat_messages: Dict[str, dict] = {}

        self.tunnel_mgr.on("request", self._on_tunnel_request)

    async def start(self):
        """启动服务器（WebSocket + HTTP REST API）"""
        self.running = True

        # 启动后台任务
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._cleanup_loop())

        logger.info(
            f"server_started - version={__version__}, ws={self.host}:{self.port}, http={self.host}:{self.port - 5000}"
        )

        # 启动 WebSocket 服务器
        ws_server = websockets.serve(self._handle_client, self.host, self.port)

        # 尝试启动 HTTP REST API（可选）
        try:
            from aiohttp import web

            app = web.Application()
            app.router.add_get("/health", self._handle_health)
            app.router.add_get("/api/services", self._handle_api_services)
            app.router.add_get("/api/services/{service_id}", self._handle_api_service_detail)
            app.router.add_get("/api/services/{service_id}/skill.md", self._handle_api_skill_doc)
            app.router.add_get("/api/tunnels", self._handle_api_tunnels)
            app.router.add_get(
                "/api/services/{service_id}/ratings", self._handle_api_service_ratings
            )
            app.router.add_post("/api/ratings", self._handle_api_add_rating)

            # === 用户管理 API ===
            app.router.add_post("/api/users", self._handle_api_create_user)
            app.router.add_get("/api/users", self._handle_api_list_users)
            app.router.add_get("/api/users/{user_id}", self._handle_api_get_user)
            app.router.add_post("/api/users/auth", self._handle_api_auth_user)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self.host, self.port - 5000)
            await site.start()

            logger.info(f"http_rest_api_started - http://{self.host}:{self.port - 5000}")
        except ImportError:
            logger.warning(f"http_rest_api_disabled - aiohttp not installed")
        except Exception as e:
            logger.error(f"http_rest_api_failed - {str(e)}")

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
        logger.info(f"client_connected - {client_id}")

        self.clients.add(websocket)

        # 存储 client_id 到 websocket 的映射（用于隧道转发）
        self._client_websockets[client_id] = websocket

        try:
            async for message in websocket:
                await self._process_message(websocket, client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"client_disconnected: {client_id}")
        except Exception as e:
            logger.error(f"client_error: {client_id}, error: {str(e)}")
        finally:
            self.clients.discard(websocket)
            # 清理 client_id 映射
            self._client_websockets.pop(client_id, None)
            # 清理该客户端的隧道
            tunnel = self.tunnel_mgr.get_tunnel_by_client(client_id)
            if tunnel:
                await self.tunnel_mgr.close_tunnel(tunnel.id)

    async def _process_message(self, websocket: ServerConnection, client_id: str, raw_message: str):
        """处理客户端消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")

            # 调试：打印所有消息类型
            if msg_type not in ["heartbeat", "ping"]:
                logger.debug("message_received", client_id=client_id, message_type=msg_type)

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

            elif msg_type == "help":
                # 帮助命令 (TC007)
                await self._handle_help(websocket, client_id, message)

            # === Key 授权相关 ===
            elif msg_type == "lifecycle_policy":
                # Provider 注册生命周期策略
                await self._handle_lifecycle_policy(client_id, message)

            elif msg_type == "key_request":
                # Consumer 请求 Key
                print(f"[Server] DEBUG: Dispatching key_request to handler", flush=True)
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

            # === 用户注册与认证相关 ===
            elif msg_type == "user_register":
                # 用户注册
                await self._handle_user_register(websocket, client_id, message)

            elif msg_type == "user_auth":
                # 用户认证（API Key 验证）
                await self._handle_user_auth(websocket, client_id, message)

            elif msg_type == "user_list":
                # 查询用户列表（需要管理员权限）
                await self._handle_user_list(websocket, client_id, message)

            # === 用户访问控制相关 ===
            elif msg_type == "user_grant_access":
                # 服务提供者授予用户访问权限
                await self._handle_user_grant_access(websocket, client_id, message)

            elif msg_type == "user_revoke_access":
                # 服务提供者撤销用户访问权限
                await self._handle_user_revoke_access(websocket, client_id, message)

            # === Chat 通讯相关 ===
            elif msg_type == "chat_message":
                # Chat 消息处理
                await self._handle_chat_message(websocket, client_id, message)

            elif msg_type == "chat_history":
                # 获取聊天历史
                await self._handle_chat_history(websocket, client_id, message)

            # === Trade 交易相关 ===
            elif msg_type == "listing_create":
                # 创建挂牌
                await self._handle_listing_create(websocket, client_id, message)

            elif msg_type == "listing_query":
                # 查询挂牌
                await self._handle_listing_query(websocket, client_id, message)

            elif msg_type == "bid_create":
                # 创建出价
                await self._handle_bid_create(websocket, client_id, message)

            elif msg_type == "bid_accept":
                # 接受出价
                await self._handle_bid_accept(websocket, client_id, message)

            elif msg_type == "negotiation_offer":
                # 议价出价
                await self._handle_negotiation_offer(websocket, client_id, message)

            elif msg_type == "negotiation_counter":
                # 议价还价
                await self._handle_negotiation_counter(websocket, client_id, message)

            elif msg_type == "negotiation_accept":
                # 接受议价
                await self._handle_negotiation_accept(websocket, client_id, message)

            elif msg_type == "rate":
                # 服务评分
                await self._handle_rate(websocket, client_id, message)

            elif msg_type == "get_rating":
                # 获取服务评分
                await self._handle_get_rating(websocket, client_id, message)

            elif msg_type == "listing_cancel":
                # 取消挂牌/订单（TC009）
                await self._handle_listing_cancel(websocket, client_id, message)

            elif msg_type == "listing_update_price":
                # 修改挂牌价格（TC010）
                await self._handle_listing_update_price(websocket, client_id, message)

            elif msg_type == "set_price":
                # 设置/更新服务价格（支持比价功能 TC004）
                await self._handle_set_price(websocket, client_id, message)

            elif msg_type == "listing_cancel_batch":
                # 批量下架（TC011）
                await self._handle_listing_cancel_batch(websocket, client_id, message)

            elif msg_type == "transaction_create":
                # 创建交易记录
                await self._handle_transaction_create(websocket, client_id, message)

            elif msg_type == "transaction_query":
                # 查询交易记录（TC012）
                await self._handle_transaction_query(websocket, client_id, message)

            else:
                print(f"[Server] Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            print(f"[Server] Invalid JSON: {raw_message[:100]}")
        except Exception as e:
            print(f"[Server] Error processing message: {e}")

    async def _handle_help(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理帮助命令 (TC007)"""
        request_id = message.get("request_id")
        topic = message.get("topic", "general")  # 可选：指定帮助主题

        help_content = {
            "general": {
                "title": "🎯 Claw Service Hub 帮助",
                "description": "服务撮合云端 - 你的服务市场",
                "commands": {
                    "register": "注册新服务 - 发送 register 消息",
                    "list": "获取服务列表 - 使用 skill_discover 或 GET /api/services",
                    "call": "调用服务 - 使用 call_service 消息",
                    "unregister": "注销服务 - 使用 DELETE /api/services/{id}",
                    "help": "获取帮助 - 发送 help 消息",
                },
                "examples": [
                    {
                        "type": "skill_discover",
                        "description": "发现所有服务",
                        "message": {"type": "skill_discover", "query": ""}
                    },
                    {
                        "type": "skill_discover",
                        "description": "搜索服务（模糊匹配）",
                        "message": {"type": "skill_discover", "query": "天气", "fuzzy": True}
                    },
                    {
                        "type": "skill_discover",
                        "description": "按价格排序",
                        "message": {"type": "skill_discover", "sort_by": "price", "sort_order": "asc"}
                    },
                    {
                        "type": "listing_create",
                        "description": "创建服务挂牌",
                        "message": {"type": "listing_create", "service_id": "xxx", "price": 100}
                    },
                    {
                        "type": "negotiation_offer",
                        "description": "提交议价",
                        "message": {"type": "negotiation_offer", "listing_id": "xxx", "price": 80}
                    },
                ]
            },
            "register": {
                "title": "📝 服务注册",
                "description": "注册一个新的服务到市场",
                "required_fields": ["service.name", "service.description"],
                "optional_fields": ["service.version", "service.tags", "service.price", "service.price_unit", "skill_doc"],
                "example": {
                    "type": "register",
                    "client_id": "client-xxx",
                    "service": {
                        "name": "天气查询服务",
                        "description": "提供实时天气信息",
                        "version": "1.0.0",
                        "tags": ["天气", "API"],
                        "price": 0.01,
                        "price_unit": "次"
                    }
                }
            },
            "discover": {
                "title": "🔍 服务发现",
                "description": "查找和筛选服务",
                "parameters": {
                    "query": "搜索关键词（支持模糊匹配）",
                    "tags": "标签过滤",
                    "min_price": "最低价格",
                    "max_price": "最高价格",
                    "sort_by": "排序字段 (name/price/time)",
                    "sort_order": "排序方向 (asc/desc)",
                    "fuzzy": "是否启用模糊搜索"
                },
                "example": {
                    "type": "skill_discover",
                    "query": "天气",
                    "fuzzy": True,
                    "sort_by": "price",
                    "sort_order": "asc"
                }
            },
            "trade": {
                "title": "💰 交易功能",
                "description": "挂牌、出价、议价、交易",
                "commands": {
                    "listing_create": "创建服务挂牌",
                    "listing_query": "查询挂牌列表",
                    "bid_create": "创建出价",
                    "bid_accept": "接受出价",
                    "negotiation_offer": "发起议价",
                    "negotiation_counter": "还价",
                    "negotiation_accept": "接受议价",
                    "transaction_create": "创建交易"
                }
            },
            "rating": {
                "title": "⭐ 评分系统",
                "description": "为服务评分和评价",
                "api": "POST /api/ratings",
                "fields": {
                    "service_id": "服务ID",
                    "score": "评分 (0-5)",
                    "comment": "评价内容",
                    "tags": "标签"
                }
            }
        }

        # 获取对应主题的帮助内容
        content = help_content.get(topic, help_content["general"])

        await websocket.send(json.dumps({
            "type": "help",
            "request_id": request_id,
            "topic": topic,
            "content": content,
            "server_version": __version__
        }))

    async def _handle_register(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理服务注册"""
        service_data = message.get("service", {})
        skill_doc = message.get("skill_doc")  # 获取 skill.md 内容
        request_id = message.get("request_id")  # 获取请求ID

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
            price=service_data.get("price"),  # P0: 服务价格
            price_unit=service_data.get("price_unit", "次"),
            owner=service_data.get("owner"),  # P0: 服务所有者
            execution_mode=service_data.get("execution_mode", "local"),
            interface_spec=service_data.get("interface_spec", {}),
            allowed_users=service_data.get("allowed_users", []),  # 用户访问控制
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

        # 创建 Chat 频道（服务注册时自动创建）
        channel = self.chat_channel_mgr.create_channel(
            service_id=service_id,
            provider_id=client_id,
        )

        # 响应客户端
        await websocket.send(
            json.dumps(
                {
                    "type": "registered",
                    "request_id": request_id,  # 返回请求ID
                    "service_id": service_id,
                    "tunnel_id": tunnel.id,
                    "channel_id": channel.channel_id,
                    "status": "online",
                }
            )
        )

        logger.info(
            f"Service registered: {service.name} (id={service_id}, tunnel={tunnel.id})"
        )

    async def _handle_set_price(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理设置/更新服务价格（支持比价功能 TC004）"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        new_price = message.get("price")
        price_unit = message.get("price_unit", "次")
        
        if not service_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_SERVICE_ID",
                "message": "Missing service_id",
                "details": "service_id is required",
                "request_id": request_id
            }))
            return
        
        # Validate price
        if new_price is None or not isinstance(new_price, (int, float)) or new_price < 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a non-negative number",
                "request_id": request_id
            }))
            return
        
        # Get service from core.registry
        service = self.registry.get(service_id)
        if not service:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "SERVICE_NOT_FOUND",
                "message": "Service not found",
                "details": f"No service found with id: {service_id}",
                "request_id": request_id
            }))
            return
        
        # Verify ownership (client must be the service provider)
        if service.provider_client_id != client_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "NOT_SERVICE_OWNER",
                "message": "Not authorized to update this service",
                "details": "Only the service owner can update the price",
                "request_id": request_id
            }))
            return
        
        # Update price
        old_price = service.price
        service.price = new_price
        service.price_unit = price_unit
        
        # Update in registry
        self.registry._services[service_id] = service
        
        await websocket.send(json.dumps({
            "type": "price_updated",
            "service_id": service_id,
            "old_price": old_price,
            "price": new_price,
            "price_unit": price_unit,
            "request_id": request_id
        }))
        
        logger.info(
            "service_price_updated",
            service_name=service.name,
            service_id=service_id,
            old_price=old_price,
            new_price=new_price,
            price_unit=price_unit,
        )

    async def _handle_connect(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理消费者客户端连接"""
        client_type = message.get("client_type", "consumer")
        self._client_info[client_id] = {
            "type": client_type,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        await websocket.send(
            json.dumps({"type": "connected", "client_id": client_id, "client_type": client_type})
        )

        print(f"[Server] Consumer connected: {client_id} ({client_type})")

    async def _handle_skill_discover(
        self, websocket: ServerConnection, client_id: str, message: dict
    ):
        """处理 skill 方式服务发现 - 支持模糊搜索、价格排序、用户过滤"""
        request_id = message.get("request_id")
        query = message.get("query", "")
        tags = message.get("tags", [])
        execution_mode = message.get("execution_mode")
        status = message.get("status", "online")
        
        # P0: 新增过滤参数
        owner = message.get("owner")  # 用户服务过滤
        min_price = message.get("min_price")
        max_price = message.get("max_price")
        sort_by = message.get("sort_by")  # name, price, time
        sort_order = message.get("sort_order", "asc")
        fuzzy = message.get("fuzzy", True)  # 模糊搜索开关

        # 查找服务
        services = self.registry.find(
            name=query, 
            tags=tags if tags else None, 
            status=status, 
            execution_mode=execution_mode,
            owner=owner,  # P0: 用户服务过滤
            min_price=min_price,  # P0: 价格范围
            max_price=max_price,
            sort_by=sort_by,  # P0: 排序
            sort_order=sort_order,
            fuzzy=fuzzy,  # P0: 模糊搜索
        )

        # 转换为 skill 描述符
        skill_list = [s.to_skill_descriptor() for s in services]

        await websocket.send(
            json.dumps(
                {
                    "type": "skill_list",
                    "request_id": request_id,
                    "skills": skill_list,
                    "total": len(skill_list),
                }
            )
        )

        print(f"[Server] Skill discover from {client_id}: found {len(skill_list)} services")

    async def _handle_get_service_docs(
        self, websocket: ServerConnection, client_id: str, message: dict
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
                "tags": service.tags,
            }
        else:
            response = {
                "type": "error",
                "request_id": request_id,
                "message": "未找到指定的服务", "details": f"服务ID: {service_id}",
            }

        await websocket.send(json.dumps(response))

    async def _handle_get_skill_doc(
        self, websocket: ServerConnection, client_id: str, message: dict
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
                "skill_doc": skill_doc,
            }
        else:
            response = {
                "type": "error",
                "request_id": request_id,
                "message": f"Skill doc not found for service: {service_id}",
            }

        await websocket.send(json.dumps(response))

    async def _handle_establish_channel(
        self, websocket: ServerConnection, client_id: str, message: dict
    ):
        """处理建立通道请求"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        consumer_client_id = client_id  # 使用实际的 WebSocket client_id，而不是消息中的

        service = self.registry.get(service_id)

        if not service:
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "message": "未找到指定的服务", "details": f"服务ID: {service_id}",
                    }
                )
            )
            return

        # 检查服务是否在线
        if service.status != "online":
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "message": "服务当前不在线", "details": f"服务ID: {service_id}",
                    }
                )
            )
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
                "tunnel_id": service.tunnel_id,
            }

            # 通知提供者
            provider_ws = self._client_websockets.get(service.provider_client_id)
            if provider_ws:
                await provider_ws.send(
                    json.dumps(
                        {
                            "type": "channel_request",
                            "request_id": channel_request_id,
                            "service_id": service_id,
                            "user_client_id": consumer_client_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )

            print(
                f"[Server] Channel request {channel_request_id} sent to provider {service.provider_client_id}"
            )

        else:
            # 本地执行模式，直接建立通道
            await websocket.send(
                json.dumps(
                    {
                        "type": "channel_established",
                        "request_id": request_id,
                        "service_id": service_id,
                        "channel_id": service.tunnel_id,
                        "tunnel_id": service.tunnel_id,
                        "execution_mode": service.execution_mode,
                        "endpoint": service.endpoint,
                    }
                )
            )

            print(f"[Server] Channel established for {service_id} (local mode)")

    async def _handle_channel_confirm(
        self, websocket: ServerConnection, client_id: str, message: dict
    ):
        """处理服务提供者通道确认"""
        request_id = message.get("request_id")  # channel_request_id
        accepted = message.get("accepted", False)
        service_id = message.get("service_id")
        tunnel_id = message.get("tunnel_id")

        print(
            f"[Server] Channel confirm received: request_id={request_id}, accepted={accepted}",
            flush=True,
        )
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
                await consumer_ws.send(
                    json.dumps(
                        {
                            "type": "channel_established",
                            "request_id": channel_req["request_id"],
                            "service_id": service_id,
                            "channel_id": request_id,
                            "tunnel_id": tunnel_id,
                            "execution_mode": "external",
                        }
                    )
                )

            print(f"[Server] Channel {request_id} established (external mode)")
        else:
            # 通道被拒绝
            if consumer_ws:
                await consumer_ws.send(
                    json.dumps(
                        {
                            "type": "error",
                            "request_id": channel_req["request_id"],
                            "message": "服务提供者拒绝了通道请求",
                        }
                    )
                )

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
        key = message.get("key")  # 可选：Key 验证
        client_id = message.get("client_id")  # 客户端 ID，用于用户验证

        if not tunnel_id or not request_id:
            print(f"[Server] Invalid call_service message: {message}")
            return

        # 获取 service_id (从 tunnel 获取)
        service_id = None
        for svc in self.registry.list_all():
            if svc.tunnel_id == tunnel_id:
                service_id = svc.id
                break

        if not service_id:
            print(f"[Server] Service not found for tunnel {tunnel_id}")
            return

        # 用户验证（如果服务设置了 allowed_users）
        user_result = self._verify_user_for_call(service_id, client_id)
        if not user_result.get("valid"):
            # 用户无权访问
            print(f"[Server] 用户验证失败: {user_result.get('reason')}")
            # 这里需要发送错误响应，但由于我们不知道发送到哪里，先打印
            return

        # Key 验证（如果提供了 Key）
        if key:
            result = key_manager.verify_key(key, service_id)
            if not result.get("valid"):
                # Key 无效，拒绝调用
                print(f"[Server] Key验证失败: {result.get('reason')}")
                return

            # Key 有效，扣减次数
            key_manager.use_key(key)
            print(
                f"[Server] Key验证成功，剩余次数: {key_manager.get_key_info(key).get('remaining_calls')}"
            )

        # 通过 tunnel manager 转发请求
        success = await self.tunnel_mgr.forward_request(
            tunnel_id=tunnel_id, request_id=request_id, method=method, params=params
        )

        if not success:
            print(f"[Server] Failed to forward request to tunnel {tunnel_id}")

    async def _handle_request_response(self, client_id: str, message: dict):
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
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "service_response",
                                "request_id": request_id,
                                "response": response_data,
                            }
                        )
                    )
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

        message = json.dumps(
            {
                "type": "metadata_list",  # 更名为 metadata_list 以区分完整服务列表
                "services": service_list,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # 广播给所有客户端
        if self.clients:
            await asyncio.gather(*[c.send(message) for c in self.clients], return_exceptions=True)

    async def _handle_health(self, request):
        """GET /health - 健康检查"""
        from aiohttp import web

        return web.json_response(
            {
                "status": "healthy",
                "version": __version__,
                "services": len(self.registry.list_all()),
                "clients": len(self.clients),
            }
        )

    async def _handle_api_services(self, request):
        """GET /api/services - 列出所有服务 (支持查询参数过滤)
        
        Query params:
            - q: 搜索关键词 (模糊搜索)
            - tags: 逗号分隔的标签
            - status: 服务状态
            - execution_mode: 执行模式
            - owner: 服务所有者用户ID
            - min_price: 最低价格
            - max_price: 最高价格
            - sort_by: 排序字段 (name, price, time)
            - sort_order: 排序方向 (asc, desc)
            - fuzzy: 是否模糊搜索 (true/false)
        """
        from aiohttp import web

        # 解析查询参数
        query = request.query.get("q", "")
        tags_str = request.query.get("tags", "")
        tags = tags_str.split(",") if tags_str else None
        status = request.query.get("status")
        execution_mode = request.query.get("execution_mode")
        owner = request.query.get("owner")  # P0: 用户服务过滤
        min_price = request.query.get("min_price")
        max_price = request.query.get("max_price")
        sort_by = request.query.get("sort_by")
        sort_order = request.query.get("sort_order", "asc")
        fuzzy = request.query.get("fuzzy", "true").lower() == "true"
        
        # 转换价格参数
        if min_price is not None:
            try:
                min_price = float(min_price)
            except ValueError:
                min_price = None
        if max_price is not None:
            try:
                max_price = float(max_price)
            except ValueError:
                max_price = None

        # 查找服务
        services = self.registry.find(
            name=query if query else None,
            tags=tags,
            status=status,
            execution_mode=execution_mode,
            owner=owner,  # P0: 用户服务过滤
            min_price=min_price,  # P0: 价格范围
            max_price=max_price,
            sort_by=sort_by,  # P0: 排序
            sort_order=sort_order,
            fuzzy=fuzzy,  # P0: 模糊搜索
        )
        
        return web.json_response([s.to_metadata_dict() for s in services])

    async def _handle_api_service_detail(self, request):
        """GET /api/services/{service_id} - 获取服务详情"""
        from aiohttp import web

        service_id = request.match_info.get("service_id")
        service = self.registry.get(service_id)
        if service:
            return web.json_response(service.to_dict())
        return web.json_response({"error": "未找到指定的服务"}, status=404)

    async def _handle_api_skill_doc(self, request):
        """GET /api/services/{service_id}/skill.md - 获取技能文档"""
        from aiohttp import web

        service_id = request.match_info.get("service_id")
        skill_doc = self.registry.get_skill_doc(service_id)
        if skill_doc:
            return web.Response(text=skill_doc, content_type="text/markdown")
        return web.json_response({"error": "Skill doc not found"}, status=404)

    async def _handle_rate(self, websocket, client_id: str, message: dict):
        """处理服务评分 (WebSocket)"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        score = message.get("score")
        comment = message.get("comment", "")
        user_id = message.get("user_id", client_id)

        if not service_id or score is None:
            await websocket.send(json.dumps({
                "type": "error",
                "request_id": request_id,
                "error_code": "MISSING_PARAMS",
                "message": "缺少 service_id 或 score"
            }))
            return

        try:
            rating = await self.rating_mgr.add_rating(
                service_id=service_id,
                score=score,
                comment=comment,
                tags=[],
            )
            await websocket.send(json.dumps({
                "type": "rating_result",
                "request_id": request_id,
                "success": True,
                "rating": rating.to_dict()
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "rating_result",
                "request_id": request_id,
                "success": False,
                "error": str(e)
            }))

    async def _handle_get_rating(self, websocket, client_id: str, message: dict):
        """获取服务评分 (WebSocket)"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")

        if not service_id:
            await websocket.send(json.dumps({
                "type": "error",
                "request_id": request_id,
                "error_code": "MISSING_SERVICE_ID",
                "message": "缺少 service_id"
            }))
            return

        stats = self.rating_mgr.get_stats(service_id)
        await websocket.send(json.dumps({
            "type": "rating_stats",
            "request_id": request_id,
            "success": True,
            "stats": stats
        }))

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
            tags=data.get("tags", []),
        )
        return web.json_response(rating.to_dict())

    # ========== 用户管理 API 处理函数 ==========

    async def _handle_api_create_user(self, request):
        """POST /api/users - 创建用户"""
        from aiohttp import web

        data = await request.json()
        name = data.get("name")
        user = self.user_mgr.create_user(name=name)
        return web.json_response(user.to_dict())

    async def _handle_api_list_users(self, request):
        """GET /api/users - 列出用户"""
        from aiohttp import web

        users = self.user_mgr.list_users(active_only=False)
        return web.json_response({"users": users})

    async def _handle_api_get_user(self, request):
        """GET /api/users/{user_id} - 获取用户信息"""
        from aiohttp import web

        user_id = request.match_info["user_id"]
        user = self.user_mgr.get_user(user_id)
        if not user:
            return web.json_response({"error": "用户不存在"}, status=404)
        return web.json_response(user.to_metadata_dict())

    async def _handle_api_auth_user(self, request):
        """POST /api/users/auth - 验证用户 API Key"""
        from aiohttp import web

        data = await request.json()
        api_key = data.get("api_key")
        result = self.user_mgr.verify_api_key(api_key)
        if not result["valid"]:
            return web.json_response({"valid": False, "reason": result["reason"]}, status=401)
        return web.json_response({"valid": True, "user": result["user"].to_metadata_dict()})

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
        try:
            print(f"[Server] _handle_key_request: {message}")

            service_id = message.get("service_id")
            purpose = message.get("purpose", "")

            print(f"[Server] Looking for service: {service_id}")
            print(f"[Server] Registry services: {[s.id for s in self.registry.list_all()]}")

            if not service_id:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "key_request_response",
                            "success": False,
                            "reason": "缺少 service_id",
                        }
                    )
                )
                return

            # 查找服务提供者
            service = self.registry.get(service_id)
            if not service:
                await websocket.send(
                    json.dumps(
                        {"type": "key_request_response", "success": False, "reason": "服务不存在"}
                    )
                )
                return

            # 转发请求给 Provider
            provider_client_id = service.provider_client_id
            provider_ws = self._client_websockets.get(provider_client_id)

            if not provider_ws:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "key_request_response",
                            "success": False,
                            "reason": "服务提供者离线",
                        }
                    )
                )
                return

            # 构造转发请求
            forward_msg = {
                "type": "key_request",
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "service_id": service_id,
                "consumer_id": client_id,
                "purpose": purpose,
                "service_name": service.name,
            }

            await provider_ws.send(json.dumps(forward_msg))
            print(f"[Server] 转发 Key 请求: {client_id} -> {provider_client_id}")
        except Exception as e:
            print(f"[Server] ERROR in _handle_key_request: {e}", flush=True)
            import traceback

            traceback.print_exc()

        if not provider_ws:
            await websocket.send(
                json.dumps(
                    {"type": "key_request_response", "success": False, "reason": "服务提供者离线"}
                )
            )
            return

        # 构造转发请求
        original_request_id = message.get("request_id")  # 保留原始 request_id
        forward_request_id = f"req_{uuid.uuid4().hex[:8]}"

        # 保存 request_id 映射
        self._key_request_map[forward_request_id] = original_request_id

        forward_msg = {
            "type": "key_request",
            "request_id": forward_request_id,
            "original_request_id": original_request_id,  # 传递给 Provider
            "service_id": service_id,
            "consumer_id": client_id,
            "purpose": purpose,
            "service_name": service.name,
        }

        await provider_ws.send(json.dumps(forward_msg))
        print(
            f"[Server] 转发 Key 请求: {client_id} -> {provider_client_id}, request_id: {forward_request_id}"
        )

    async def _handle_key_response(self, websocket, client_id: str, message: dict):
        """处理 Provider 返回 Key（批准/拒绝）"""
        forward_request_id = message.get("request_id")
        original_request_id = self._key_request_map.get(forward_request_id, forward_request_id)

        approved = message.get("approved", False)

        if not approved:
            # 拒绝 - 通知 Consumer
            for ws in self._client_websockets.values():
                try:
                    await ws.send(
                        json.dumps(
                            {
                                "type": "key_request_response",
                                "request_id": original_request_id,
                                "success": False,
                                "reason": message.get("reason", "Provider 拒绝"),
                            }
                        )
                    )
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
            max_calls=lifecycle.get("max_calls"),
        )

        key_info = key_manager.get_key_info(key)

        # 通知 Consumer
        for ws in self._client_websockets.values():
            try:
                await ws.send(
                    json.dumps(
                        {
                            "type": "key_request_response",
                            "request_id": original_request_id,
                            "success": True,
                            "key": key,
                            "lifecycle": key_info,
                        }
                    )
                )
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

        await websocket.send(json.dumps({"type": "key_list_response", "keys": keys}))

    def _verify_key_for_call(self, service_id: str, key: str = None) -> dict:
        """验证 Key（用于 call_service 前）"""
        if not key:
            return {"valid": False, "reason": "需要 Key"}

        return key_manager.verify_key(key, service_id)

    # ========== 用户管理处理方法 ==========

    async def _handle_user_register(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理用户注册"""
        name = message.get("name")
        request_id = message.get("request_id")  # 获取请求ID
        user = self.user_mgr.create_user(name=name)

        print(f"[Server] 用户注册: {user.user_id} (name={user.name})")

        await websocket.send(
            json.dumps(
                {
                    "type": "user_register_response",
                    "request_id": request_id,  # 返回请求ID
                    "success": True,
                    "user": user.to_dict(),
                }
            )
        )

    async def _handle_user_auth(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理用户认证（API Key 验证）"""
        api_key = message.get("api_key")
        request_id = message.get("request_id")  # 获取请求ID
        result = self.user_mgr.verify_api_key(api_key)

        if result["valid"]:
            # 记录用户会话
            user_id = result["user"].user_id
            self._client_user_map[client_id] = user_id

            print(f"[Server] 用户认证成功: {user_id}")

            await websocket.send(
                json.dumps(
                    {
                        "type": "user_auth_response",
                        "request_id": request_id,  # 返回请求ID
                        "success": True,
                        "user": result["user"].to_metadata_dict(),
                    }
                )
            )
        else:
            print(f"[Server] 用户认证失败: {result['reason']}")

            await websocket.send(
                json.dumps(
                    {
                        "type": "user_auth_response",
                        "request_id": request_id,  # 返回请求ID
                        "success": False,
                        "reason": result["reason"],
                    }
                )
            )

    async def _handle_user_list(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理查询用户列表"""
        users = self.user_mgr.list_users(active_only=True)

        await websocket.send(json.dumps({"type": "user_list_response", "users": users}))

    async def _handle_user_grant_access(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理服务提供者授予用户访问权限"""
        service_id = message.get("service_id")
        user_id = message.get("user_id")

        # 获取服务
        service = self.registry.get(service_id)
        if not service:
            await websocket.send(
                json.dumps(
                    {
                        "type": "user_grant_access_response",
                        "success": False,
                        "reason": "服务不存在",
                    }
                )
            )
            return

        # 检查客户端是否有权管理该服务（必须是服务提供者）
        client_info = self._client_info.get(client_id, {})
        if client_info.get("service_id") != service_id:
            await websocket.send(
                json.dumps(
                    {
                        "type": "user_grant_access_response",
                        "success": False,
                        "reason": "无权限管理此服务",
                    }
                )
            )
            return

        # 添加用户到允许列表
        if user_id not in service.allowed_users:
            service.allowed_users.append(user_id)
            print(f"[Server] 授权用户 {user_id} 访问服务 {service_id}")

            await websocket.send(
                json.dumps(
                    {
                        "type": "user_grant_access_response",
                        "success": True,
                        "service_id": service_id,
                        "user_id": user_id,
                    }
                )
            )
        else:
            await websocket.send(
                json.dumps(
                    {
                        "type": "user_grant_access_response",
                        "success": True,
                        "reason": "用户已有访问权限",
                    }
                )
            )

    async def _handle_user_revoke_access(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理服务提供者撤销用户访问权限"""
        service_id = message.get("service_id")
        user_id = message.get("user_id")

        # 获取服务
        service = self.registry.get(service_id)
        if not service:
            await websocket.send(
                json.dumps(
                    {
                        "type": "user_revoke_access_response",
                        "success": False,
                        "reason": "服务不存在",
                    }
                )
            )
            return

        # 检查客户端是否有权管理该服务
        client_info = self._client_info.get(client_id, {})
        if client_info.get("service_id") != service_id:
            await websocket.send(
                json.dumps(
                    {
                        "type": "user_revoke_access_response",
                        "success": False,
                        "reason": "无权限管理此服务",
                    }
                )
            )
            return

        # 从允许列表中移除用户
        if user_id in service.allowed_users:
            service.allowed_users.remove(user_id)
            print(f"[Server] 撤销用户 {user_id} 对服务 {service_id} 的访问权限")

            await websocket.send(
                json.dumps(
                    {
                        "type": "user_revoke_access_response",
                        "success": True,
                        "service_id": service_id,
                        "user_id": user_id,
                    }
                )
            )
        else:
            await websocket.send(
                json.dumps(
                    {
                        "type": "user_revoke_access_response",
                        "success": True,
                        "reason": "用户没有访问权限",
                    }
                )
            )

    def _verify_user_for_call(self, service_id: str, client_id: str = None) -> dict:
        """验证用户是否有权访问服务
        
        Args:
            service_id: 服务 ID
            client_id: 客户端 ID（用于获取用户身份）
            
        Returns:
            {"valid": bool, "reason": str, "user_id": str or None}
        """
        # 获取服务
        service = self.registry.get(service_id)
        if not service:
            return {"valid": False, "reason": "服务不存在", "user_id": None}

        # 如果服务没有设置 allowed_users（空列表），则允许所有用户访问
        if not service.allowed_users:
            return {"valid": True, "reason": "", "user_id": self._client_user_map.get(client_id)}

        # 获取客户端关联的用户
        user_id = self._client_user_map.get(client_id)
        if not user_id:
            return {"valid": False, "reason": "用户未认证", "user_id": None}

        # 检查用户是否在允许列表中
        if user_id not in service.allowed_users:
            return {"valid": False, "reason": "无权限访问此服务", "user_id": user_id}

        return {"valid": True, "reason": "", "user_id": user_id}

    # ========== Chat 消息处理函数 ==========

    async def _handle_chat_message(
        self, websocket: ServerConnection, client_id: str, message: dict
    ):
        """处理 Chat 消息"""
        message_id = message.get("message_id")
        sender_id = message.get("sender_id", client_id)
        target_agent = message.get("target_agent")
        service_id = message.get("service_id")
        content = message.get("content", "")

        # 添加时间戳
        message["timestamp"] = datetime.now(timezone.utc).isoformat()

        # 存储消息
        self._chat_messages[message_id] = message

        # 通过 service_id 查找频道和目标
        if service_id:
            channel = self.chat_channel_mgr.get_channel_by_service(service_id)
            if channel:
                # 转发给 Provider
                provider_ws = self._client_websockets.get(channel.provider_id)
                if provider_ws:
                    await provider_ws.send(json.dumps({
                        "type": "chat_message",
                        "message_id": message_id,
                        "sender_id": sender_id,
                        "service_id": service_id,
                        "content": content,
                        "timestamp": message["timestamp"],
                    }))

                # 如果有 consumer，也转发
                if channel.consumer_id:
                    consumer_ws = self._client_websockets.get(channel.consumer_id)
                    if consumer_ws:
                        await consumer_ws.send(json.dumps({
                            "type": "chat_message",
                            "message_id": message_id,
                            "sender_id": sender_id,
                            "service_id": service_id,
                            "content": content,
                            "timestamp": message["timestamp"],
                        }))

                print(f"[Server] Chat message forwarded via channel {channel.channel_id}")
                return

        # 直接通过 target_agent 转发
        if target_agent:
            target_ws = self._client_websockets.get(target_agent)
            if target_ws:
                await target_ws.send(json.dumps(message))
                print(f"[Server] Chat message forwarded to {target_agent}")
                return
            else:
                print(f"[Server] Target agent {target_agent} not found")

        # 响应发送者确认收到
        await websocket.send(json.dumps({
            "type": "chat_message_ack",
            "message_id": message_id,
            "status": "delivered" if target_agent else "pending",
        }))

    async def _handle_chat_history(
        self, websocket: ServerConnection, client_id: str, message: dict
    ):
        """处理获取 Chat 历史消息"""
        request_id = message.get("request_id")
        service_id = message.get("service_id")
        channel_id = message.get("channel_id")
        limit = message.get("limit", 50)

        # 查找频道
        if channel_id:
            channel = self.chat_channel_mgr.get_channel(channel_id)
        elif service_id:
            channel = self.chat_channel_mgr.get_channel_by_service(service_id)
        else:
            channel = None

        # 获取该频道的所有消息
        messages = []
        if channel:
            # 过滤该频道相关的消息（通过 service_id）
            for msg in self._chat_messages.values():
                if msg.get("service_id") == channel.service_id:
                    messages.append(msg)

        # 限制数量
        messages = messages[-limit:]

        # 响应给客户端
        await websocket.send(json.dumps({
            "type": "chat_history_response",
            "request_id": request_id,
            "channel_id": channel_id or (channel.channel_id if channel else None),
            "service_id": service_id,
            "messages": messages,
            "total": len(messages),
        }))

        print(f"[Server] Chat history: {len(messages)} messages for {service_id or channel_id}")

    # ========== Trade 交易处理方法 ==========

    async def _handle_listing_create(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理创建挂牌"""
        # 验证必填字段
        required_fields = ["listing_id", "title", "price"]
        missing = [f for f in required_fields if not message.get(f)]
        if missing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_FIELDS",
                "message": f"Missing required fields: {missing}",
                "details": "listing_id, title, and price are required"
            }))
            return
            
        price = message.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number"
            }))
            return
            
        listing_id = message.get("listing_id")
        listing = {
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "title": message.get("title"),
            "description": message.get("description"),
            "price": price,
            "category": message.get("category", "service"),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.listing_mgr._listings[listing_id] = listing
        await websocket.send(json.dumps({
            "type": "listing_created",
            "listing_id": listing_id,
            "status": "active",
        }))
        print(f"[Server] Listing created: {listing_id} by {listing['agent_id']}")

    async def _handle_listing_query(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理查询挂牌"""
        request_id = message.get("request_id")
        category = message.get("category")
        listings = [l for l in self.listing_mgr._listings.values() if l.get("status") == "active"]
        if category:
            listings = [l for l in listings if l.get("category") == category]
        await websocket.send(json.dumps({
            "type": "listing_query_response",
            "request_id": request_id,
            "listings": listings,
            "total": len(listings),
        }))
        print(f"[Server] Listing query: {len(listings)} results")

    async def _handle_bid_create(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理创建出价"""
        # 验证必填字段
        required_fields = ["bid_id", "listing_id", "price"]
        missing = [f for f in required_fields if not message.get(f)]
        if missing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_FIELDS",
                "message": f"Missing required fields: {missing}",
                "details": "bid_id, listing_id, and price are required"
            }))
            return
            
        bid_id = message.get("bid_id")
        listing_id = message.get("listing_id")
        listing = self.listing_mgr._listings.get(listing_id)
        
        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed"
            }))
            return
            
        if listing.get("status") != "active":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_ACTIVE",
                "message": f"Listing is not active: {listing.get('status')}",
                "details": "Cannot bid on inactive listing"
            }))
            return
            
        price = message.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number"
            }))
            return
            
        bid = {
            "bid_id": bid_id,
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "price": price,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.bid_mgr._bids[bid_id] = bid
        # 通知挂牌所有者
        owner_ws = self._client_websockets.get(listing.get("agent_id"))
        if owner_ws:
            await owner_ws.send(json.dumps({"type": "bid_received", "bid": bid}))
        await websocket.send(json.dumps({"type": "bid_created", "bid_id": bid_id}))
        print(f"[Server] Bid created: {bid_id} for listing {listing_id}")

    async def _handle_bid_accept(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理接受出价"""
        bid_id = message.get("bid_id")
        if not bid_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_BID_ID",
                "message": "Missing bid_id",
                "details": "bid_id is required"
            }))
            return
            
        bid = self.bid_mgr._bids.get(bid_id)
        if not bid:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "BID_NOT_FOUND",
                "message": f"Bid not found: {bid_id}",
                "details": "The bid does not exist or has expired"
            }))
            return
            
        if bid.get("status") != "pending":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "BID_NOT_PENDING",
                "message": f"Bid is not pending: {bid.get('status')}",
                "details": "This bid has already been processed"
            }))
            return
            
        bid["status"] = "accepted"
        listing_id = bid["listing_id"]
        listing = self.listing_mgr._listings.get(listing_id)
        if listing:
            listing["status"] = "sold"
            # 创建交易记录
            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
            transaction = {
                "transaction_id": transaction_id,
                "listing_id": listing_id,
                "buyer_id": bid.get("agent_id"),
                "seller_id": listing.get("agent_id"),
                "price": bid.get("price"),
                "type": "bid",
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.transaction_mgr._transactions[transaction_id] = transaction
            print(f"[Server] Transaction created from bid: {transaction_id}")
        
        # 通知出价者
        bidder_ws = self._client_websockets.get(bid.get("agent_id"))
        if bidder_ws:
            await bidder_ws.send(json.dumps({"type": "bid_accepted", "bid_id": bid_id}))
        await websocket.send(json.dumps({"type": "bid_accept_response", "bid_id": bid_id, "status": "accepted"}))
        print(f"[Server] Bid accepted: {bid_id}")

    async def _handle_negotiation_offer(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理议价出价"""
        request_id = message.get("request_id")
        offer_id = message.get("offer_id")
        listing_id = message.get("listing_id")
        
        # 验证 listing_id
        if not listing_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_ID",
                "message": "Missing listing_id",
                "details": "listing_id is required",
                "request_id": request_id
            }))
            return
            
        listing = self.listing_mgr._listings.get(listing_id)
        if not listing:
            await websocket.send(json.dumps({
                "type": "error", 
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed",
                "request_id": request_id
            }))
            return
        
        # 验证价格
        price = message.get("price")
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number",
                "request_id": request_id
            }))
            return
            
        # 检查 listing 状态
        if listing.get("status") != "active":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_ACTIVE",
                "message": f"Listing is not active: {listing.get('status')}",
                "details": "Cannot make offer on inactive listing",
                "request_id": request_id
            }))
            return
            
        offer = {
            "offer_id": offer_id,
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "price": price,
            "type": "offer",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.negotiation_mgr._offers[offer_id] = offer
        # 通知挂牌所有者
        owner_ws = self._client_websockets.get(listing.get("agent_id"))
        if owner_ws:
            await owner_ws.send(json.dumps({"type": "negotiation_received", "offer": offer}))
        await websocket.send(json.dumps({"type": "negotiation_sent", "offer_id": offer_id, "request_id": request_id}))
        print(f"[Server] Negotiation offer: {offer_id}")

    async def _handle_negotiation_counter(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理议价还价"""
        request_id = message.get("request_id")
        offer_id = message.get("offer_id")  # 这是客户端传来的原始 offer_id
        original_offer = self.negotiation_mgr._offers.get(offer_id)
        if not original_offer:
            await websocket.send(json.dumps({
                "type": "error", 
                "error_code": "OFFER_NOT_FOUND",
                "message": f"Offer not found: {offer_id}",
                "details": "The original offer ID does not exist or has expired",
                "request_id": request_id
            }))
            return
        
        # 验证价格
        price = message.get("price")
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number",
                "request_id": request_id
            }))
            return
        
        # 验证 listing_id
        listing_id = message.get("listing_id")
        if not listing_id or listing_id not in self.listing_mgr._listings:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing ID does not exist",
                "request_id": request_id
            }))
            return
            
        # 使用客户端提供的 offer_id 作为 counter 的 ID
        # 这样客户端可以正确追踪其 counter offer
        counter_id = offer_id  # 使用原始 offer_id 作为 counter ID（简化追踪）
        
        counter = {
            "offer_id": counter_id,
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "price": price,
            "type": "counter",
            "parent_offer_id": offer_id,  # 保留对原始 offer 的引用
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # 如果已存在相同 ID 的 offer，先删除旧的
        if counter_id in self.negotiation_mgr._offers:
            del self.negotiation_mgr._offers[counter_id]
        
        self.negotiation_mgr._offers[counter_id] = counter
        
        # 通知原始出价者
        original_agent = original_offer.get("agent_id")
        original_ws = self._client_websockets.get(original_agent)
        if original_ws:
            await original_ws.send(json.dumps({
                "type": "negotiation_counter", 
                "offer": counter,
                "parent_offer_id": offer_id  # 明确告知这是对哪个 offer 的还价
            }))
        
        await websocket.send(json.dumps({
            "type": "negotiation_counter_sent", 
            "offer_id": counter_id,
            "parent_offer_id": offer_id,
            "request_id": request_id
        }))
        print(f"[Server] Negotiation counter: {counter_id} (parent: {offer_id})")

    async def _handle_negotiation_accept(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理接受议价"""
        request_id = message.get("request_id")
        offer_id = message.get("offer_id")
        if not offer_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_OFFER_ID",
                "message": "Missing offer_id",
                "details": "offer_id is required",
                "request_id": request_id
            }))
            return
            
        offer = self.negotiation_mgr._offers.get(offer_id)
        if not offer:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "OFFER_NOT_FOUND",
                "message": f"Offer not found: {offer_id}",
                "details": "The offer does not exist or has expired",
                "request_id": request_id
            }))
            return
            
        if offer.get("status") != "pending":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "OFFER_NOT_PENDING",
                "message": f"Offer is not pending: {offer.get('status')}",
                "details": "This offer has already been processed",
                "request_id": request_id
            }))
            return
            
        offer["status"] = "accepted"
        listing_id = offer["listing_id"]
        listing = self.listing_mgr._listings.get(listing_id)
        if listing:
            listing["status"] = "sold"
            # 创建交易记录
            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
            transaction = {
                "transaction_id": transaction_id,
                "listing_id": listing_id,
                "buyer_id": offer.get("agent_id"),
                "seller_id": listing.get("agent_id"),
                "price": offer.get("price"),
                "type": "negotiation",
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.transaction_mgr._transactions[transaction_id] = transaction
            print(f"[Server] Transaction created from negotiation: {transaction_id}")
        
        # 通知出价者
        offer_agent = offer.get("agent_id")
        offer_ws = self._client_websockets.get(offer_agent)
        if offer_ws:
            await offer_ws.send(json.dumps({"type": "negotiation_accepted", "offer_id": offer_id}))
        await websocket.send(json.dumps({"type": "negotiation_accept_response", "offer_id": offer_id, "status": "accepted", "request_id": request_id}))
        print(f"[Server] Negotiation accepted: {offer_id}")

    # ========== 交易功能增强 ==========
    
    async def _handle_listing_cancel(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理取消挂牌（TC009 取消订单）"""
        request_id = message.get("request_id")
        listing_id = message.get("listing_id")
        
        if not listing_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_ID",
                "message": "Missing listing_id",
                "details": "listing_id is required",
                "request_id": request_id
            }))
            return
            
        listing = self.listing_mgr._listings.get(listing_id)
        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed",
                "request_id": request_id
            }))
            return
        
        # 验证权限（只有挂牌所有者可以取消）
        if listing.get("agent_id") != client_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "PERMISSION_DENIED",
                "message": "Permission denied",
                "details": "Only the listing owner can cancel this listing",
                "request_id": request_id
            }))
            return
        
        # 检查挂牌状态
        if listing.get("status") == "sold":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_ALREADY_SOLD",
                "message": "Listing already sold",
                "details": "Cannot cancel a listing that has been sold",
                "request_id": request_id
            }))
            return
        
        # 取消挂牌
        listing["status"] = "cancelled"
        listing["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        
        await websocket.send(json.dumps({
            "type": "listing_cancelled",
            "listing_id": listing_id,
            "status": "cancelled",
            "request_id": request_id
        }))
        print(f"[Server] Listing cancelled: {listing_id}")

    async def _handle_listing_update_price(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理修改挂牌价格（TC010 修改价格）"""
        request_id = message.get("request_id")
        listing_id = message.get("listing_id")
        new_price = message.get("price")
        
        if not listing_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_ID",
                "message": "Missing listing_id",
                "details": "listing_id is required",
                "request_id": request_id
            }))
            return
        
        if new_price is None or not isinstance(new_price, (int, float)) or new_price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number",
                "request_id": request_id
            }))
            return
            
        listing = self.listing_mgr._listings.get(listing_id)
        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed",
                "request_id": request_id
            }))
            return
        
        # 验证权限
        if listing.get("agent_id") != client_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "PERMISSION_DENIED",
                "message": "Permission denied",
                "details": "Only the listing owner can update the price",
                "request_id": request_id
            }))
            return
        
        # 检查挂牌状态
        if listing.get("status") != "active":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_ACTIVE",
                "message": f"Listing is not active: {listing.get('status')}",
                "details": "Cannot update price of inactive listing",
                "request_id": request_id
            }))
            return
        
        old_price = listing.get("price")
        listing["price"] = new_price
        listing["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await websocket.send(json.dumps({
            "type": "listing_price_updated",
            "listing_id": listing_id,
            "old_price": old_price,
            "new_price": new_price,
            "status": "active",
            "request_id": request_id
        }))
        print(f"[Server] Listing price updated: {listing_id} ({old_price} -> {new_price})")

    async def _handle_listing_cancel_batch(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理批量下架（TC011 批量下架）"""
        request_id = message.get("request_id")
        listing_ids = message.get("listing_ids", [])
        
        if not listing_ids:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_IDS",
                "message": "Missing listing_ids",
                "details": "listing_ids is required and must not be empty",
                "request_id": request_id
            }))
            return
        
        results = []
        for listing_id in listing_ids:
            listing = self.listing_mgr._listings.get(listing_id)
            if not listing:
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Listing not found"
                })
                continue
            
            # 验证权限
            if listing.get("agent_id") != client_id:
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Permission denied"
                })
                continue
            
            # 检查状态
            if listing.get("status") == "sold":
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Listing already sold"
                })
                continue
            
            # 取消挂牌
            listing["status"] = "cancelled"
            listing["cancelled_at"] = datetime.now(timezone.utc).isoformat()
            results.append({
                "listing_id": listing_id,
                "status": "cancelled"
            })
        
        success_count = sum(1 for r in results if r["status"] == "cancelled")
        await websocket.send(json.dumps({
            "type": "listing_cancelled_batch",
            "results": results,
            "total": len(listing_ids),
            "success_count": success_count,
            "request_id": request_id
        }))
        print(f"[Server] Batch cancel: {success_count}/{len(listing_ids)} listings cancelled")

    # 交易记录存储: transaction_id -> transaction
    _transactions: Dict[str, dict] = {}
    
    async def _handle_transaction_create(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理创建交易记录（购买成交时记录）"""
        transaction_id = message.get("transaction_id")
        listing_id = message.get("listing_id")
        buyer_id = message.get("buyer_id")
        seller_id = message.get("seller_id")
        price = message.get("price")
        
        if not all([transaction_id, listing_id, buyer_id, seller_id, price]):
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_FIELDS",
                "message": "Missing required fields",
                "details": "transaction_id, listing_id, buyer_id, seller_id, and price are required"
            }))
            return
        
        transaction = {
            "transaction_id": transaction_id,
            "listing_id": listing_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "price": price,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.transaction_mgr._transactions[transaction_id] = transaction
        
        # 同时记录到 buyer 和 seller 的消费/收入记录
        # (在用户对象中记录，这里先简化为存储在 _transactions 中)
        
        await websocket.send(json.dumps({
            "type": "transaction_created",
            "transaction_id": transaction_id,
            "status": "completed"
        }))
        print(f"[Server] Transaction created: {transaction_id}")

    async def _handle_transaction_query(self, websocket: ServerConnection, client_id: str, message: dict):
        """处理查询交易记录（TC012 查询消费记录）"""
        request_id = message.get("request_id")
        query_type = message.get("query_type", "all")  # all, bought, sold
        agent_id = message.get("agent_id")  # 可选：查询特定用户的记录
        
        transactions = []
        
        for txn in self.transaction_mgr._transactions.values():
            if query_type == "bought":
                # 查询购买的（消费记录）
                if agent_id and txn.get("buyer_id") == agent_id:
                    transactions.append(txn)
                elif not agent_id and txn.get("buyer_id") == client_id:
                    transactions.append(txn)
            elif query_type == "sold":
                # 查询销售的（收入记录）
                if agent_id and txn.get("seller_id") == agent_id:
                    transactions.append(txn)
                elif not agent_id and txn.get("seller_id") == client_id:
                    transactions.append(txn)
            else:
                # 全部记录
                if agent_id:
                    if txn.get("buyer_id") == agent_id or txn.get("seller_id") == agent_id:
                        transactions.append(txn)
                else:
                    if txn.get("buyer_id") == client_id or txn.get("seller_id") == client_id:
                        transactions.append(txn)
        
        # 计算总消费/收入
        total_spent = sum(t.get("price", 0) for t in transactions if t.get("buyer_id") == (agent_id or client_id))
        total_earned = sum(t.get("price", 0) for t in transactions if t.get("seller_id") == (agent_id or client_id))
        
        await websocket.send(json.dumps({
            "type": "transaction_query_response",
            "request_id": request_id,
            "transactions": transactions,
            "total": len(transactions),
            "total_spent": total_spent,
            "total_earned": total_earned,
            "query_type": query_type
        }))
        print(f"[Server] Transaction query: {len(transactions)} records for {agent_id or client_id}")


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
