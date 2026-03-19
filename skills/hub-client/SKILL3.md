
name: claw-service-hub
description: 服务撮合平台 - 提供服务注册与远程调用能力（Provider / Consumer 双模式）
homepage: https://github.com/openclaw/claw-service-hub
metadata:
  openclaw:
    emoji: "🔌"
    requires:
      bins: ["python", "curl"]
      env: ["HUB_URL", "HUB_WS_URL", "WORKSPACE_DIR"]
    primaryEnv: "HUB_URL"

triggers:
  provider:
    - 提供.*服务
    - 发布.*服务
    - 把.*变成服务
    - 暴露.*接口
  consumer:
    - 有哪些服务
    - 列出服务
    - 调用.*服务
    - 使用.*服务

# Tool Service Hub (Production Skill)

## 🧠 决策入口（强约束，降低幻觉）

```text
IF 用户意图 ∈ provider:
    执行 Provider Workflow

ELSE IF 用户意图 ∈ consumer:
    执行 Consumer Workflow

ELSE:
    不使用本 skill
````

## 一、Provider（提供服务）

### ✅ 输入约束

```yaml
Inputs:
  user_intent: string
  source_type: enum[file, api, script, unknown]
  source_path: optional string
```

---

### 🔒 标准处理流程（禁止跳步）

```text
Step 1: 意图解析（必须）
  - 提取：服务名称 / 数据来源 / 能力类型
  - 若缺失 → 询问用户（禁止猜测）

Step 2: 来源判定（强约束）
  IF 包含路径:
      source_type = file
  ELSE IF 包含 URL/API:
      source_type = api
  ELSE:
      source_type = script

Step 3: 路径规范化（关键：多用户兼容）
  IF source_path 是绝对路径:
      - 替换为:
        ${WORKSPACE_DIR}/<relative_path>
      - 或 Path.home()

  示例：
    /home/t/data → ${WORKSPACE_DIR}/data
    ~/NG → Path.home() / "NG"

Step 4: 模板选择（禁止自由生成）
  file → 使用 FileServiceTemplate
  api → 使用 APIServiceTemplate
  script → 使用 ScriptServiceTemplate

Step 5: 生成服务代码（受限生成）
  必须包含：
    - LocalServiceRunner
    - register_handler
    - 明确返回 JSON

Step 6: 注册服务
  - 使用 HUB_WS_URL
  - 启动 runner.run()

Step 7: 输出结果
  - service_name
  - methods
  - 示例调用方式
```

---

### 📦 标准代码模板（强制使用）

#### 1️⃣ 文件服务模板（FileServiceTemplate）

```python
from pathlib import Path
from client.client import LocalServiceRunner

BASE_DIR = Path(
    os.getenv("WORKSPACE_DIR", str(Path.home()))
)

DATA_DIR = BASE_DIR / "data"   # 统一相对路径

async def list_files(**params):
    ext = params.get("extension", "")
    files = list(DATA_DIR.glob(f"*{ext}")) if ext else list(DATA_DIR.glob("*"))
    return {"files": [f.name for f in files if f.is_file()]}

runner = LocalServiceRunner(
    name="file-service",
    description="文件数据服务",
    tags=["file", "data"],
    hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
)

runner.register_handler("list_files", list_files)

await runner.run()
```

---

#### 2️⃣ API 服务模板（APIServiceTemplate）

```python
import aiohttp
from client.client import LocalServiceRunner

async def fetch_data(**params):
    url = params.get("url")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return {"status": resp.status}

runner = LocalServiceRunner(
    name="api-service",
    description="API 调用服务",
    tags=["api"],
    hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
)

runner.register_handler("fetch_data", fetch_data)

await runner.run()
```

---

## ❗ Provider 限制（防止幻觉）

* ❌ 不允许编造 API
* ❌ 不允许假设文件存在
* ❌ 不允许生成复杂业务逻辑
* ✅ 只允许 CRUD / fetch / list 类简单能力

---

## 二、Consumer（调用服务）

### ✅ 输入约束

```yaml
Inputs:
  service_name: optional string
  method: optional string
```

---

### 🔒 标准流程

```text
Step 1: 发现服务
  执行:
    {baseDir}/scripts/discover

Step 2: 匹配服务（必须）
  - 按 name / tags 过滤
  - 若不唯一 → 让用户选择

Step 3: 获取文档（强制）
  {baseDir}/scripts/doc <service_id>

Step 4: 调用服务
  使用 ToolServiceClient:
    - tunnel_id
    - method
    - params

Step 5: 返回结果
  - 原始 JSON
```

---

### 📦 调用模板

```python
from client.client import ToolServiceClient

client = ToolServiceClient(
    hub_url=os.getenv("HUB_WS_URL", "ws://localhost:8765")
)

await client.connect()

result = await client.call_remote_service(
    tunnel_id="xxx",
    method="method_name",
    params={}
)
```

---

## 三、路径规范（核心改进）

### ❗ 禁止写死路径

#### ❌ 错误

```python
DATA_DIR = "/home/t/NG"
```

#### ✅ 正确（生产级）

```python
BASE_DIR = Path(os.getenv("WORKSPACE_DIR", str(Path.home())))
DATA_DIR = BASE_DIR / "NG"
```

---

## ✅ 支持多用户方式

| 用户环境                 | 结果                      |
| -------------------- | ----------------------- |
| 未设置 WORKSPACE_DIR    | 使用 `~`                  |
| 设置 `/data/workspace` | 使用 `/data/workspace/NG` |

---

## 四、输出规范（必须）

```yaml
Outputs:
  service_name: string
  service_id: string
  methods: list
  usage_example: string
```

---

