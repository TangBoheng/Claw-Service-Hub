---
name: claw-service-hub
description: 服务撮合平台 - 实现 OpenClaw 节点的跨进程/跨机器服务发布、发现与调用
homepage: https://github.com/openclaw/claw-service-hub
metadata:
  openclaw:
    emoji: "🔌"
    requires:
      bins: ["python", "curl"]
      env: ["HUB_URL", "HUB_WS_URL"]
    primaryEnv: "HUB_URL"
---

# Tool Service Hub

OpenClaw 核心能力组件：支持节点作为 **Provider** 暴露本地能力，或作为 **Consumer** 消费远程资源。

---

## 角色 A：服务提供者 (Provider)

**触发指令**：
- "将 [路径/功能] 发布为服务"
- "让 [脚本/API] 可被远程调用"
- "提供一个 [名称] 服务"

**Agent 执行逻辑**：

1. **资源解析**：
   - 扫描本地路径或分析代码片段，确定输入参数 (params) 与输出结构 (return)。
2. **代码生成**：
   - 自动生成基于 `LocalServiceRunner` 的封装代码。
   - 必须包含：服务元数据、具体的 `handler` 函数、以及 `await runner.run()`。
3. **部署注册**：
   - 检查 Hub 状态，通过 WebSocket (`HUB_WS_URL`) 建立长连接并注册。
4. **交付反馈**：
   - 告知用户 `service_id`、可用方法列表及调用示例。

---

## 角色 B：服务消费者 (Consumer)

**触发指令**：
- "列出/发现可用服务"
- "查看 [service_id] 的接口文档"
- "调用 [service_id] 的 [method] 方法"

**Agent 执行逻辑**：

1. **服务发现**：执行 `discover` 脚本或请求 REST API 获取在线服务列表。
2. **协议对齐**：通过 `doc <service_id>` 获取其 `SKILL.md` 定义，确保参数类型匹配。
3. **执行调用**：使用 `ToolServiceClient` 发起远程请求并返回结果。

---

## 核心环境与路径

| 组件 | 路径 |
|------|------|
| **Client Lib** | `Claw-Service-Hub/client/client.py` |
| **Scripts** | `Claw-Service-Hub/skills/hub-client/scripts/` |

---

## 快速调用命令

| 命令 | 描述 |
|------|------|
| `discover [--tags X]` | 检索 Hub 上的活跃服务 |
| `doc <service_id>` | 获取特定服务的结构化文档 |
| `curl {HUB_URL}/api/services` | 快速查看所有服务详情 |

---

## 关键原则

1. **心跳依赖**：Provider 必须保持 Python 进程运行，断开即下线。
2. **路径优先**：在生成代码时，优先使用 `/workspace/` 下的路径引用库文件。
3. **错误冒泡**：在 `handler` 中必须捕获并返回 `{"error": "msg"}` 格式，严禁导致 Runner 崩溃。