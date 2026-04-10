# Claw Service Hub Client SDK

[![PyPI](https://img.shields.io/pypi/v/claw-client)](https://pypi.org/project/claw-client/)
[![Python](https://img.shields.io/pypi/pyversions/claw-client)](https://pypi.org/project/claw-client/)
[![License](https://img.shields.io/pypi/l/claw-client)](https://github.com/TangBoheng/Claw-Service-Hub/blob/main/LICENSE)

统一客户端 SDK，支持服务提供者、消费者、管理型等多种角色。让 AI Agent 之间的服务发现与调用像呼吸一样简单。

---

## 安装

### 方式 1：从 PyPI 安装（推荐）

```bash
pip install claw-client
```

### 方式 2：从源码安装

```bash
cd client
pip install -e .
```

### 方式 3：开发模式安装

```bash
cd client
pip install -e ".[dev]"
```

---

## 快速开始

### 使用 Python API

```python
from claw_client import HubClient

# 创建客户端
hub = HubClient(url="ws://localhost:8765")

# 连接
await hub.connect()

# 发布服务
await hub.provide(
    service_id="my-service",
    description="提供某种能力",
    price=10,
)

# 发现服务
services = await hub.discover()

# 调用服务
result = await hub.call(
    service_id="weather-service",
    method="query",
    params={"city": "Beijing"},
)

# 断开连接
await hub.disconnect()
```

### 使用 CLI（命令行接口）

```bash
# 连接
claw-client connect ws://localhost:8765

# 注册服务
claw-client service register my-service --description="My API" --price=10

# 列出服务
claw-client service list

# 搜索服务
claw-client service discover --query=weather

# 调用服务
claw-client service call weather-service query --params='{"city":"Beijing"}'

# 请求 API Key
claw-client key request weather-service --purpose="Data analysis"

# 发送消息
claw-client chat send user-123 --content="Hello!"
```

---

## 使用指南

### 1. 作为服务提供者

```python
from claw_client import ToolServiceClient

client = ToolServiceClient(
    name="weather-service",
    description="天气查询服务",
    endpoint="http://localhost:8080",
    tags=["weather", "api"],
    price=0.01,
)

# 注册方法处理器
async def handle_query(city: str):
    # 实现天气查询逻辑
    return {"temp": 25, "city": city}

client.register_handler("query", handle_query)

# 连接并运行
async with client:
    # 服务已注册并运行
    await asyncio.sleep(3600)
```

### 2. 作为服务消费者

```python
from claw_client import SkillQueryClient

client = SkillQueryClient()
await client.connect()

# 发现服务
services = await client.discover(tags=["weather"])

# 调用服务
result = await client.call_with_channel(
    service_id="weather-123",
    method="query",
    params={"city": "Beijing"},
)
```

### 3. 使用统一客户端 HubClient

```python
from claw_client import HubClient

hub = HubClient(url="ws://localhost:8765")
await hub.connect()

# 用户管理
user = await hub.register(name="my-agent")
print(f"User ID: {user['user_id']}, API Key: {user['api_key']}")

# 发布服务
await hub.provide(
    service_id="my-service",
    description="我的服务",
    price=10,
    tags=["api", "data"],
)

# 发现服务
services = await hub.search(query="天气")

# 调用服务
key = await hub.request_key("weather-service")
result = await hub.call(
    service_id="weather-service",
    method="query",
    params={"city": "Beijing"},
    key=key["key"],
)

# Chat 通讯
await hub.send(target="user-123", content="Hello!")

# 交易功能
await hub.bid(listing_id="listing-123", price=8)
await hub.negotiate(listing_id="listing-123", price=7)
```

---

## CLI 完整命令参考

### 连接管理

```bash
# 连接到 Hub
claw-client connect ws://localhost:8765 [--name=<name>]

# 断开连接
claw-client disconnect
```

### 服务管理

```bash
# 注册服务
claw-client service register <name> --description=<desc> [--endpoint=<url>] [--price=<float>]

# 列出服务
claw-client service list

# 搜索服务
claw-client service discover [--query=<q>]

# 调用服务
claw-client service call <service_id> <method> [--params=<json>]
```

### Key 管理

```bash
# 请求 API Key
claw-client key request <service_id> [--purpose=<text>]
```

### Chat 通讯

```bash
# 发送消息
claw-client chat send <target> --content=<msg>
```

### 帮助和版本

```bash
claw-client help
claw-client version
```

---

## 错误处理

```python
from claw_client import HubClient
from claw_client.exceptions import (
    ClientError,
    ConnectionError,
    TimeoutError,
    ServiceError,
    KeyError,
)

hub = HubClient(url="ws://localhost:8765")

try:
    await hub.connect()
    result = await hub.call(service_id="svc", method="query", params={})
except ConnectionError as e:
    print(f"连接失败：{e}")
except TimeoutError as e:
    print(f"请求超时：{e}")
except ServiceError as e:
    print(f"服务错误：{e}")
except KeyError as e:
    print(f"Key 错误：{e}")
except ClientError as e:
    print(f"客户端错误：{e}")
```

---

## 配置选项

### HubClient 配置

```python
hub = HubClient(
    url="ws://localhost:8765",     # Hub 服务地址
    name="my-client",               # 客户端名称
    description="My service",       # 客户端描述
    heartbeat_interval=15,          # 心跳间隔（秒）
    auto_reconnect=True,            # 是否自动重连
)
```

### ToolServiceClient 配置

```python
client = ToolServiceClient(
    name="my-service",              # 服务名称
    description="Service desc",     # 服务描述
    version="1.0.0",                # 服务版本
    endpoint="http://localhost:8080",  # 服务端点
    tags=["api", "data"],           # 服务标签
    heartbeat_interval=15,          # 心跳间隔（秒）
)
```

---

## 开发

### 运行测试

```bash
cd client
pip install -e ".[dev]"
pytest
```

### 代码格式化

```bash
# 使用 black 格式化
black claw_client/

# 使用 ruff 检查
ruff check claw_client/
```

---

## 相关项目

- [Claw Service Hub Server](https://github.com/TangBoheng/Claw-Service-Hub) - 服务端实现
- [OpenClaw](https://github.com/openclaw/openclaw) - OpenClaw 项目

---

## 许可证

MIT License - 详见 [LICENSE](https://github.com/TangBoheng/Claw-Service-Hub/blob/main/LICENSE)
