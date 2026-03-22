# 快速开始

本指南将帮助你快速启动 Claw Service Hub 并运行你的第一个服务。

## 环境要求

- Python 3.10+
- pip 包管理器

## 安装

```bash
pip install claw-service-hub
```

或从源码安装：

```bash
git clone https://github.com/TangBoheng/Claw-Service-Hub.git
cd Claw-Service-Hub
pip install -e .
```

## 启动 Hub 服务器

```bash
python -m server.main
```

服务器将在 `ws://localhost:8765` 启动。

## 作为 Provider 注册服务

```python
import asyncio
import sys
sys.path.insert(0, '.')
from client.client import LocalServiceRunner

async def my_handler(**params):
    return {"result": "Hello from service!"}

async def main():
    runner = LocalServiceRunner(
        name="my-service",
        description="My awesome service",
        hub_url="ws://localhost:8765"
    )
    runner.register_handler("my_method", my_handler)
    await runner.run()

asyncio.run(main())
```

## 作为 Consumer 发现并调用服务

```python
import asyncio
import sys
sys.path.insert(0, '.')
from client.skill_client import SkillQueryClient

async def main():
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    # 发现服务
    services = await client.discover()
    print(f"Found {len(services)} services")
    
    # 调用服务
    result = await client.call_service(
        service_id="service-skill-id",
        method="my_method",
        params={"key": "value"}
    )
    print(result)
    
    await client.disconnect()

asyncio.run(main())
```

## 下一步

- 📖 阅读 [Provider 指南](guide/provider.md)
- 📖 阅读 [Consumer 指南](guide/consumer.md)
- 🔧 查看 [API 参考](api.md)