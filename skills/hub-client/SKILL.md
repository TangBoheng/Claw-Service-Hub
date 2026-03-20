name: claw-service-hub
description: 服务撮合平台 - 将任意数据源发布为服务，或调用 Hub 上的服务
homepage: https://github.com/openclaw/claw-service-hub
metadata:
  openclaw:
    emoji: "🔌"
    requires:
      bins: ["python", "pip"]
      env: ["HUB_WS_URL"]
      pip: ["websockets", "aiohttp"]
    primaryEnv: "HUB_WS_URL"

triggers:
  provider:
    - 提供.*服务
    - 发布.*服务
    - 把.*变成服务
    - 暴露.*接口
    - 启动.*服务
    - 做.*服务
    - 实现.*服务
  consumer:
    - 有哪些服务
    - 列出服务
    - 调用.*服务
    - 使用.*服务
    - 查询.*数据
    - 获取.*数据

# Tool Service Hub Skill

## 概述

让 subagent 能够：
1. **Provider 模式**：将本地数据/能力发布为服务，供其他 subagent 调用
2. **Consumer 模式**：发现 Hub 上的服务并调用

---

## 一、作为 Provider 发布服务

### 完整代码模板

```python
import asyncio
import os
import sys
from pathlib import Path

# === 1. 设置路径 ===
WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', '/home/t/.openclaw/workspace-subagentX')
sys.path.insert(0, WORKSPACE_DIR)

from client.client import LocalServiceRunner

# === 2. 定义你的服务能力 ===

async def your_method(**params):
    """
    服务方法
    params: 接收调用方传入的参数
    必须返回 dict 类型
    """
    # 你的业务逻辑
    result = {"status": "ok", "data": "..."}
    return result

# === 3. 启动服务 ===

async def main():
    runner = LocalServiceRunner(
        name="your-service-name",      # 服务名（英文，无空格）
        description="服务描述",           # 中文描述
        hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
    )
    
    # 注册方法（可以注册多个）
    runner.register_handler("your_method", your_method)
    
    print(f"🚀 启动服务...")
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 二、作为 Consumer 调用服务

### 完整代码模板

```python
import asyncio
import os
import sys

WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', '/home/t/.openclaw/workspace-subagentX')
sys.path.insert(0, WORKSPACE_DIR)

from client.skill_client import SkillQueryClient

async def main():
    # 1. 连接 Hub
    client = SkillQueryClient(
        hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
    )
    await client.connect()
    
    # 2. 发现服务
    services = await client.discover()
    print(f"发现 {len(services)} 个服务")
    
    # 3. 找到目标服务（按名称过滤）
    target = None
    target_name = "weather-service"  # 替换为你的目标服务名
    for s in services:
        if target_name in s.get("name", ""):
            target = s
            break
    
    if not target:
        print(f"未找到服务: {target_name}")
        return
    
    skill_id = target.get("skill_id")
    print(f"使用服务: {target.get('name')}, skill_id: {skill_id}")
    
    # 4. 调用服务
    result = await client.call_service(
        service_id=skill_id,
        method="your_method",      # 方法名
        params={"key": "value"}    # 参数
    )
    
    print(f"结果: {result}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 三、常见数据源示例

### 3.1 文件数据服务

```python
from pathlib import Path

DATA_DIR = Path("/path/to/data")  # 修改为实际目录

async def list_files(**params):
    ext = params.get("extension", "")
    pattern = f"*{ext}" if ext else "*"
    files = [f.name for f in DATA_DIR.glob(pattern) if f.is_file()]
    return {"files": files[:50], "total": len(files)}

async def read_file(**params):
    filename = params.get("filename")
    if not filename:
        return {"error": "filename is required"}
    
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return {"error": f"File not found: {filename}"}
    
    # 文本文件直接读取
    if filepath.suffix == '.txt':
        return {"content": filepath.read_text()[:1000]}
    
    # 其他文件返回信息
    return {"filename": filename, "size": filepath.stat().st_size}
```

### 3.2 API 数据服务

```python
import aiohttp

async def fetch_data(**params):
    url = params.get("url")
    if not url:
        return {"error": "url is required"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(10)) as resp:
                data = await resp.json()
        return {"status": resp.status, "data": data}
    except Exception as e:
        return {"error": str(e)}
```

### 3.3 天气服务 (wttr.in)

```python
import aiohttp

async def get_weather(**params):
    city = params.get("city", "Shanghai")
    url = f"https://wttr.in/{city}?format=j1"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(10)) as resp:
                data = await resp.json()
        
        # 注意：wttr.in 返回结构是 data.current_condition
        c = data.get("data", {}).get("current_condition", [{}])[0]
        return {
            "city": city,
            "temp": int(c.get("temp_C") or 0),
            "condition": c.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            "humidity": c.get("humidity")
        }
    except Exception as e:
        return {"error": str(e)}
```

---

## 四、工作流示例

### 组合多个服务

```python
async def workflow():
    """组合多个服务的完整工作流"""
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    services = await client.discover()
    
    # 找到所需服务
    weather = next((s for s in services if "weather" in s.get("name", "")), None)
    images = next((s for s in services if "image" in s.get("name", "")), None)
    
    results = {}
    
    # 调用天气服务
    if weather:
        w = await client.call_service(weather.get("skill_id"), "get_weather", {"city": "Shanghai"})
        results["weather"] = w.get("result", {})
    
    # 调用图片服务
    if images:
        i = await client.call_service(images.get("skill_id"), "list_images", {"limit": 10})
        results["images"] = i.get("result", {})
    
    await client.disconnect()
    return results
```

---

## 五、环境配置

### 安装依赖

```bash
pip install websockets aiohttp
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| HUB_WS_URL | ws://localhost:8765 | Hub 地址 |
| WORKSPACE_DIR | /home/t/.../workspace-subagentX | 工作目录 |

### 启动 Hub Server（可选）

```bash
cd Claw-Service-Hub
python -m server.main

# WebSocket: ws://0.0.0.0:8765
# REST API: http://0.0.0.0:3765
```

---

## 六、故障排查

### 问题 1: ImportError

**错误**: `ModuleNotFoundError: No module named 'client'`

**解决**: 正确设置 sys.path
```python
import os
import sys
WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', '/home/t/.openclaw/workspace-subagentX')
sys.path.insert(0, WORKSPACE_DIR)
from client.client import LocalServiceRunner
```

### 问题 2: 服务注册成功但无法调用

**检查**:
1. Provider 进程是否还在运行
2. 方法名是否正确（大小写敏感）
3. 参数格式是否正确

### 问题 3: API 返回 None

**常见原因**: 数据结构解析错误

**解决**: 先打印原始数据，确认结构
```python
async def get_data(**params):
    url = params.get("url")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
    print(f"原始数据: {data}")  # 添加这行调试
    # 然后根据实际结构解析
    return {"data": data}
```

### 问题 4: 找不到服务

**解决**: 先列出所有服务
```python
services = await client.discover()
for s in services:
    print(f"{s.get('name')}: {s.get('skill_id')}")
```

### 问题 5: 返回值必须是 dict

**错误**: `TypeError: ... got an unexpected keyword argument`

**解决**: handler 必须返回 dict
```python
async def wrong():  # 错误
    return "string"

async def right(**params):  # 正确
    return {"result": "value"}
```

### 问题 6: 返回值被包装在 'result' 中

**现象**: 调用服务后返回 `{'result': {'actual_data': '...'}}`

**说明**: Hub 会将 handler 返回的 dict 包装在 'result' 字段中

**解决**: 直接使用返回值，或根据需要提取
```python
result = await client.call_service(service_id, "method", params)
# result = {'result': {'temp': 25, 'city': 'Beijing'}}

# 方式1: 直接使用（推荐）
data = result  # 已经是解包后的数据

# 方式2: 如果需要明确提取
if 'result' in result:
    data = result['result']
```

---

## 七、最小示例

### Provider (5行)

```python
import asyncio, os, sys
sys.path.insert(0, os.getenv('WORKSPACE_DIR','.'))
from client.client import LocalServiceRunner

async def hello(**p): return {"msg":"Hello!"}
r = LocalServiceRunner("demo","演示",os.getenv("HUB_WS_URL","ws://localhost:8765"))
r.register_handler("hello", hello)
asyncio.run(r.run())
```

### Consumer (6行)

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

## 八、文件结构

```
Claw-Service-Hub/
├── client/
│   ├── client.py           # LocalServiceRunner, ToolServiceClient
│   ├── skill_client.py     # SkillQueryClient
│   └── management_client.py
├── skills/
│   └── hub-client/
│       └── SKILL.md        # 本文件
└── server/
    └── main.py             # Hub Server
```

---

## 九、发布流程

1. 确保 Hub Server 运行中 (`ws://localhost:8765`)
2. Provider: 运行 `python your_service.py` 注册服务
3. Consumer: 连接 Hub 发现服务
4. Consumer: 调用服务获取结果

---

## 十、Key 授权机制 (可选)

### 10.1 概述

可选的 Key 授权机制，用于控制服务的访问权限。

**功能**：
- 时间维度：Key 有效期（支持 Provider 自定义）
- 次数维度：最大调用次数（支持 Provider 自定义）
- 双验证：Provider 自主管理 + Hub 验证

### 10.2 Provider 端 - 设置生命周期策略

```python
from client.client import LocalServiceRunner

# 创建服务
runner = LocalServiceRunner(
    name="my-protected-service",
    description="需要授权的服务",
    hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
)

# 设置默认生命周期策略
runner.set_lifecycle_policy(
    duration_seconds=3600,  # 默认1小时有效
    max_calls=100           # 默认100次调用
)

# 设置自定义策略（可选）
runner.set_custom_policy(
    condition="premium",     # 策略名称
    duration_seconds=86400,  # 24小时
    max_calls=1000           # 1000次
)

# 注册方法
async def get_data(**params):
    return {"data": "secret data"}

runner.register_handler("get_data", get_data)

# 启动服务
print(f"🚀 启动授权服务...")
await runner.run()
```

### 10.3 Consumer 端 - 请求 Key 并调用

```python
from client.skill_client import SkillQueryClient

async def main():
    client = SkillQueryClient(
        hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
    )
    await client.connect()
    
    # 发现服务
    services = await client.discover()
    target = next((s for s in services if "protected" in s.get("name", "")), None)
    
    if not target:
        print("未找到服务")
        return
    
    service_id = target.get("skill_id")
    
    # 方法1: 直接调用（如果服务不需要 Key）
    # result = await client.call_service(service_id, "get_data", {})
    
    # 方法2: 先请求 Key，再调用（推荐）
    key_info = await client.request_key(
        service_id=service_id,
        purpose="日常数据查询"
    )
    
    if key_info.get("success"):
        key = key_info["key"]
        lifecycle = key_info["lifecycle"]
        
        print(f"✅ Key 获取成功")
        print(f"   Key: {key[:20]}...")
        print(f"   有效期: {lifecycle.get('remaining_time')} 秒")
        print(f"   剩余次数: {lifecycle.get('remaining_calls')} 次")
        
        # 用 Key 调用服务
        result = await client.call_service(
            service_id=service_id,
            method="get_data",
            params={},
            key=key  # 携带 Key
        )
        
        print(f"📥 结果: {result}")
    else:
        print(f"❌ Key 获取失败: {key_info.get('reason')}")
    
    await client.disconnect()

asyncio.run(main())
```

### 10.4 Key 验证失败的处理

```python
async def call_with_fallback(client, service_id, method, params):
    """带自动重试的调用"""
    
    # 先尝试不带 Key
    result = await client.call_service(service_id, method, params)
    
    # 检查是否需要 Key
    if result.get("error") and "Key" in result.get("error", ""):
        print("需要 Key，请求授权...")
        
        key_info = await client.request_key(service_id, "自动申请")
        if key_info.get("success"):
            key = key_info["key"]
            # 重试带 Key
            result = await client.call_service(
                service_id, method, params, key=key
            )
    
    return result
```

### 10.5 消息协议

| 消息类型 | 方向 | 说明 |
|---------|------|------|
| lifecycle_policy | Provider→Hub | 注册生命周期策略 |
| key_request | Consumer→Hub→Provider | 请求 Key |
| key_response | Provider→Hub→Consumer | 返回 Key（批准/拒绝） |
| key_revoke | Provider→Hub | 撤销 Key |
| call_service (带 key) | Consumer→Hub | 带 Key 调用服务 |

### 10.6 生命周期参数

```python
# Provider 注册策略
{
    "duration_seconds": 3600,    # 有效时长（秒）
    "max_calls": 100,             # 最大调用次数
    "custom_policies": {         # 可选：自定义策略
        "premium": {
            "duration_seconds": 86400,
            "max_calls": 1000
        }
    }
}

# Key 验证结果
{
    "valid": True,
    "key": "key_abc123...",
    "lifecycle": {
        "expires_at": "2026-03-20T03:47:00Z",
        "max_calls": 100,
        "call_count": 5,
        "remaining_calls": 95,
        "remaining_time": 3200
    }
}
```

### 10.7 subagent 使用建议

**对于 Provider（服务发布者）**：
1. 如果服务需要授权，在 `set_lifecycle_policy` 设置合理的限制
2. 建议默认 `max_calls=100`, `duration_seconds=3600`
3. 可以为不同 consumer 设置不同策略

**对于 Consumer（服务调用者）**：
1. 先尝试直接调用，如果失败再申请 Key
2. 保存 Key 避免重复申请
3. 检查 `lifecycle.get('remaining_calls')` 避免次数用尽
4. 注意 `lifecycle.get('remaining_time')` 及时续期