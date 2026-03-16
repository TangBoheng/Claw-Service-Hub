"""
CSV Processor Tool Service Example

This demonstrates how to use the new SkillMetadata + skill.md feature.
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client import ToolServiceClient


async def handle_analyze(file_path: str) -> dict:
    """Analyze CSV file"""
    # 简化示例，实际应该读取文件
    return {
        "status": "success",
        "file_path": file_path,
        "row_count": 100,
        "column_count": 5,
        "message": "CSV analyzed successfully"
    }


async def handle_convert(file_path: str, target_format: str = "json") -> dict:
    """Convert CSV to other format"""
    return {
        "status": "success",
        "file_path": file_path,
        "target_format": target_format,
        "message": f"Converted to {target_format}"
    }


async def main():
    """启动 CSV Processor 工具服务"""
    skill_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建客户端，自动加载 SKILL.md
    client = ToolServiceClient(
        name="csv-processor",
        description="Process and analyze CSV files locally",
        version="1.0.0",
        tags=["csv", "data", "processor"],
        emoji="📊",
        requires={"bins": ["python"], "env": []},
        skill_dir=skill_dir,  # 会自动加载 SKILL.md
        hub_url="ws://localhost:8765"
    )

    # 注册处理器
    client.register_handler("analyze", handle_analyze)
    client.register_handler("convert", handle_convert)

    try:
        # 连接到云端
        await client.connect()
        print(f"[CSV Processor] Service running with skill_dir: {skill_dir}")

        # 保持运行
        while client.running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n[CSV Processor] Shutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
