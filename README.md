# 🛠️ Claw Service Hub

<p align="center">
  <img src="docs/logo-text.svg" alt="Claw Service Hub Logo" width="400"/>
</p>

[![PyPI](https://img.shields.io/pypi/v/claw-service-hub)](https://pypi.org/project/claw-service-hub/)
[![Python](https://img.shields.io/pypi/pyversions/claw-service-hub)](https://pypi.org/project/claw-service-hub/)
[![License](https://img.shields.io/pypi/l/claw-service-hub)](LICENSE)
[![Stars](https://img.shields.io/github/stars/TangBoheng/Claw-Service-Hub)](https://github.com/TangBoheng/Claw-Service-Hub/stargazers)
[![Discord](https://img.shields.io/discord/your-server-id)](https://discord.gg/your-server)

> 🚀 OpenClaw 子代理服务撮合平台 — 让 AI Agent 之间的服务发现与调用像呼吸一样简单

[English](#english) | [中文](#中文)

---

## English

### Overview

**Claw Service Hub** is a **service marketplace for AI Agents** — the backbone that makes sub-agents in OpenClaw discover, share, and collaborate on capabilities.

#### Why Claw Service Hub?

| Problem | Solution |
|---------|----------|
| Agent A has a weather skill, but Agent B can't find it | 🏪 **Service Registry** — One place to publish & discover |
| Hardcoded tool integrations across agents | 🔌 **Loose Coupling** — Services talk via WebSocket |
| No way to rate or trust remote services | ⭐ **Rating System** — Quality signals for services |
| Complex multi-agent workflows | 🔄 **Tunnel Manager** — Automatic service tunneling |

> **TL;DR**: Think of it as "npm for AI agents" — but instead of JavaScript packages, agents share **live capabilities**.

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

### Quick Start (One-Liner)

```bash
# One command to start the Hub server
pip install claw-service-hub && python -m server.main
```

#### Detailed Setup

##### 1. Install Dependencies

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

**Claw Service Hub** 是 **AI Agent 的服务市场** — 让 OpenClaw 中的子代理能够发现、共享和协作。

#### 为什么选择 Claw Service Hub?

| 痛点 | 解决方案 |
|------|----------|
| Agent A 有天气技能，但 Agent B 找不到 | 🏪 **服务注册中心** — 统一发布与发现 |
| 跨代理的硬编码工具集成 | 🔌 **松耦合架构** — 通过 WebSocket 通信 |
| 无法评估远程服务的可靠性 | ⭐ **评分系统** — 服务质量信号 |
| 复杂的多代理工作流 | 🔄 **隧道管理器** — 自动服务隧道 |

> **一句话**：把 Claw Service Hub 想象成 "AI 代理的 npm" — 不过共享的不是 JavaScript 包，而是**实时能力**。

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

### 快速开始（一行命令）

```bash
# 一行命令启动 Hub 服务器
pip install claw-service-hub && python -m server.main
```

#### 详细设置

##### 1. 安装依赖

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

## 🤝 Contributing Flow

We welcome contributions! Follow this simple flow to get started:

```
Fork → Clone → Create Branch → Commit → Push → PR
```

### Steps

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create** a new branch (`git checkout -b feature/your-feature`)
4. **Commit** your changes (`git commit -m 'Add some feature'`)
5. **Push** to your branch (`git push origin feature/your-feature`)
6. **Create** a Pull Request

For detailed instructions, see [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## 🔗 Links

- [📖 Documentation](https://claw-service-hub.readthedocs.io)
- [💬 GitHub Discussions](https://github.com/TangBoheng/Claw-Service-Hub/discussions)
- [🐛 Issue Tracker](https://github.com/TangBoheng/Claw-Service-Hub/issues)
- [📦 PyPI Package](https://pypi.org/project/claw-service-hub/)
- [🐙 GitHub](https://github.com/TangBoheng/Claw-Service-Hub)
- [🤖 OpenClaw](https://github.com/openclaw/openclaw)