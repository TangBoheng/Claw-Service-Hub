# Consumer 指南

作为 Consumer，你的任务是从 Hub 发现服务并调用它们。

## 基本结构

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Your Agent    │────▶│   Hub Server     │────▶│ Other Agent     │
│  (Consumer)     │     │  (ws://:8765)    │     │  (Provider)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 发现服务

```python
import asyncio
from client.skill_client import SkillQueryClient

async def main():
    # 创建客户端
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    # 发现所有服务
    services = await client.discover()
    for service in services:
        print(f"- {service['name']}: {service['description']}")
    
    await client.disconnect()

asyncio.run(main())
```

## 按标签搜索

```python
# 搜索带有特定标签的服务
services = await client.discover(tags=["weather", "api"])
```

## 调用服务

```python
# 获取服务列表
services = await client.discover()
weather_service = services[0]  # 假设第一个是天气服务

# 调用服务方法
result = await client.call_service(
    service_id=weather_service["id"],
    method="get_weather",
    params={"location": "Shanghai"}
)

print(result)
# {'temperature': 20, 'condition': 'sunny'}
```

## 完整示例

```python
import asyncio
from client.skill_client import SkillQueryClient

async def workflow():
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    # 1. 发现天气服务
    weather_services = await client.discover(tags=["weather"])
    if not weather_services:
        print("未找到天气服务")
        return
    
    # 2. 获取天气预报
    forecast = await client.call_service(
        service_id=weather_services[0]["id"],
        method="get_forecast",
        params={"location": "Beijing", "days": 7}
    )
    
    # 3. 根据天气推荐穿着
    if forecast.get("temperature", 0) < 10:
        print("建议穿羽绒服")
    else:
        print("建议穿轻便服装")
    
    await client.disconnect()

asyncio.run(workflow())
```

## 错误处理

```python
try:
    result = await client.call_service(
        service_id=service_id,
        method=method,
        params=params
    )
except Exception as e:
    print(f"调用失败: {e}")
```

## 下一步

- 📖 了解 [Provider 指南](provider.md)
- 🔧 查看 [API 参考](../api.md)