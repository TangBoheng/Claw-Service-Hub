---
name: claw-service-hub
description: Claw-Service-Hub 客户端。提供服务注册和远程服务调用能力。
homepage: https://github.com/openclaw/claw-service-hub
metadata:
  clawdbot:
    emoji: "🔌"
    requires:
      bins: ["curl", "python"]
      env: ["HUB_URL"]
    primaryEnv: "HUB_URL"
---

# Hub Client

Claw-Service-Hub 服务撮合客户端。

**两大能力：**
1. **提供服务** - 将本地工具/数据注册为远程可调用服务
2. **调用服务** - 发现并调用其他节点提供的服务

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HUB_URL` | Hub HTTP 地址 | `http://localhost:3765` |
| `HUB_WS_URL` | Hub WebSocket 地址 | `ws://localhost:8765` |

---

# 第一部分：提供服务

## 1. 创建服务

### 1.1 定义服务元数据

```
name: "my-service"           # 服务名称
description: "服务描述"       # 功能说明
tags: ["tag1", "tag2"]       # 标签，用于发现
emoji: "🔧"                  # 图标
```

### 1.2 定义接口文档 (SKILL.md)

创建一个 skill 目录，包含 `SKILL.md` 文件：

```markdown
# My Service

## 功能说明
xxx

## 可调用方法

### method_name
- 描述: xxx
- 参数: { "param1": "type" }
- 返回: { "result": "..." }
```

---

## 2. 注册服务

使用 Python 客户端注册服务：

```python
from client.client import LocalServiceRunner

async def my_handler(**params):
    # 处理逻辑
    return {"result": "..."}

runner = LocalServiceRunner(
    name="my-service",
    description="服务描述",
    tags=["tag1"],
    skill_dir="/path/to/skill"  # 包含 SKILL.md
)
runner.register_handler("method_name", my_handler)
await runner.run()
```

---

# 第二部分：调用服务

## 1. 发现服务

```bash
# 列出所有服务
{baseDir}/scripts/discover

# 按标签过滤
{baseDir}/scripts/discover --tags image,data
```

响应示例：
```json
[
  {
    "id": "abc123",
    "name": "image-service",
    "description": "图片处理服务",
    "tags": ["image"],
    "emoji": "🖼️",
    "status": "online",
    "tunnel_id": "xxx-xxx-xxx"
  }
]
```

---

## 2. 获取服务文档

```bash
{baseDir}/scripts/doc <service_id>
```

返回服务的完整接口文档，包含：
- 功能描述
- 可调用方法列表
- 参数定义
- 返回格式

---

## 3. 调用服务

### Python 方式

```python
from client.client import ToolServiceClient

client = ToolServiceClient(hub_url="ws://localhost:8765")
await client.connect()

result = await client.call_remote_service(
    tunnel_id="xxx-xxx-xxx",
    method="method_name",
    params={"param1": "value"}
)
```

---

# 完整流程

## 作为服务提供者

```
1. 定义服务：编写 SKILL.md + 实现处理函数
2. 注册服务：使用 LocalServiceRunner 连接 Hub
3. 运行服务：心跳保活 + 处理请求
```

## 作为服务消费者

```
1. 发现服务：discover 获取服务列表
2. 获取文档：doc <service_id> 了解接口
3. 调用服务：Python 客户端调用
```

---

## 相关命令

| 命令 | 说明 |
|------|------|
| `{baseDir}/scripts/discover` | 列出所有服务 |
| `{baseDir}/scripts/discover --tags <tags>` | 按标签过滤 |
| `{baseDir}/scripts/doc <service_id>` | 获取服务文档 |