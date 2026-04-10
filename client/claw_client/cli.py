#!/usr/bin/env python3
"""
Claw Service Hub Client CLI.

Usage:
    claw-client connect <url> [--name=<name>]
    claw-client service register <name> --description=<desc> [--endpoint=<url>]
    claw-client service list
    claw-client service call <service_id> <method> [--params=<json>]
    claw-client service discover [--query=<q>]
    claw-client key request <service_id> [--purpose=<text>]
    claw-client chat send <target> --content=<msg>
    claw-client --help
    claw-client --version

Options:
    --name=<name>           客户端名称
    --description=<desc>    服务描述
    --endpoint=<url>        服务端点
    --params=<json>         方法参数（JSON 格式）
    --query=<q>             搜索关键词
    --purpose=<text>        Key 用途说明
    --content=<msg>         消息内容
    --help                  显示帮助
    --version               显示版本
"""

import asyncio
import json
import sys
from typing import Optional

from claw_client.exceptions import ConnectionError
from claw_client.hub.client import HubClient


class ClawClientCLI:
    """Claw Service Hub CLI 主类"""

    def __init__(self):
        self.client: Optional[HubClient] = None
        self.config_file = "~/.claw_client/config.json"

    async def connect(self, url: str, name: str = None):
        """连接到 Hub"""
        self.client = HubClient(url=url, name=name)
        try:
            await self.client.connect()
            print(f"✓ 已连接到 {url}")
            print(f"  Client ID: {self.client.client_id}")
            return True
        except ConnectionError as e:
            print(f"✗ 连接失败：{e}")
            return False

    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.disconnect()
            print("✓ 已断开连接")

    async def register_service(self, name: str, description: str, endpoint: str = "",
                                price: float = 0, tags: list = None):
        """注册服务"""
        if not self.client:
            print("✗ 未连接，请先执行 connect")
            return

        result = await self.client.provide(
            service_id=name,
            description=description,
            price=price,
            tags=tags or [],
        )

        if result.get("status") == "registered":
            print(f"✓ 服务已注册：{name}")
            print(f"  Service ID: {result.get('service_id')}")
        else:
            print(f"✗ 注册失败：{result.get('error', 'Unknown error')}")

    async def list_services(self):
        """列出服务"""
        if not self.client:
            print("✗ 未连接")
            return

        services = await self.client.discover()
        if services:
            print(f"可用服务 ({len(services)}):")
            for svc in services:
                name = svc.get("name", "N/A")
                desc = svc.get("description", "")[:50]
                price = svc.get("price", 0)
                print(f"  - {name}: {desc} (¥{price})")
        else:
            print("暂无可用服务")

    async def discover_services(self, query: str = ""):
        """搜索服务"""
        if not self.client:
            print("✗ 未连接")
            return

        services = await self.client.search(query=query)
        if services:
            print(f"搜索结果 ({len(services)}):")
            for svc in services:
                name = svc.get("name", "N/A")
                desc = svc.get("description", "")[:50]
                print(f"  - {name}: {desc}")
        else:
            print("未找到匹配的服务")

    async def call_service(self, service_id: str, method: str, params: dict = None):
        """调用服务"""
        if not self.client:
            print("✗ 未连接")
            return

        result = await self.client.call(
            service_id=service_id,
            method=method,
            params=params or {},
        )

        if "error" in result:
            print(f"✗ 调用失败：{result['error']}")
        else:
            print("✓ 调用成功:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

    async def request_key(self, service_id: str, purpose: str = ""):
        """请求 API Key"""
        if not self.client:
            print("✗ 未连接")
            return

        result = await self.client.request_key(
            service_id=service_id,
            purpose=purpose,
        )

        if result.get("key"):
            print("✓ Key 已获取:")
            print(f"  Key: {result['key'][:20]}...")
            print(f"  剩余次数：{result.get('lifecycle', {}).get('remaining_calls', 'N/A')}")
        else:
            print(f"✗ 获取失败：{result.get('error', 'Unknown error')}")

    async def send_message(self, target: str, content: str):
        """发送消息"""
        if not self.client:
            print("✗ 未连接")
            return

        result = await self.client.send(target=target, content=content)
        if result.get("status") == "sent":
            print(f"✓ 消息已发送，Message ID: {result.get('message_id')}")
        else:
            print(f"✗ 发送失败：{result.get('error', 'Unknown error')}")


def print_help():
    """打印帮助信息"""
    print("""
Claw Service Hub Client CLI

用法:
    claw-client <command> [options]

命令:
    connect <url>                  连接到 Hub
    disconnect                     断开连接
    service register <name>        注册服务
    service list                   列出服务
    service discover [--query=]    搜索服务
    service call <id> <method>     调用服务
    key request <service_id>       请求 API Key
    chat send <target> --content=  发送消息
    help                           显示帮助
    version                        显示版本

示例:
    claw-client connect ws://localhost:8765
    claw-client service register my-service --description="My API"
    claw-client service list
    claw-client service call weather-service query --params='{"city":"Beijing"}'
    claw-client key request weather-service --purpose="Data analysis"
    claw-client chat send user-123 --content="Hello!"
""")


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    cli = ClawClientCLI()
    command = sys.argv[1]

    if command in ("--help", "help", "-h"):
        print_help()
        sys.exit(0)

    if command in ("--version", "version", "-v"):
        from claw_client import __version__
        print(f"Claw Service Hub Client v{__version__}")
        sys.exit(0)

    if command == "connect":
        if len(sys.argv) < 3:
            print("Usage: claw-client connect <url> [--name=<name>]")
            sys.exit(1)
        url = sys.argv[2]
        name = None
        for arg in sys.argv[3:]:
            if arg.startswith("--name="):
                name = arg.split("=", 1)[1]
        asyncio.run(cli.connect(url, name))

    elif command == "disconnect":
        asyncio.run(cli.disconnect())

    elif command == "service":
        if len(sys.argv) < 3:
            print("Usage: claw-client service <register|list|discover|call> [args]")
            sys.exit(1)

        subcmd = sys.argv[2]

        if subcmd == "register":
            if len(sys.argv) < 4:
                print("Usage: claw-client service register <name> --description=<desc>")
                sys.exit(1)
            name = sys.argv[3]
            desc = ""
            endpoint = ""
            price = 0
            for arg in sys.argv[4:]:
                if arg.startswith("--description="):
                    desc = arg.split("=", 1)[1]
                elif arg.startswith("--endpoint="):
                    endpoint = arg.split("=", 1)[1]
                elif arg.startswith("--price="):
                    price = float(arg.split("=", 1)[1])
            asyncio.run(cli.register_service(name, desc, endpoint, price))

        elif subcmd == "list":
            asyncio.run(cli.list_services())

        elif subcmd == "discover":
            query = ""
            for arg in sys.argv[3:]:
                if arg.startswith("--query="):
                    query = arg.split("=", 1)[1]
            asyncio.run(cli.discover_services(query))

        elif subcmd == "call":
            if len(sys.argv) < 5:
                print("Usage: claw-client service call <service_id> <method> [--params=<json>]")
                sys.exit(1)
            service_id = sys.argv[3]
            method = sys.argv[4]
            params = {}
            for arg in sys.argv[5:]:
                if arg.startswith("--params="):
                    params = json.loads(arg.split("=", 1)[1])
            asyncio.run(cli.call_service(service_id, method, params))

    elif command == "key":
        if len(sys.argv) < 4 or sys.argv[2] != "request":
            print("Usage: claw-client key request <service_id> [--purpose=<text>]")
            sys.exit(1)
        service_id = sys.argv[3]
        purpose = ""
        for arg in sys.argv[4:]:
            if arg.startswith("--purpose="):
                purpose = arg.split("=", 1)[1]
        asyncio.run(cli.request_key(service_id, purpose))

    elif command == "chat":
        if len(sys.argv) < 5 or sys.argv[2] != "send":
            print("Usage: claw-client chat send <target> --content=<msg>")
            sys.exit(1)
        target = sys.argv[3]
        content = ""
        for arg in sys.argv[4:]:
            if arg.startswith("--content="):
                content = arg.split("=", 1)[1]
        asyncio.run(cli.send_message(target, content))

    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
