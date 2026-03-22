"""
示例：纯管理型客户端注册服务（subagent1 场景）

这个示例演示：
- subagent1 注册一个数据服务（只管理，不执行）
- 实际业务由外部服务处理（如 n8n webhook 或 python 服务）
"""

import asyncio
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.management_client import ManagementOnlyClient


async def main():
    """
    subagent1: 注册一个图片数据服务
    - 服务元数据注册到撮合系统
    - 实际执行交给外部端点（如 n8n workflow）
    - subagent1 只管理，不执行业务
    """

    # 定义服务接口规范
    interface_spec = {
        "methods": [
            {
                "name": "list_images",
                "description": "列出可用的图片",
                "parameters": {
                    "limit": {"type": "integer", "default": 10, "max": 100},
                    "offset": {"type": "integer", "default": 0},
                },
                "returns": {
                    "images": [{"id": "string", "url": "string", "label": "string"}],
                    "total": "integer",
                },
            },
            {
                "name": "get_image",
                "description": "获取单张图片",
                "parameters": {"id": {"type": "string", "required": True}},
                "returns": {"id": "string", "url": "string", "data": "base64"},
            },
        ],
        "data_source": "~/data/dataset/coco/images/val2017",
        "authentication": "none",
    }

    # 创建纯管理型客户端
    client = ManagementOnlyClient(
        name="coco-image-service",
        description="COCO数据集图片访问服务 - 提供图片列表和下载",
        version="1.0.0",
        endpoint="http://localhost:8080/api/coco",  # 外部执行器地址（n8n/python服务）
        tags=["image", "coco", "dataset", "data"],
        emoji="🖼️",
        execution_mode="external",  # 关键：external 表示外部执行
        interface_spec=interface_spec,
        hub_url="ws://localhost:8765",
    )

    # 注册回调：当用户请求建立通道时
    async def on_channel_request(message):
        print(f"\n[Subagent1] 收到通道请求: {message}")
        # 自动确认通道（可根据需要添加权限检查）
        request_id = message.get("request_id")
        await client.confirm_channel(request_id, accepted=True)
        print(f"[Subagent1] 已确认通道: {request_id}")

    client.on("channel_request", on_channel_request)

    # 注册回调：当服务成功注册
    async def on_registered(service_id, tunnel_id):
        print(f"\n[Subagent1] 服务注册成功!")
        print(f"  - Service ID: {service_id}")
        print(f"  - Tunnel ID: {tunnel_id}")
        print(f"  - Execution Mode: external (只管理不执行)")
        print(f"\n[Subagent1] 等待用户通过 skill 方式查询并建立通道...")

    client.on("registered", on_registered)

    try:
        # 连接到撮合系统并注册服务
        await client.connect()

        # 保持运行
        print("\n" + "=" * 50)
        print("Subagent1 运行中...")
        print("=" * 50)
        print("服务已注册，等待 subagent2 查询和调用")
        print("按 Ctrl+C 停止")

        while client.running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n[Subagent1] 停止中...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
