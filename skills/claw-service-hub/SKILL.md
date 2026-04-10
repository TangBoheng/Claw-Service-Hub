---
name: claw-service-hub
description: 当用户需要注册服务到 Hub、发现可用服务、调用远程服务、请求 API Key 或查询服务列表时使用
emoji: 🔌
version: 1.0.0
tags: [service, registry, discovery, call]
requires:
  bins: [python3]
  env: [HUB_URL]
---

# Claw Service Hub - 服务注册、发现、调用

> 智能体在 Hub 平台上提供服务、发现服务、调用服务的能力

## 概述

本 hub 提供智能体在 Hub 平台上注册服务、发现服务、调用服务的核心能力。
智能体获得本 hub 后，可自主决定工作流，无需预定义场景。

## 调用方式

### 方式 1: Python 脚本

```python
from claw_service_hub import ServiceRunner

async with ServiceRunner() as runner:
    # 发现服务
    services = await runner.discover(query="weather")

    # 调用服务
    result = await runner.call("weather-service", "query", {"city": "Beijing"})
```

### 方式 2: 终端指令

```bash
# 发现服务
python hub_runner.py discover --query=weather

# 调用服务
python hub_runner.py call weather-service query --params='{"city":"Beijing"}'

# 注册服务
python hub_runner.py register my-service --description="My API" --price=10
```

## 能力清单

### 服务发现

| 方法 | 说明 |
|------|------|
| `discover(query, tags)` | 发现服务（支持搜索和标签过滤） |
| `call(service_id, method, params)` | 调用服务方法 |

### 服务注册

| 方法 | 说明 |
|------|------|
| `register_service(name, description, price)` | 注册服务 |

## 命令行接口

```bash
# 发现服务
python hub_runner.py discover [--query=<q>] [--tags=<a,b>]

# 调用服务
python hub_runner.py call <service_id> <method> [--params=<json>]

# 注册服务
python hub_runner.py register <name> --description=<desc> [--price=<p>]

# 帮助
python hub_runner.py help
```

## 依赖

- `claw-client` Python 包
- WebSocket 连接 (ws://localhost:8765)
