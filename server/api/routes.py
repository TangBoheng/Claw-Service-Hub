"""REST API routes for Claw Service Hub."""

from typing import Any


class ApiRoutes:
    """REST API 路由处理器"""

    def __init__(self, registry, tunnel_mgr, rating_mgr, user_mgr):
        self.registry = registry
        self.tunnel_mgr = tunnel_mgr
        self.rating_mgr = rating_mgr
        self.user_mgr = user_mgr

    def setup_routes(self, app: Any):
        """设置所有路由"""
        from aiohttp import web

        # Health check
        app.router.add_get("/health", self.handle_health)

        # Services
        app.router.add_get("/api/services", self.handle_services)
        app.router.add_get("/api/services/{service_id}", self.handle_service_detail)
        app.router.add_get("/api/services/{service_id}/skill.md", self.handle_skill_doc)

        # Tunnels
        app.router.add_get("/api/tunnels", self.handle_tunnels)

        # Ratings
        app.router.add_get("/api/services/{service_id}/ratings", self.handle_service_ratings)
        app.router.add_post("/api/ratings", self.handle_add_rating)

        # Users
        app.router.add_post("/api/users", self.handle_create_user)
        app.router.add_get("/api/users", self.handle_list_users)
        app.router.add_get("/api/users/{user_id}", self.handle_get_user)
        app.router.add_post("/api/users/auth", self.handle_auth_user)

    async def handle_health(self, request: Any) -> Any:
        """GET /health - 健康检查"""
        from aiohttp import web
        from server import __version__

        # 需要引用 HubServer 的 clients
        return web.json_response({
            "status": "healthy",
            "version": __version__,
            "services": len(self.registry.list_all()),
        })

    async def handle_services(self, request: Any) -> Any:
        """GET /api/services - 列出所有服务"""
        from aiohttp import web

        # 解析查询参数
        query = request.query.get("q", "")
        tags_str = request.query.get("tags", "")
        tags = tags_str.split(",") if tags_str else None
        status = request.query.get("status")
        execution_mode = request.query.get("execution_mode")
        owner = request.query.get("owner")
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
            owner=owner,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_order=sort_order,
            fuzzy=fuzzy,
        )

        return web.json_response([s.to_metadata_dict() for s in services])

    async def handle_service_detail(self, request: Any) -> Any:
        """GET /api/services/{service_id} - 获取服务详情"""
        from aiohttp import web

        service_id = request.match_info.get("service_id")
        service = self.registry.get(service_id)
        if service:
            return web.json_response(service.to_dict())
        return web.json_response({"error": "未找到指定的服务"}, status=404)

    async def handle_skill_doc(self, request: Any) -> Any:
        """GET /api/services/{service_id}/skill.md - 获取技能文档"""
        from aiohttp import web

        service_id = request.match_info.get("service_id")
        skill_doc = self.registry.get_skill_doc(service_id)
        if skill_doc:
            return web.Response(text=skill_doc, content_type="text/markdown")
        return web.json_response({"error": "Skill doc not found"}, status=404)

    async def handle_tunnels(self, request: Any) -> Any:
        """GET /api/tunnels - 列出所有隧道"""
        from aiohttp import web

        tunnels = self.tunnel_mgr.list_tunnels()
        return web.json_response([t.to_dict() for t in tunnels])

    async def handle_service_ratings(self, request: Any) -> Any:
        """GET /api/services/{service_id}/ratings - 获取服务评分"""
        from aiohttp import web

        service_id = request.match_info.get("service_id")
        stats = self.rating_mgr.get_stats(service_id)
        return web.json_response(stats)

    async def handle_add_rating(self, request: Any) -> Any:
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

    async def handle_create_user(self, request: Any) -> Any:
        """POST /api/users - 创建用户"""
        from aiohttp import web

        data = await request.json()
        name = data.get("name")
        user = self.user_mgr.create_user(name=name)
        return web.json_response(user.to_dict())

    async def handle_list_users(self, request: Any) -> Any:
        """GET /api/users - 列出用户"""
        from aiohttp import web

        users = self.user_mgr.list_users(active_only=False)
        return web.json_response({"users": users})

    async def handle_get_user(self, request: Any) -> Any:
        """GET /api/users/{user_id} - 获取用户信息"""
        from aiohttp import web

        user_id = request.match_info["user_id"]
        user = self.user_mgr.get_user(user_id)
        if not user:
            return web.json_response({"error": "用户不存在"}, status=404)
        return web.json_response(user.to_metadata_dict())

    async def handle_auth_user(self, request: Any) -> Any:
        """POST /api/users/auth - 验证用户 API Key"""
        from aiohttp import web

        data = await request.json()
        api_key = data.get("api_key")
        result = self.user_mgr.verify_api_key(api_key)
        if not result["valid"]:
            return web.json_response({"valid": False, "reason": result["reason"]}, status=401)
        return web.json_response({"valid": True, "user": result["user"].to_metadata_dict()})
