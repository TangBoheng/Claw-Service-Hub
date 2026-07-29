---
name: claw-service-hub
description: Service registry, discovery, and remote invocation hub for AI agents. Register services, discover available services, call remote methods, request API keys, or list services. / AI 智能体的服务注册、发现与调用中心。
emoji: 🔌
version: 1.1.0
tags: [service, registry, discovery, call, hub]
homepage: https://github.com/TangBoheng/Claw-Service-Hub
source: https://github.com/TangBoheng/Claw-Service-Hub/tree/main/skills/claw-service-hub
license: MIT
requires:
  bins: [python3]
  env: [HUB_URL]
---

# Claw Service Hub - Service Registry, Discovery & Invocation

> A hub that lets agents offer, discover, and invoke services on the platform.

## Source

- Repository: <https://github.com/TangBoheng/Claw-Service-Hub>
- This skill: [`skills/claw-service-hub`](https://github.com/TangBoheng/Claw-Service-Hub/tree/main/skills/claw-service-hub)

## Overview / 概述

This hub provides the core ability for an agent to **register**, **discover**, and **call** services on the Hub platform. Once an agent owns this hub, it can decide its own workflow on the fly - no predefined scenarios required.

本 hub 提供智能体在 Hub 平台上注册服务、发现服务、调用服务的核心能力。智能体获得本 hub 后，可自主决定工作流，无需预定义场景。

## Usage / 调用方式

### Option 1: Python

```python
from claw_service_hub import ServiceRunner

async with ServiceRunner() as runner:
    # Discover services
    services = await runner.discover(query="weather")

    # Call a service
    result = await runner.call("weather-service", "query", {"city": "Beijing"})
```

### Option 2: CLI

```bash
# Discover services
python hub_runner.py discover --query=weather

# Call a service
python hub_runner.py call weather-service query --params='{"city":"Beijing"}'

# Register a service
python hub_runner.py register my-service --description="My API" --price=10
```

## Capabilities / 能力清单

### Service discovery

| Method | Description |
|--------|-------------|
| `discover(query, tags)` | Discover services (search + tag filter) |
| `call(service_id, method, params)` | Invoke a service method |

### Service registration

| Method | Description |
|--------|-------------|
| `register_service(name, description, price)` | Register a service |

## CLI reference / 命令行接口

```bash
# Discover services
python hub_runner.py discover [--query=<q>] [--tags=<a,b>]

# Call a service
python hub_runner.py call <service_id> <method> [--params=<json>]

# Register a service
python hub_runner.py register <name> --description=<desc> [--price=<p>]

# Help
python hub_runner.py help
```

## Dependencies / 依赖

- `claw-client` Python package
- WebSocket connection (`ws://localhost:8765`)
