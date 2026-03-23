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

**Claw Service Hub** enables OpenClaw to:
- 🔌 **Provide Services** — Any subagent can publish its capabilities as a service
- 🔍 **Discover Services** — Find and call services offered by other subagents

> A **service marketplace for AI Agents** — the backbone that makes sub-agents in OpenClaw discover, share, and collaborate on capabilities.

### Why Claw Service Hub?

Think of it as **"npm for AI agents"** — but instead of JavaScript packages, agents share **live capabilities**.

| Problem | Solution |
|---------|----------|
| Agent A has a skill, but Agent B can't find it | 🏪 **Service Registry** — One place to publish & discover |
| Hardcoded tool integrations across agents | 🔌 **Loose Coupling** — Services talk via WebSocket |
| No way to rate or trust remote services | ⭐ **Rating System** — Quality signals for services |
| Complex multi-agent workflows | 🔄 **Tunnel Manager** — Automatic service tunneling |

### Quick Start

```bash
# One command to start the Hub server
pip install claw-service-hub && python -m server.main
```

Server listens on `ws://localhost:8765`

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
```

### Cloud Skill Registry (Option B)

In addition to local skill management, Claw Service Hub supports **Cloud-based Skill Registry** for large-scale deployments.

#### Core Advantages

| Advantage | Description |
|-----------|-------------|
| **High Scalability** | Dynamic registration & discovery, supports hundreds/thousands of tools, multi-team friendly |
| **Low Context Load** | Local only keeps router skill, dynamically pulls schema on-demand, saves tokens |
| **Strong Governance** | RBAC, call auditing, SLA/rate limiting |
| **Low Maintenance** | Server-side updates, easy grayscale release & rollback |
| **High Security** | Central API Gateway control, Zero Trust architecture |

#### Architecture

```
LLM Agent → Router Skill (Local) → Cloud Registry → Services
```

#### Comparison

| Approach | Use Case |
|----------|----------|
| **Option A (Local)** | Offline environments, <20 skills, latency-sensitive |
| **Option B (Cloud)** | >50 skills, multi-team, requires permission control |

#### Recommended: Hybrid (80% B + 20% A)

Cloud-first with local fallback for offline resilience.

---

### Project Structure

```
Claw-Service-Hub/
├── client/           # Client SDK (Provider/Consumer)
├── server/           # Hub Server
├── docs/             # Documentation (Wiki)
├── skills/           # Skill definitions
└── examples/         # Example services
```

### Features

| Feature | Status |
|---------|--------|
| Service Registration | ✅ |
| Service Discovery | ✅ |
| Heartbeat/Keep-alive | ✅ |
| WebSocket Tunnel | ✅ |
| Rating System | ✅ |
| REST API | ✅ |

### 📖 Documentation

- [Quick Start Guide](https://claw-service-hub.readthedocs.io/quickstart.html)
- [Provider Guide](https://claw-service-hub.readthedocs.io/guide/provider.html)
- [Consumer Guide](https://claw-service-hub.readthedocs.io/guide/consumer.html)
- [API Reference](https://claw-service-hub.readthedocs.io/api.html)
- [Examples](https://claw-service-hub.readthedocs.io/examples/index.html)

---

## 中文

### 概述

**Claw Service Hub** 让 OpenClaw 能够：
- 🔌 **提供服务** — 任何 subagent 都可以将自身能力发布为服务
- 🔍 **获取服务** — 发现并调用其他 subagent 提供的服务

**Claw Service Hub** 是 **AI Agent 的服务市场** — 让 OpenClaw 中的子代理能够发现、共享和协作。

把 Claw Service Hub 想象成 **"AI 代理的 npm"** — 不过共享的不是 JavaScript 包，而是**实时能力**。

### 为什么选择 Claw Service Hub?

| 痛点 | 解决方案 |
|------|----------|
| Agent A 有技能，但 Agent B 找不到 | 🏪 **服务注册中心** — 统一发布与发现 |
| 跨代理的硬编码工具集成 | 🔌 **松耦合架构** — 通过 WebSocket 通信 |
| 无法评估远程服务的可靠性 | ⭐ **评分系统** — 服务质量信号 |
| 复杂的多代理工作流 | 🔄 **隧道管理器** — 自动服务隧道 |

### 快速开始

```bash
# 一行命令启动 Hub 服务器
pip install claw-service-hub && python -m server.main
```

服务器监听 `ws://localhost:8765`

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
```

### 项目结构

```
Claw-Service-Hub/
├── client/           # 客户端 SDK (Provider/Consumer)
├── server/           # Hub 服务器
├── docs/             # 文档 (Wiki)
├── skills/           # Skill 定义
└── examples/         # 示例服务
```

### 云端 Skill Registry (方案 B)

除本地 skill 管理外，Claw Service Hub 还支持**云端 Skill Registry**，适用于大规模部署场景。

#### 核心优势

| 优势 | 描述 |
|------|------|
| **高可扩展性** | 动态注册/发现，支持数百/数千工具，天然支持多团队 |
| **低上下文负载** | 本地只保留 router skill，动态按需拉取 schema，节省 token |
| **强治理能力** | 支持 RBAC 权限控制、调用审计、SLA/限流 |
| **低维护成本** | 服务端统一更新，灰度发布/回滚容易 |
| **高安全性** | 中央 API Gateway 控制，零信任架构 |

#### 架构图

```
LLM Agent → Router Skill (本地) → Cloud Registry → Services
```

#### 对比定位

| 方案 | 适用场景 |
|------|----------|
| **方案 A (本地)** | 离线环境，<20 skills，延迟敏感 |
| **方案 B (云端)** | >50 skills，多团队，需要权限控制 |

#### 推荐架构：Hybrid (80% B + 20% A)

云端为主 + 本地 fallback，离线可用

---

### 功能列表

| 功能 | 状态 |
|------|------|
| 服务注册 | ✅ |
| 服务发现 | ✅ |
| 心跳保活 | ✅ |
| WebSocket 隧道 | ✅ |
| 评分系统 | ✅ |
| REST API | ✅ |

### 📖 文档

- [快速开始指南](https://claw-service-hub.readthedocs.io/quickstart.html)
- [Provider 指南](https://claw-service-hub.readthedocs.io/guide/provider.html)
- [Consumer 指南](https://claw-service-hub.readthedocs.io/guide/consumer.html)
- [API 参考](https://claw-service-hub.readthedocs.io/api.html)
- [使用示例](https://claw-service-hub.readthedocs.io/examples/index.html)

---

## 🤝 Contributing

感谢你对 Claw Service Hub 感兴趣！请阅读我们的 [贡献指南](./CONTRIBUTING.md) 开始参与贡献。

### 如何贡献

1. 🍴 Fork 项目
2. 🌿 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 📝 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 🚀 推送到分支 (`git push origin feature/amazing-feature`)
5. 🎁 发起 Pull Request

寻找贡献点？查看我们的 [good first issues](https://github.com/TangBoheng/Claw-Service-Hub/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)！

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

- [📖 完整文档](https://claw-service-hub.readthedocs.io)
- [💬 GitHub Discussions](https://github.com/TangBoheng/Claw-Service-Hub/discussions)
- [🐛 问题反馈](https://github.com/TangBeng/Claw-Service-Hub/issues)
- [📦 PyPI 包](https://pypi.org/project/claw-service-hub/)
- [🐙 GitHub](https://github.com/TangBoheng/Claw-Service-Hub)
- [🤖 OpenClaw](https://github.com/openclaw/openclaw)