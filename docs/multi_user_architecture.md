# 多用户数据服务共享架构

## 概述

本架构实现了一个 **管理-执行分离** 的服务撮合系统，支持多用户（subagent）场景下的数据服务注册、发现和调用。

## 核心概念

### 角色定义

| 角色 | 职责 | 示例 |
|------|------|------|
| **云端服务器** | 服务撮合平台 | 注册中心、隧道管理、服务发现 |
| **subagent1 (服务提供者)** | 纯管理型客户端 | 注册服务，管理生命周期，不执行业务 |
| **subagent2 (服务消费者)** | Skill 查询客户端 | 查询服务，建立通道，调用服务 |
| **外部执行器** | 实际业务服务 | n8n webhook、python 服务等 |

### 执行模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `local` | 客户端本地执行请求 | 单节点既注册又执行 |
| `external` | 转发到外部端点执行 | subagent1 只管理，外部服务执行 |
| `remote` | 远程代理执行 | 未来扩展 |

## 消息流程

### 服务注册流程 (subagent1)

```
subagent1 (ManagementOnlyClient)
    │
    │ 1. connect {"type": "register", "client_type": "management_only"}
    ▼
云端服务器
    │
    │ 2. 创建服务 + 隧道
    │ 3. 返回 {"type": "registered", "service_id", "tunnel_id"}
    ▼
subagent1 (等待通道请求)
```

### Skill 查询流程 (subagent2)

```
subagent2 (SkillQueryClient)
    │
    │ 1. connect {"type": "connect", "client_type": "skill_consumer"}
    │ 2. skill_discover {"tags": ["image"]}
    ▼
云端服务器
    │
    │ 3. 返回 {"type": "skill_list", "skills": [...]}
    ▼
subagent2
    │
    │ 4. get_service_docs {"service_id": "xxx"}
    ▼
云端服务器
    │
    │ 5. 返回 {"type": "service_docs", documentation, interface_spec}
    ▼
subagent2
    │
    │ 6. establish_channel {"service_id": "xxx"}
    ▼
云端服务器
    │
    │ 7. 转发 channel_request 到 subagent1
    ▼
subagent1
    │
    │ 8. channel_confirm {"accepted": true}
    ▼
云端服务器
    │
    │ 9. 返回 {"type": "channel_established"} 给 subagent2
    ▼
subagent2
    │
    │ 10. call_service {"method": "list_images", ...}
    ▼
云端服务器
    │
    │ 11. 转发到外部执行器
    ▼
外部执行器 (返回结果)
```

## 使用示例

### 1. 启动云端服务器

```bash
cd /home/t/.openclaw/workspace/Claw-Service-Hub
python -m server.main
```

### 2. 启动外部执行器（可选）

```bash
python examples/external_executor.py
```

### 3. subagent1 注册服务

```python
from client.management_client import ManagementOnlyClient

client = ManagementOnlyClient(
    name="coco-image-service",
    description="COCO数据集图片服务",
    endpoint="http://localhost:8080/api/coco",
    execution_mode="external",  # 关键：外部执行
    interface_spec={"methods": [...]}
)

await client.connect()
```

### 4. subagent2 查询和调用

```python
from client.skill_client import SkillQueryClient

client = SkillQueryClient()
await client.connect()

# 发现服务
services = await client.discover(tags=["image"])

# 获取文档
docs = await client.get_docs(service_id)

# 建立通道
channel = await client.establish_channel(service_id)

# 调用服务
result = await client.call_service(
    service_id=service_id,
    method="list_images",
    params={"limit": 10}
)
```

## 文件结构

```
Claw-Service-Hub/
├── server/
│   ├── main.py              # 云端服务器（已扩展新消息类型）
│   ├── registry.py          # 服务注册表（已扩展执行模式）
│   ├── tunnel.py            # 隧道管理
│   └── rating.py            # 评分系统
├── client/
│   ├── client.py            # 原始客户端（本地执行模式）
│   ├── management_client.py # 新增：纯管理型客户端
│   └── skill_client.py      # 新增：Skill 查询客户端
└── examples/
    ├── subagent1_management_only.py  # subagent1 示例
    ├── subagent2_skill_consumer.py   # subagent2 示例
    ├── multi_user_demo.py            # 完整演示
    └── external_executor.py          # 外部执行器示例
```

## API 参考

### 管理型客户端 (ManagementOnlyClient)

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到云端并注册服务 |
| `disconnect()` | 断开连接 |
| `confirm_channel(request_id, accepted)` | 确认/拒绝通道请求 |
| `on(event, callback)` | 注册事件回调 |

事件：
- `registered`: 服务注册成功
- `channel_request`: 收到通道建立请求

### Skill 查询客户端 (SkillQueryClient)

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到云端 |
| `discover(query, tags, ...)` | 发现服务 |
| `get_docs(service_id)` | 获取服务文档 |
| `get_skill_doc(service_id)` | 获取 SKILL.md |
| `establish_channel(service_id)` | 建立服务通道 |
| `call_service(service_id, method, params)` | 调用服务 |

## 消息协议扩展

### 新增消息类型

**客户端 → 服务器**

| 类型 | 说明 |
|------|------|
| `connect` | 消费者客户端连接 |
| `skill_discover` | Skill 方式查询服务 |
| `get_service_docs` | 获取服务文档 |
| `get_skill_doc` | 获取 SKILL.md |
| `establish_channel` | 建立服务通道 |
| `channel_confirm` | 确认通道请求 |

**服务器 → 客户端**

| 类型 | 说明 |
|------|------|
| `skill_list` | 服务列表响应 |
| `service_docs` | 服务文档响应 |
| `skill_doc` | SKILL.md 内容 |
| `channel_request` | 通道建立请求（发给提供者） |
| `channel_established` | 通道建立成功 |

## 与原架构的对比

| 特性 | 原架构 | 新架构 |
|------|--------|--------|
| 执行模式 | 本地执行 | 支持 external/remote |
| 客户端类型 | 单一 | 管理型 + 消费者 |
| 服务发现 | REST API / WebSocket 广播 | Skill 方式查询 |
| 通道建立 | 自动 | 提供者确认机制 |
| 使用场景 | 单节点 | 多用户协作 |

## 注意事项

1. **执行模式选择**
   - `local`: 适用于单节点既注册又执行
   - `external`: 适用于管理型客户端场景

2. **通道确认**
   - external 模式下，subagent1 需要确认通道请求
   - 可在回调中添加权限检查逻辑

3. **外部执行器**
   - 需要独立运行（如 n8n、python 服务）
   - 云端服务器转发请求到指定的 endpoint

4. **向后兼容**
   - 原 `ToolServiceClient` 仍可用
   - 新客户端是独立实现，不影响现有代码
