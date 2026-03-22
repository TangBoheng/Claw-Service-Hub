"""
示例：Skill 方式查询和调用服务（subagent2 场景）

这个示例演示：
- subagent2 通过 skill 方式查询可用服务
- 获取服务文档和接口描述
- 建立服务通道
- 调用远程服务
"""

import asyncio
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.skill_client import SkillQueryClient


async def main():
    """
    subagent2: 通过 skill 方式发现和使用服务
    """

    # 创建 skill 查询客户端
    client = SkillQueryClient(hub_url="ws://localhost:8765")

    try:
        # 连接到撮合系统
        await client.connect()

        print("=" * 50)
        print("Subagent2: Skill 方式查询服务")
        print("=" * 50)

        # 步骤1: 发现服务
        print("\n步骤1: 查询可用的图片服务...")
        services = await client.discover(
            query="coco", tags=["image", "data"], execution_mode="external"  # 只查询外部执行的服务
        )

        if not services:
            print("未找到匹配的服务")
            return

        print(f"找到 {len(services)} 个服务:")
        for s in services:
            print(f"  - {s['emoji']} {s['name']} (v{s['version']})")
            print(f"    ID: {s['skill_id']}")
            print(f"    描述: {s['description']}")
            print(f"    标签: {', '.join(s['tags'])}")
            print()

        # 选择第一个服务
        service = services[0]
        service_id = service["skill_id"]

        # 步骤2: 获取服务文档
        print("\n步骤2: 获取服务文档...")
        docs = await client.get_docs(service_id)

        print(f"服务名称: {docs['name']}")
        print(f"描述: {docs['documentation']}")
        print(f"执行模式: {docs['execution_mode']}")
        print(f"外部端点: {docs['endpoint']}")

        if docs.get("interface_spec"):
            spec = docs["interface_spec"]
            print(f"\n接口规范:")
            for method in spec.get("methods", []):
                print(f"  - {method['name']}: {method['description']}")
                print(f"    参数: {list(method.get('parameters', {}).keys())}")

        # 步骤3: 建立服务通道
        print("\n步骤3: 建立服务通道...")
        channel = await client.establish_channel(service_id)

        if "error" in channel:
            print(f"建立通道失败: {channel['error']}")
            return

        print(f"通道建立成功!")
        print(f"  Channel ID: {channel.get('channel_id')}")
        print(f"  Tunnel ID: {channel.get('tunnel_id')}")

        # 步骤4: 调用服务
        print("\n步骤4: 调用服务...")

        # 调用 list_images 方法
        result = await client.call_service(
            service_id=service_id, method="list_images", params={"limit": 5}
        )

        if "error" in result:
            print(f"调用失败: {result['error']}")
        else:
            print(f"调用成功!")
            print(f"结果: {result}")

        # 保持连接一段时间
        print("\n保持连接 10 秒...")
        await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\n[Subagent2] 停止中...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
