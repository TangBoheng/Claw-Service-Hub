# 🛠️ Tool Service Hub

[English](#english) | [中文](#中文)

---

## English

### Overview

**Tool Service Hub** is a service orchestration platform for OpenClaw that enables:

- **Service Registration**: Publish local capabilities as discoverable services
- **Service Discovery**: Find and use services published by other agents
- **Service Invocation**: Call remote services via WebSocket

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool Service Hub                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Service    │  │   Tunnel    │  │   Rating    │         │
│  │  Registry   │  │   Manager   │  │   Manager   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                         │                                    │
│                    WebSocket :8765                          │
└─────────────────────────────────────────────────────────────┘
           ▲                ▲                 ▲
           │                │                 │
    ┌──────┴──────┐  ┌──────┴──────┐   ┌──────┴──────┐
    │  Provider   │  │  Provider   │   │  Provider   │
    │ (subagent1) │  │ (subagent2) │   │ (subagent3) │
    │ (Data Svc)  │  │ (Workflow)  │   │ (API Svc)   │
    └────────────┘  └────────────┘   └────────────┘
```

### Quick Start

#### 1. Install Dependencies

```bash
pip install websockets aiohttp
```

#### 2. Start Hub Server

```bash
cd Claw-Service-Hub
python -m server.main
```

Server listens on `ws://localhost:8765`

#### 3. As a Provider - Register Your Service

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

#### 4. As a Consumer - Discover and Call Services

```python
import asyncio
import sys
sys.path.insert(0, '.')
from client.skill_client import SkillQueryClient

async def main():
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    # Discover services
    services = await client.discover()
    print(f"Found {len(services)} services")
    
    # Call a service
    result = await client.call_service(
        service_id="service-skill-id",
        method="my_method",
        params={"key": "value"}
    )
    print(result)
    
    await client.disconnect()

asyncio.run(main())
```

### Project Structure

```
Claw-Service-Hub/
├── client/
│   ├── client.py           # LocalServiceRunner, ToolServiceClient
│   ├── skill_client.py     # SkillQueryClient, SkillConsumer
│   └── management_client.py # ManagementOnlyClient
├── server/
│   └── main.py             # Hub Server (WebSocket + REST API)
├── skills/
│   └── hub-client/
│       └── SKILL.md        # Complete skill documentation
└── README.md
```

### Skill Documentation

See [skills/hub-client/SKILL.md](./skills/hub-client/SKILL.md) for complete usage guide including:

- Provider/Consumer templates
- Common data source examples (file, API, weather)
- Troubleshooting guide
- Environment configuration

### Features

| Feature | Status |
|---------|--------|
| Service Registration | ✅ |
| Service Discovery (by name/tag) | ✅ |
| Heartbeat/Keep-alive | ✅ |
| WebSocket Tunnel | ✅ |
| Rating System (1-10) | ✅ |
| REST API | ✅ |

---

## 中文

### 概述

**Tool Service Hub** 是 OpenClaw 的服务撮合平台，实现：

- **服务注册**：将本地能力发布为可发现的服务
- **服务发现**：查找并使用其他 agent 发布的服务
- **服务调用**：通过 WebSocket 调用远程服务

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool Service Hub 服务中心                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  服务注册   │  │  隧道管理   │  │  评分系统   │         │
│  │  Registry   │  │  Manager    │  │  Manager    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                         │                                    │
│                    WebSocket :8765                          │
└─────────────────────────────────────────────────────────────┘
           ▲                ▲                 ▲
           │                │                 │
    ┌──────┴──────┐  ┌──────┴──────┐   ┌──────┴──────┐
    │  Provider   │  │  Provider   │   │  Provider   │
    │ (subagent1) │  │ (subagent2) │   │ (subagent3) │
    │ (数据服务)  │  │ (工作流)    │   │ (API服务)   │
    └────────────┘  └────────────┘   └────────────┘
```

### 快速开始

#### 1. 安装依赖

```bash
pip install websockets aiohttp
```

#### 2. 启动 Hub 服务器

```bash
cd Claw-Service-Hub
python -m server.main
```

服务器监听 `ws://localhost:8765`

#### 3. 作为 Provider - 注册服务

```python
import asyncio
import sys
sys.path.insert(0, '.')
from client.client import LocalServiceRunner

async def my_handler(**params):
    return {"result": "你好，来自服务！"}

async def main():
    runner = LocalServiceRunner(
        name="my-service",
        description="我的服务",
        hub_url="ws://localhost:8765"
    )
    runner.register_handler("my_method", my_handler)
    await runner.run()

asyncio.run(main())
```

#### 4. 作为 Consumer - 发现并调用服务

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
    print(f"发现 {len(services)} 个服务")
    
    # 调用服务
    result = await client.call_service(
        service_id="服务ID",
        method="方法名",
        params={"参数": "值"}
    )
    print(result)
    
    await client.disconnect()

asyncio.run(main())
```

### 项目结构

```
Claw-Service-Hub/
├── client/
│   ├── client.py           # LocalServiceRunner, ToolServiceClient
│   ├── skill_client.py      # SkillQueryClient, SkillConsumer
│   └── management_client.py # ManagementOnlyClient
├── server/
│   └── main.py              # Hub 服务器 (WebSocket + REST API)
├── skills/
│   └── hub-client/
│       └── SKILL.md        # 完整的 Skill 使用文档
└── README.md
```

### Skill 完整文档

详见 [skills/hub-client/SKILL.md](./skills/hub-client/SKILL.md)，包含：

- Provider/Consumer 完整模板
- 常见数据源示例（文件、API、天气）
- 故障排查指南
- 环境配置说明

### 功能列表

| 功能 | 状态 |
|------|------|
| 服务注册 | ✅ |
| 服务发现（按名称/标签） | ✅ |
| 心跳保活 | ✅ |
| WebSocket 隧道 | ✅ |
| 评分系统 (1-10分) | ✅ |
| REST API | ✅ |

### 使用示例

**场景**：每日穿衣推荐 + NG 图片推荐

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ weather-service │────▶│   Hub (WS:8765)  │◀────│ ng-image-service    │
│  (天气服务)     │     │   (服务中心)      │     │  (NG图片服务)        │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                               ▲
                               │
                        ┌──────┴──────┐
                        │  Consumer   │
                        │  (工作流)   │
                        └─────────────┘
```

**结果**：
```
📍 Shanghai | 15°C | 阴
👔 穿衣建议：温度适中，建议穿长袖衬衫或薄外套
🎨 今日搭配灵感: 时尚春季穿搭
```

---

## 🔗 Links

- [GitHub](https://github.com/TangBoheng/Claw-Service-Hub)
- [OpenClaw](https://github.com/openclaw/openclaw)