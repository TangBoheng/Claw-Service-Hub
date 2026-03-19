---
name: claw-service-hub
description: 服务撮合平台 - 发布、发现、调用远程服务
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

服务撮合平台 - 让 OpenClaw 节点可以发布和调用远程服务

---

## 两种角色

### 1. 服务提供者 (Provider)

**触发条件**：用户说以下任何一种：
- "提供...服务"、"发布...为服务"
- "把 XX 变成可调用服务"、"让 XX 可以被远程调用"
- "把本地 XX 发布到 Hub"
- "创建一个 XX 服务"

**Agent 工作流**：

```
Step 1: 理解需求
  - 用户要提供什么服务？数据？API？脚本？
  - 服务名称是什么？
  - 提供哪些方法/能力？

Step 2: 分析来源
  - 本地文件/目录 → 扫描并理解数据结构
  - API/数据库 → 分析接口或 Schema
  - 脚本/命令 → 理解输出格式
  - 实时数据 → 确定数据获取方式

Step 3: 生成服务代码
  - 使用 LocalServiceRunner 包装服务和处理函数
  - 定义服务元数据 (name, description, tags)
  - 实现处理方法 (handler)

Step 4: 注册并启动
  - 连接到 Hub (ws://localhost:8765)
  - 注册服务 (自动获取 service_id)
  - 保持心跳

Step 5: 返回结果
  - 服务名称
  - 服务 ID
  - 可用方法列表
  - 如何调用
```

**关键原则**：
- 不局限于"数据服务"，根据需求灵活处理
- 让模型自己判断如何封装服务和生成代码
- 优先使用 Python 的 LocalServiceRunner

---

### 2. 服务消费者 (Consumer)

**触发条件**：用户说以下任何一种：
- "有哪些服务"、"列出服务"、"查看可用服务"
- "发现服务"
- "调用 XX 服务的 XX 方法"
- "请求 XX 服务"

**Agent 工作流**：

```
Step 1: 发现服务
  - 调用 discover 或直接请求 Hub API
  - 列出所有可用服务或按标签过滤

Step 2: (可选) 获取服务文档
  - 调用 doc <service_id> 获取接口文档
  - 了解可用的方法和参数

Step 3: 调用服务
  - 使用 ToolServiceClient 或 HTTP API 调用
  - 传入方法名和参数
  - 返回结果给用户
```

---

## 代码位置

| 组件 | 路径 |
|------|------|
| Hub Server | `/home/t/.openclaw/workspace/Claw-Service-Hub/server/main.py` |
| Client Lib | `/home/t/.openclaw/workspace/Claw-Service-Hub/client/client.py` |
| Skill Scripts | `/home/t/.openclaw/workspace/Claw-Service-Hub/skills/hub-client/scripts/` |

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HUB_URL` | Hub HTTP 地址 | `http://localhost:3765` |
| `HUB_WS_URL` | Hub WebSocket 地址 | `ws://localhost:8765` |

---

## 服务代码示例

### 示例 1: 发布本地数据服务

```python
import asyncio
import json
import os
from pathlib import Path

# 假设用户要把 ~/NG/ 目录的数据发布为服务
DATA_DIR = Path.home() / "NG"

async def get_files(**params):
    """列出目录下的文件"""
    ext = params.get("extension", "")
    files = list(DATA_DIR.glob(f"*{ext}")) if ext else list(DATA_DIR.glob("*"))
    return {
        "files": [f.name for f in files if f.is_file()],
        "count": len(files)
    }

async def read_file(**params):
    """读取指定文件内容"""
    filename = params.get("filename")
    if not filename:
        return {"error": "filename is required"}
    
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return {"error": f"File not found: {filename}"}
    
    content = filepath.read_text(errors="ignore")
    return {"filename": filename, "content": content[:1000]}

# 创建服务
from client.client import LocalServiceRunner

runner = LocalServiceRunner(
    name="ng-data-service",
    description="本地 NG 目录的数据服务",
    tags=["data", "local", "files"],
    hub_url="ws://localhost:8765"
)

runner.register_handler("get_files", get_files)
runner.register_handler("read_file", read_file)

await runner.run()
```

### 示例 2: 发布 API 服务

```python
import aiohttp

async def fetch_weather(**params):
    """获取天气"""
    city = params.get("city", "beijing")
    # 调用外部 API...
    return {"city": city, "temp": 20, "weather": "sunny"}

runner = LocalServiceRunner(
    name="weather-service",
    description="天气查询服务",
    tags=["api", "weather"],
    hub_url="ws://localhost:8765"
)

runner.register_handler("fetch_weather", fetch_weather)
await runner.run()
```

---

## 脚本命令

| 命令 | 说明 |
|------|------|
| `{baseDir}/scripts/discover` | 列出所有可用服务 |
| `{baseDir}/scripts/discover --tags tag1,tag2` | 按标签过滤 |
| `{baseDir}/scripts/doc <service_id>` | 获取服务接口文档 |

---

## REST API

Hub 服务还提供 HTTP REST API：

```bash
# 列出所有服务
curl http://localhost:3765/api/services

# 获取服务详情
curl http://localhost:3765/api/services/{service_id}

# 列出隧道
curl http://localhost:3765/api/tunnels
```

---

## 示例对话

| 用户说 | Agent 应该做什么 |
|--------|-----------------|
| "把 ~/NG/ 的数据发布为服务" | 扫描 ~/NG/ → 生成服务代码 → 启动并注册 → 返回服务信息 |
| "提供天气查询服务" | 生成天气服务代码 → 启动 → 注册 → 返回 |
| "有哪些服务可用" | 调用 discover 或 HTTP API → 格式化展示结果 |
| "调用 image-service 的 resize 方法" | 查找服务 → 获取文档 → 调用 call_service → 返回结果 |
| "查看 all-data 服务的接口" | 调用 doc all-data → 展示接口文档 |

---

## 注意事项

1. **先启动 Hub Server**：如果是第一次使用，先确保 Hub 在运行
   ```bash
   cd /home/t/.openclaw/workspace/Claw-Service-Hub
   python -m server.main
   ```

2. **服务需要持续运行**：提供者需要在后台持续运行，否则服务会因心跳超时而下线

3. **处理错误**：实现 handler 时注意异常处理，返回有意义的错误信息