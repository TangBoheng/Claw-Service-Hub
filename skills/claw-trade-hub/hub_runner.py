#!/usr/bin/env python3
"""
Claw Trade Hub - 交易议价能力
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client"))

from claw_client import HubClient


class TradeRunner:
    """Trade Hub 运行器"""

    def __init__(self, agent_id: str = None, hub_url: str = "ws://localhost:8765"):
        self.agent_id = agent_id
        self.hub_url = hub_url
        self.client: HubClient = None

    async def connect(self):
        self.client = HubClient(url=self.hub_url, name=self.agent_id)
        await self.client.connect()
        return self

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def create_listing(self, title: str, price: float, description: str = "") -> dict:
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client._send_request("listing_create", {"title": title, "description": description, "price": price})

    async def query_listings(self) -> list:
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client._send_request("listing_query", {})

    async def bid(self, listing_id: str, price: float) -> dict:
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.bid(listing_id=listing_id, price=price)

    async def negotiate(self, listing_id: str, price: float) -> dict:
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.negotiate(listing_id=listing_id, price=price)

    def print_listings(self, listings: list):
        if not listings:
            print("暂无挂牌")
            return
        print(f"挂牌列表 ({len(listings)}):")
        for item in listings:
            title = item.get("title", "N/A")
            price = item.get("price", 0)
            print(f"  - {title}: ¥{price}")

    def print_result(self, result: dict):
        if "error" in result:
            print(f"错误：{result['error']}")
        else:
            print("结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))


async def cli_main():
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print("""
Claw Trade Hub - 交易议价能力

用法:
    python hub_runner.py <command> [options]

命令:
    list --title=<t> --price=<p>     创建挂牌
    query                            查询挂牌
    bid --listing-id=<id> --price=<p>  出价
    negotiate --listing-id=<id> --price=<p>  议价
    help                             显示帮助
""")
        return

    command = sys.argv[1]
    agent_id = None
    for arg in sys.argv:
        if arg.startswith("--agent-id="):
            agent_id = arg.split("=", 1)[1]
            break

    async with TradeRunner(agent_id=agent_id or "cli-agent") as runner:
        if command == "list":
            title = ""
            price = 0
            for arg in sys.argv[2:]:
                if arg.startswith("--title="):
                    title = arg.split("=", 1)[1]
                elif arg.startswith("--price="):
                    price = float(arg.split("=", 1)[1])
            if not title:
                print("用法：python hub_runner.py list --title=<t> --price=<p>")
                return
            result = await runner.create_listing(title, price)
            runner.print_result(result)
        elif command == "query":
            listings = await runner.query_listings()
            runner.print_listings(listings)
        elif command == "bid":
            listing_id = ""
            price = 0
            for arg in sys.argv[2:]:
                if arg.startswith("--listing-id="):
                    listing_id = arg.split("=", 1)[1]
                elif arg.startswith("--price="):
                    price = float(arg.split("=", 1)[1])
            result = await runner.bid(listing_id, price)
            runner.print_result(result)
        elif command == "negotiate":
            listing_id = ""
            price = 0
            for arg in sys.argv[2:]:
                if arg.startswith("--listing-id="):
                    listing_id = arg.split("=", 1)[1]
                elif arg.startswith("--price="):
                    price = float(arg.split("=", 1)[1])
            result = await runner.negotiate(listing_id, price)
            runner.print_result(result)
        else:
            print(f"未知命令：{command}")


if __name__ == "__main__":
    asyncio.run(cli_main())
