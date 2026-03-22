# 示例

本节提供完整的示例代码帮助你快速上手。

## 目录

- [天气服务示例](#weather)
- [数据源服务示例](#data-source)

---

## 天气服务示例

作为 Provider 注册一个简单的天气服务：

```python
import asyncio
from client.client import LocalServiceRunner

# 模拟天气数据
WEATHER_DATA = {
    "Shanghai": {"temp": 18, "condition": "Cloudy"},
    "Beijing": {"temp": 12, "condition": "Sunny"},
    "Shenzhen": {"temp": 25, "condition": "Rainy"}
}

async def get_weather(**params):
    location = params.get("location", "Shanghai")
    return WEATHER_DATA.get(location, {"temp": 0, "condition": "Unknown"})

async def get_forecast(**params):
    location = params.get("location", "Shanghai")
    days = params.get("days", 3)
    return {
        "location": location,
        "forecast": [
            {"day": i+1, "temp": 15+i, "condition": "Sunny"} 
            for i in range(days)
        ]
    }

async def main():
    runner = LocalServiceRunner(
        name="weather-service",
        description="全球城市天气查询服务",
        hub_url="ws://localhost:8765",
        tags=["weather", "api", "data"]
    )
    
    runner.register_handler("get_weather", get_weather)
    runner.register_handler("get_forecast", get_forecast)
    
    print("🌤️ 天气服务已启动...")
    await runner.run()

asyncio.run(main())
```

**Consumer 端调用：**

```python
import asyncio
from client.skill_client import SkillQueryClient

async def main():
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    services = await client.discover(tags=["weather"])
    if not services:
        print("未找到天气服务")
        return
    
    result = await client.call_service(
        service_id=services[0]["id"],
        method="get_weather",
        params={"location": "Shanghai"}
    )
    
    print(f"上海天气: {result}")
    await client.disconnect()

asyncio.run(main())
```

---

## 数据源服务示例 {#data-source}

提供文件读取、API 调用等数据源服务：

```python
import asyncio
import aiohttp
from client.client import LocalServiceRunner

async def fetch_url(**params):
    url = params.get("url")
    if not url:
        return {"error": "URL is required"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
            return {
                "status": response.status,
                "content_length": len(content),
                "preview": content[:200]
            }

async def read_file(**params):
    import os
    path = params.get("path")
    if not path or not os.path.exists(path):
        return {"error": "File not found"}
    
    with open(path, 'r') as f:
        content = f.read()
    
    return {"path": path, "size": len(content), "content": content[:500]}

async def main():
    runner = LocalServiceRunner(
        name="data-source-service",
        description="通用数据源服务",
        hub_url="ws://localhost:8765",
        tags=["data", "utility", "api"]
    )
    
    runner.register_handler("fetch_url", fetch_url)
    runner.register_handler("read_file", read_file)
    
    print("📦 数据源服务已启动...")
    await runner.run()

asyncio.run(main())
```

---

## 更多示例

- 📂 [CSV Processor Skill](../csv-processor-skill/) - 处理 CSV 文件
- 🔌 [External Executor](../external_executor.py) - 外部执行器
- 👤 [Subagent1 Management](../subagent1_management_only.py) - 管理型客户端
- 🔍 [Subagent2 Consumer](../subagent2_skill_consumer.py) - 消费型客户端