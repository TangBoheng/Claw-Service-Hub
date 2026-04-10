#!/usr/bin/env python3
"""
Claw Service Hub - 服务注册、发现、调用

使用方式:
    # 终端指令
    python hub_runner.py discover --query=weather
    python hub_runner.py call weather-service query --params='{"city":"Beijing"}'
    python hub_runner.py register my-service --description="My API"

    # Python 脚本
    from hub_runner import ServiceRunner
    async with ServiceRunner() as runner:
        services = await runner.discover(query="weather")
        result = await runner.call("weather-service", "query", {"city": "Beijing"})
"""

import asyncio
import json
import sys
import os

# 添加 client 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client"))

from claw_client import HubClient
from claw_client.exceptions import ClientError


class ServiceRunner:
    """Service Skill 运行器"""

    def __init__(self, hub_url: str = "ws://localhost:8765"):
        self.hub_url = hub_url
        self.client: HubClient = None

    async def connect(self):
        """连接到 Hub"""
        self.client = HubClient(url=self.hub_url)
        await self.client.connect()
        return self

    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def discover(self, query: str = "", tags: list = None) -> list:
        """发现服务"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.search(query=query, tags=tags or [])

    async def call(self, service_id: str, method: str, params: dict = None) -> dict:
        """调用服务"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.call(service_id=service_id, method=method, params=params or {})

    async def register_service(self, name: str, description: str, price: float = 0, tags: list = None) -> dict:
        """注册服务"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.provide(service_id=name, description=description, price=price, tags=tags or [])

    def print_services(self, services: list):
        """打印服务列表"""
        if not services:
            print("暂无可用服务")
            return
        print(f"可用服务 ({len(services)}):")
        for svc in services:
            name = svc.get("name", "N/A")
            desc = svc.get("description", "")[:50]
            price = svc.get("price", 0)
            print(f"  - {name}: {desc} (¥{price})")

    def print_result(self, result: dict):
        """打印结果"""
        if "error" in result:
            print(f"错误：{result['error']}")
        else:
            print("结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))


async def cli_main():
    """CLI 入口点"""
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print("""
Claw Service Hub - 服务注册、发现、调用

用法:
    python hub_runner.py <command> [options]

命令:
    discover [--query=<q>] [--tags=<a,b>]   发现服务
    call <service_id> <method> [--params=<json>]  调用服务
    register <name> --description=<desc> [--price=<p>]  注册服务
    help                                    显示帮助

示例:
    python hub_runner.py discover --query=weather
    python hub_runner.py call weather-service query --params='{"city":"Beijing"}'
    python hub_runner.py register my-service --description="My API" --price=10
""")
        return

    command = sys.argv[1]

    async with ServiceRunner() as runner:
        if command == "discover":
            query = ""
            tags = None
            for arg in sys.argv[2:]:
                if arg.startswith("--query="):
                    query = arg.split("=", 1)[1]
                elif arg.startswith("--tags="):
                    tags = arg.split("=", 1)[1].split(",")
            services = await runner.discover(query=query, tags=tags)
            runner.print_services(services)

        elif command == "call":
            if len(sys.argv) < 4:
                print("用法：python hub_runner.py call <service_id> <method> [--params=<json>]")
                return
            service_id = sys.argv[2]
            method = sys.argv[3]
            params = {}
            for arg in sys.argv[4:]:
                if arg.startswith("--params="):
                    params = json.loads(arg.split("=", 1)[1])
            result = await runner.call(service_id, method, params)
            runner.print_result(result)

        elif command == "register":
            if len(sys.argv) < 3:
                print("用法：python hub_runner.py register <name> --description=<desc>")
                return
            name = sys.argv[2]
            description = ""
            price = 0
            tags = None
            for arg in sys.argv[3:]:
                if arg.startswith("--description="):
                    description = arg.split("=", 1)[1]
                elif arg.startswith("--price="):
                    price = float(arg.split("=", 1)[1])
                elif arg.startswith("--tags="):
                    tags = arg.split("=", 1)[1].split(",")
            result = await runner.register_service(name, description, price, tags)
            runner.print_result(result)
        else:
            print(f"未知命令：{command}")
            print("使用 'python hub_runner.py help' 查看帮助")


if __name__ == "__main__":
    asyncio.run(cli_main())
