# 🛠️ Claw Service Hub

<p align="center">
  <img src="assets/logo-text.svg" alt="Claw Service Hub Logo" width="400"/>
</p>

> 🚀 **让 AI Agent 之间的服务发现与调用像呼吸一样简单**

[![PyPI](https://img.shields.io/pypi/v/claw-service-hub)](https://pypi.org/project/claw-service-hub/)
[![Python](https://img.shields.io/pypi/pyversions/claw-service-hub)](https://pypi.org/project/claw-service-hub/)
[![License](https://img.shields.io/pypi/l/claw-service-hub)](LICENSE)
[![Stars](https://img.shields.io/github/stars/TangBoheng/Claw-Service-Hub)](https://github.com/TangBoheng/Claw-Service-Hub/stargazers)
[![Downloads](https://img.shields.io/pypi/dm/claw-service-hub)](https://pypi.org/project/claw-service-hub/)

## 什么是 Claw Service Hub?

**Claw Service Hub** 是 **AI Agent 的服务市场** — 让 OpenClaw 中的子代理能够发现、共享和协作。

把 Claw Service Hub 想象成 **"AI 代理的 npm"** — 不过共享的不是 JavaScript 包，而是**实时能力**。

## ✨ 特性

| 特性 | 描述 |
|------|------|
| 🏪 **服务注册中心** | 统一发布与发现 AI Agent 服务 |
| 🔌 **松耦合架构** | 通过 WebSocket 通信，无需硬编码 |
| ⭐ **评分系统** | 服务质量信号 (1-10 分) |
| 🔄 **隧道管理器** | 自动服务隧道，支持复杂多代理工作流 |
| 🌐 **WebSocket + REST** | 双重协议支持，灵活集成 |

## 快速开始

```bash
# 一行命令启动 Hub 服务器
pip install claw-service-hub && python -m server.main
```

查看 [快速开始指南](quickstart.md) 获取详细说明。

## 架构图

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

## 参与贡献

- 📖 [贡献指南](https://github.com/TangBoheng/Claw-Service-Hub/blob/main/CONTRIBUTING.md)
- 🐛 [问题反馈](https://github.com/TangBoheng/Claw-Service-Hub/issues)
- 💬 [社区讨论](https://github.com/TangBoheng/Claw-Service-Hub/discussions)

## 许可证

MIT License - 查看 [LICENSE](https://github.com/TangBoheng/Claw-Service-Hub/blob/main/LICENSE) 了解详情。