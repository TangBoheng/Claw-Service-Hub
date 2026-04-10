#!/usr/bin/env python3
"""
Claw Chat Hub - 智能体通讯能力

使用方式:
    # 终端指令
    python hub_runner.py send --target=agent_b --content="Hello"
    python hub_runner.py history --channel=ch_xxx --limit=50

    # Python 脚本
    from hub_runner import ChatRunner
    async with ChatRunner(agent_id="my-agent") as runner:
        await runner.send_message("agent_b", "Hello")
        history = await runner.get_history(channel_id="ch_xxx")
"""

import asyncio
import json
import sys
import os
from typing import Optional, Callable

# 添加 client 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client"))

from claw_client import HubClient
from claw_client.exceptions import ClientError


class ChatRunner:
    """Chat Skill 运行器"""

    def __init__(self, agent_id: str = None, hub_url: str = "ws://localhost:8765"):
        self.agent_id = agent_id
        self.hub_url = hub_url
        self.client: HubClient = None
        self._message_callback: Optional[Callable] = None

    async def connect(self):
        """连接到 Hub"""
        self.client = HubClient(url=self.hub_url, name=self.agent_id)
        await self.client.connect()
        self.client.on_message(self._on_message)
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

    def on_message(self, callback: Callable):
        """注册消息回调"""
        self._message_callback = callback
        if self.client:
            self.client.on_message(callback)

    def _on_message(self, msg: dict):
        """内部消息处理"""
        if self._message_callback:
            self._message_callback(msg)

    async def send_message(self, target: str, content: str, service_id: str = None) -> dict:
        """发送消息"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.send(target=target, content=content, service_id=service_id)

    async def request_chat(self, service_id: str, message: str = "") -> dict:
        """请求通讯"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.request_chat(service_id=service_id, message=message)

    async def accept_chat(self, consumer_id: str, message: str = "") -> dict:
        """接受通讯"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.accept_chat(consumer_id=consumer_id, message=message)

    async def reject_chat(self, consumer_id: str, reason: str = "") -> dict:
        """拒绝通讯"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.reject_chat(consumer_id=consumer_id, reason=reason)

    async def end_chat(self, channel_id: str, reason: str = "") -> dict:
        """结束通讯"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.end_chat(channel_id=channel_id, reason=reason)

    async def get_history(self, channel_id: str, limit: int = 50) -> list:
        """获取历史消息"""
        if not self.client:
            raise RuntimeError("未连接")
        return await self.client.history(channel_id=channel_id, limit=limit)

    def print_messages(self, messages: list):
        """打印消息列表"""
        if not messages:
            print("暂无消息")
            return
        print(f"历史消息 ({len(messages)}):")
        for msg in messages:
            sender = msg.get("sender", "N/A")
            content = msg.get("content", "")
            ts = msg.get("timestamp", "")[:16]
            print(f"  [{ts}] {sender}: {content}")


async def cli_main():
    """CLI 入口点"""
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print("""
Claw Chat Hub - 智能体通讯能力

用法:
    python hub_runner.py <command> [options]

命令:
    send --target=<agent> --content=<msg>      发送消息
    request --service-id=<svc>                 请求通讯
    accept --consumer-id=<agent>               接受通讯
    reject --consumer-id=<agent> --reason=<r>  拒绝通讯
    end --channel=<ch_id>                      结束通讯
    history --channel=<ch_id> [--limit=50]     获取历史
    help                                        显示帮助

示例:
    python hub_runner.py send --target=agent_b --content="Hello"
    python hub_runner.py request --service-id=weather-service
    python hub_runner.py history --channel=ch_xxx --limit=100
""")
        return

    command = sys.argv[1]
    agent_id = None
    for arg in sys.argv:
        if arg.startswith("--agent-id="):
            agent_id = arg.split("=", 1)[1]
            break

    async with ChatRunner(agent_id=agent_id or "cli-agent") as runner:
        if command == "send":
            target = ""
            content = ""
            service_id = None
            for arg in sys.argv[2:]:
                if arg.startswith("--target="):
                    target = arg.split("=", 1)[1]
                elif arg.startswith("--content="):
                    content = arg.split("=", 1)[1]
                elif arg.startswith("--service-id="):
                    service_id = arg.split("=", 1)[1]
            if not target or not content:
                print("用法：python hub_runner.py send --target=<agent> --content=<msg>")
                return
            result = await runner.send_message(target, content, service_id)
            runner.print_messages([result] if result else [])

        elif command == "request":
            service_id = None
            message = ""
            for arg in sys.argv[2:]:
                if arg.startswith("--service-id="):
                    service_id = arg.split("=", 1)[1]
                elif arg.startswith("--message="):
                    message = arg.split("=", 1)[1]
            if not service_id:
                print("用法：python hub_runner.py request --service-id=<svc>")
                return
            result = await runner.request_chat(service_id, message)
            print(f"请求结果：{result}")

        elif command == "history":
            channel_id = None
            limit = 50
            for arg in sys.argv[2:]:
                if arg.startswith("--channel="):
                    channel_id = arg.split("=", 1)[1]
                elif arg.startswith("--limit="):
                    limit = int(arg.split("=", 1)[1])
            if not channel_id:
                print("用法：python hub_runner.py history --channel=<ch_id>")
                return
            messages = await runner.get_history(channel_id, limit)
            runner.print_messages(messages)

        elif command == "end":
            channel_id = None
            reason = ""
            for arg in sys.argv[2:]:
                if arg.startswith("--channel="):
                    channel_id = arg.split("=", 1)[1]
                elif arg.startswith("--reason="):
                    reason = arg.split("=", 1)[1]
            if not channel_id:
                print("用法：python hub_runner.py end --channel=<ch_id>")
                return
            result = await runner.end_chat(channel_id, reason)
            print(f"结束结果：{result}")

        else:
            print(f"未知命令：{command}")
            print("使用 'python hub_runner.py help' 查看帮助")


if __name__ == "__main__":
    asyncio.run(cli_main())
