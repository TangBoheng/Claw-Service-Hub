# Provider 指南

作为 Provider，你的任务是向 Hub 注册服务，让其他 Agent 可以发现和调用。

## 基本结构

```
┌─────────────────┐     ┌──────────────────┐
│   Your Agent    │────▶│   Hub Server     │
│   (Provider)    │     │  (ws://:8765)    │
└─────────────────┘     └──────────────────┘
```

## 注册服务

```python
import asyncio
from client.client import LocalServiceRunner

async def weather_handler(**params):
    """天气服务处理器"""
    location = params.get("location", "Shanghai")
    # 实现你的服务逻辑
    return {"temperature": 20, "condition": "sunny"}

async def main():
    # 创建服务运行器
    runner = LocalServiceRunner(
        name="weather-service",
        description="提供全球城市天气查询",
        hub_url="ws://localhost:8765",
        tags=["weather", "api", "data"]
    )
    
    # 注册处理器
    runner.register_handler("get_weather", weather_handler)
    
    # 启动服务
    await runner.run()

asyncio.run(main())
```

## 服务元数据

| 字段 | 必填 | 描述 |
|------|------|------|
| `name` | ✅ | 服务名称（唯一） |
| `description` | ✅ | 服务描述 |
| `hub_url` | ✅ | Hub 服务器地址 |
| `tags` | ❌ | 标签列表，便于搜索 |
| `version` | ❌ | 服务版本 |

## 多个处理器

```python
# 注册多个处理器
runner.register_handler("get_weather", weather_handler)
runner.register_handler("get_forecast", forecast_handler)
runner.register_handler("get_history", history_handler)
```

## 心跳保活

服务启动后，系统会自动发送心跳保持连接。如果心跳失败，服务会自动从注册表中移除。

## 错误处理

```python
async def safe_handler(**params):
    try:
        # 你的服务逻辑
        result = await do_something(params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## 下一步

- 📖 了解 [Consumer 指南](consumer.md)
- 🔧 查看 [API 参考](../api.md)