# Add claw-service-hub Skill

## Description

This PR adds the `claw-service-hub` skill to the official OpenClaw skills repository.

## Skill Overview

- **Name**: claw-service-hub
- **Description**: Service marketplace: publish data as services, consume hub services
- **Emoji**: 🔌

## Features

- **Provider Mode**: Publish local data/capabilities as services for other subagents
- **Consumer Mode**: Discover and call services on the Hub
- **Authorization**: Optional key-based access control with time/count limits

## Files to Add

Create directory: `claw-service-hub/` in the skills root

Add file: `claw-service-hub/SKILL.md` (content below)

## SKILL.md Content

```markdown
---
name: claw-service-hub
description: "Service marketplace: publish data as services, consume hub services"
homepage: https://github.com/openclaw/claw-service-hub
metadata:
  openclaw:
    emoji: "🔌"
    requires:
      bins: ["python", "pip"]
      env: ["HUB_WS_URL"]
      pip: ["websockets", "aiohttp"]
    primaryEnv: "HUB_WS_URL"
    install:
      - id: pip
        kind: pip
        package: claw-service-hub
        label: "Install via pip"
---

triggers:
  provider:
    - provide.*service
    - publish.*service
    - expose.*service
    - create.*service
    - make.*service
    - implement.*service
  consumer:
    - what services
    - list services
    - call.*service
    - use.*service
    - query.*data
    - fetch.*data

# Claw Service Hub Skill

## Overview

Enables subagents to:
1. **Provider Mode**: Publish local data/capabilities as services for other subagents to call
2. **Consumer Mode**: Discover and call services on the Hub

---

## 1. Publishing Services as a Provider

### Complete Code Template

```python
import asyncio
import os
import sys
from pathlib import Path

# === 1. Setup path ===
WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', '/home/t/.openclaw/workspace-subagentX')
sys.path.insert(0, WORKSPACE_DIR)

from client.client import LocalServiceRunner

# === 2. Define your service capability ===

async def your_method(**params):
    """
    Service method
    params: Parameters passed by the caller
    Must return a dict
    """
    # Your business logic here
    result = {"status": "ok", "data": "..."}
    return result

# === 3. Start the service ===

async def main():
    runner = LocalServiceRunner(
        name="your-service-name",      # Service name (English, no spaces)
        description="Service description",  # English description
        hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
    )
    
    # Register methods (can register multiple)
    runner.register_handler("your_method", your_method)
    
    print(f"🚀 Starting service...")
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2. Calling Services as a Consumer

### Complete Code Template

```python
import asyncio
import os
import sys

WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', '/home/t/.openclaw/workspace-subagentX')
sys.path.insert(0, WORKSPACE_DIR)

from client.skill_client import SkillQueryClient

async def main():
    # 1. Connect to Hub
    client = SkillQueryClient(
        hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
    )
    await client.connect()
    
    # 2. Discover services
    services = await client.discover()
    print(f"Discovered {len(services)} services")
    
    # 3. Find target service (filter by name)
    target = None
    target_name = "weather-service"  # Replace with your target service name
    for s in services:
        if target_name in s.get("name", ""):
            target = s
            break
    
    if not target:
        print(f"Service not found: {target_name}")
        return
    
    skill_id = target.get("skill_id")
    print(f"Using service: {target.get('name')}, skill_id: {skill_id}")
    
    # 4. Call the service
    result = await client.call_service(
        service_id=skill_id,
        method="your_method",      # Method name
        params={"key": "value"}    # Parameters
    )
    
    print(f"Result: {result}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. Environment Configuration

### Install Dependencies

```bash
pip install websockets aiohttp
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| HUB_WS_URL | ws://localhost:8765 | Hub WebSocket address |
| WORKSPACE_DIR | /home/t/.../workspace-subagentX | Working directory |

---

## 4. Minimal Examples

### Provider (5 lines)

```python
import asyncio, os, sys
sys.path.insert(0, os.getenv('WORKSPACE_DIR','.'))
from client.client import LocalServiceRunner

async def hello(**p): return {"msg":"Hello!"}
r = LocalServiceRunner("demo","Demo Service",os.getenv("HUB_WS_URL","ws://localhost:8765"))
r.register_handler("hello", hello)
asyncio.run(r.run())
```

### Consumer (6 lines)

```python
import asyncio, os, sys
sys.path.insert(0, os.getenv('WORKSPACE_DIR','.'))
from client.skill_client import SkillQueryClient

async def main():
    c = SkillQueryClient()
    await c.connect()
    print([s.get("name") for s in await c.discover()])
    await c.disconnect()
asyncio.run(main())
```

---

## License

MIT License
```

## Alternative: Use GitHub CLI

```bash
# Fork and clone
gh repo fork openclaw/skills --clone
cd skills

# Create branch
git checkout -b add-claw-service-hub

# Create directory and add file
mkdir -p claw-service-hub
# Add SKILL.md content...

# Commit and push
git add .
git commit -m "Add claw-service-hub skill"
git push -u origin add-claw-service-hub

# Create PR
gh pr create --title "Add claw-service-hub skill" --body "@openclaw/maintainers Please review"
```