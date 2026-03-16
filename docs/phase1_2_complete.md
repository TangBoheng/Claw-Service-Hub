# Phase 1-2 实现完成

## 实现内容

### 1. 标准化的 SkillMetadata 格式 (server/registry.py)

**新增字段**：
- `emoji` - 服务图标/表情符号
- `requires` - 依赖要求 `{"bins": [...], "env": [...]}`

**新增方法**：
- `to_metadata_dict()` - 返回轻量级 metadata，用于广播和发现

**示例**：
```python
service = ToolService(
    id="svc-123",
    name="csv-processor",
    description="Process CSV files",
    emoji="📊",
    requires={"bins": ["python"], "env": []},
    tags=["csv", "data"]
)

# 获取轻量级 metadata（用于广播）
metadata = service.to_metadata_dict()
# {'id': 'svc-123', 'name': 'csv-processor', 'emoji': '📊', ...}
```

### 2. skill.md 存储与获取 (server/registry.py)

**ServiceRegistry 新增**：
- `_skill_docs: Dict[str, str]` - 存储 service_id -> skill.md 内容
- `register(service, skill_doc=None)` - 支持传入 skill_doc
- `get_skill_doc(service_id)` - 获取完整 skill.md
- `list_all_metadata()` - 获取所有服务的轻量级 metadata
- `unregister()` - 同时清理 skill_doc

**示例**：
```python
registry = ServiceRegistry()
service_id = await registry.register(service, skill_doc_content)

# 获取完整文档
full_doc = registry.get_skill_doc(service_id)

# 获取轻量 metadata（用于广播）
metadata_list = registry.list_all_metadata()
```

### 3. Client 读取和发送 skill.md (client/client.py)

**ToolServiceClient 新增**：
- `skill_dir` 参数 - 指定包含 SKILL.md 的目录
- `skill_doc` 属性 - 自动加载的 SKILL.md 内容
- `_load_skill_doc()` - 从磁盘读取 SKILL.md

**注册时自动发送**：
```python
client = ToolServiceClient(
    name="csv-processor",
    skill_dir="./examples/csv-processor-skill"  # 自动加载 SKILL.md
)
await client.connect()  # 自动发送 skill_doc
```

### 4. 服务端广播轻量级 metadata (server/main.py)

**修改**：
- `_handle_register()` - 处理包含 skill_doc 的注册消息
- `_broadcast_service_list()` - 改为 `list_all_metadata()`，仅广播轻量数据
- 消息类型从 `service_list` 改为 `metadata_list`

## 文件变更

| 文件 | 变更 |
|------|------|
| `server/registry.py` | 新增 SkillMetadata 字段，skill_doc 存储 |
| `client/client.py` | 新增 skill_dir 参数，自动加载 SKILL.md |
| `server/main.py` | 处理 skill_doc，广播轻量级 metadata |

## 示例

### 创建一个带有 skill.md 的工具服务

```python
# examples/csv-processor-skill/run.py
from client.client import ToolServiceClient

client = ToolServiceClient(
    name="csv-processor",
    description="Process CSV files",
    emoji="📊",
    requires={"bins": ["python"], "env": []},
    skill_dir="./examples/csv-processor-skill"  # 包含 SKILL.md
)

await client.connect("ws://localhost:8765")
# 会自动发送 SKILL.md 内容到服务端
```

### SKILL.md 格式示例

```markdown
---
name: csv-processor
description: Process and analyze CSV files
emoji: 📊
version: 1.0.0
tags: [csv, data]
requires:
  bins: [python]
  env: []
---

# CSV Processor

Full documentation here...
```

## 架构图

```
┌─────────────────────────────────────────────────────┐
│                    云端 Server                       │
│  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │ Service     │  │ _skill_docs: Dict[str, str] │  │
│  │ Registry    │  │ - service_id -> skill.md    │  │
│  │ (metadata)  │  │ - 完整文档存储               │  │
│  └─────────────┘  └─────────────────────────────┘  │
│        │                                            │
│        ▼ to_metadata_dict()                         │
│  WebSocket 广播轻量 metadata                         │
└─────────────────────────────────────────────────────┘
           ▲
           │ WebSocket (register + skill_doc)
    ┌──────┴──────┐
    │ OpenClaw    │
    │ Skill/Client│
    │ - SKILL.md  │
    │ - metadata  │
    └─────────────┘
```

## 测试

运行测试：
```bash
python tests/test_phase1_2.py
```

所有测试通过 ✅

## 下一步

Phase 3-4（可选）：
- 增强过滤功能（按 requires 过滤）
- 添加 HTTP API 获取 skill.md
- OpenClaw Skill 适配器
