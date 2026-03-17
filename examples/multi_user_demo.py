"""
完整示例：多用户数据服务共享场景

演示流程：
1. 启动云端服务器
2. subagent1 注册服务（只管理）
3. subagent2 查询服务（skill方式）
4. subagent2 建立通道并调用
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入服务器组件
from server.main import HubServer
from client.management_client import ManagementOnlyClient
from client.skill_client import SkillQueryClient


async def run_server():
    """运行云端服务器"""
    server = HubServer(host="localhost", port=8765)
    await server.start()


async def run_subagent1():
    """subagent1: 注册服务"""
    await asyncio.sleep(1)  # 等待服务器启动

    # 定义服务接口
    interface_spec = {
        "methods": [
            {
                "name": "list_images",
                "description": "列出可用的图片",
                "parameters": {"limit": {"type": "integer", "default": 10}}
            },
            {
                "name": "get_image",
                "description": "获取单张图片",
                "parameters": {"id": {"type": "string", "required": True}}
            }
        ],
        "data_source": "~/data/dataset/coco/images/val2017"
    }

    client = ManagementOnlyClient(
        name="coco-image-service",
        description="COCO数据集图片访问服务",
        version="1.0.0",
        endpoint="http://localhost:8080/api/coco",
        tags=["image", "coco", "dataset"],
        emoji="🖼️",
        execution_mode="external",
        interface_spec=interface_spec,
        hub_url="ws://localhost:8765"
    )

    # 自动接受通道请求
    async def on_channel_request(message):
        request_id = message.get("request_id")
        await client.confirm_channel(request_id, accepted=True)
        print(f"[Subagent1] 自动确认通道: {request_id}")

    client.on("channel_request", on_channel_request)

    await client.connect()
    print(f"\n[Subagent1] 服务已注册: {client.service_id}")

    # 保持运行
    while client.running:
        await asyncio.sleep(1)


async def run_subagent2():
    """subagent2: 查询和调用服务"""
    await asyncio.sleep(2)  # 等待服务注册

    client = SkillQueryClient(hub_url="ws://localhost:8765")
    await client.connect()

    print("\n" + "="*50)
    print("Subagent2: 开始查询")
    print("="*50)

    # 步骤1: 发现服务
    print("\n[Subagent2] 步骤1: 发现服务...")
    services = await client.discover(tags=["image"])
    print(f"[Subagent2] 找到 {len(services)} 个图片服务")

    for s in services:
        print(f"  - {s['name']}: {s['description']}")

    if not services:
        print("[Subagent2] 未找到服务，退出")
        await client.disconnect()
        return

    service = services[0]
    service_id = service['skill_id']

    # 步骤2: 获取文档
    print(f"\n[Subagent2] 步骤2: 获取服务文档...")
    docs = await client.get_docs(service_id)
    print(f"  名称: {docs.get('name')}")
    print(f"  执行模式: {docs.get('execution_mode')}")
    print(f"  接口: {list(docs.get('interface_spec', {}).keys())}")

    # 步骤3: 建立通道
    print(f"\n[Subagent2] 步骤3: 建立通道...")
    channel = await client.establish_channel(service_id)

    if 'error' in channel:
        print(f"[Subagent2] 通道建立失败: {channel['error']}")
        await client.disconnect()
        return

    print(f"[Subagent2] 通道建立成功: {channel.get('channel_id')}")

    # 步骤4: 调用服务
    print(f"\n[Subagent2] 步骤4: 调用服务...")
    result = await client.call_service(
        service_id=service_id,
        method="list_images",
        params={"limit": 5}
    )
    print(f"[Subagent2] 调用结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 完成
    print("\n" + "="*50)
    print("Subagent2: 流程完成")
    print("="*50)

    await asyncio.sleep(1)
    await client.disconnect()


async def main():
    """运行完整示例"""
    print("="*50)
    print("多用户数据服务共享示例")
    print("="*50)
    print("\n启动顺序:")
    print("1. 云端服务器")
    print("2. Subagent1 (服务注册)")
    print("3. Subagent2 (查询和调用)")
    print()

    # 创建任务
    tasks = [
        asyncio.create_task(run_subagent2(), name="subagent2"),
        asyncio.create_task(run_subagent1(), name="subagent1"),
    ]

    # 运行示例（带超时）
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=30
        )
    except asyncio.TimeoutError:
        print("\n[示例] 超时，正在停止...")
    finally:
        for task in tasks:
            task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[示例] 用户中断")
