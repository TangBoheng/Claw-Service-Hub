# 🤖 Chat 通讯功能规划

## 目标
让服务提供者和服务使用者可以通过 Hub 进行双向实时通讯

---

## 1. 架构设计

### 1.1 核心概念

| 概念 | 说明 |
|------|------|
| **Channel (频道)** | 两个智能体之间的通讯通道 |
| **Session (会话)** | 单次对话，包含多条消息 |
| **Message (消息)** | 具体的消息内容 |

### 1.2 通讯流程

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│ Provider A  │         │     Hub    │         │ Consumer B  │
│  (star)     │◄───────►│  (Server)  │◄───────►│  (evo)      │
└─────────────┘         └─────────────┘         └─────────────┘
     │                        │                        │
     │  1. 注册服务            │                        │
     │──────────────────────►│                        │
     │                       │                        │
     │                 2. 绑定频道                   │
     │◄─────────────────────│                        │
     │                       │                        │
     │                 3. 发现服务                  │
     │                       │◄──────────────────────►│
     │                       │                        │
     │  4. 双向通讯           │◄─────────────────────►
     │◄─────────────────────│◄─────────────────────►
     │                       │                        │
     │                 5. 保存会话                  │
     │◄─────────────────────│◄─────────────────────►
```

---

## 2. Server 改进

### 2.1 新增文件

| 文件 | 功能 |
|------|------|
| `server/chat_channel.py` | 频道管理器 - 创建/获取/关闭频道 |
| `server/chat_session.py` | 会话管理器 - 创建/查询/历史 |
| `server/chat_message.py` | 消息处理 |
| `server/chat_storage.py` | 消息持久化 (SQLite) |
| `server/main.py` | 添加 chat 消息协议处理 |

### 2.2 消息协议

| 消息类型 | 方向 | 内容 |
|----------|------|------|
| `chat_request` | Consumer → Hub → Provider | 发起通讯请求 |
| `chat_accept` | Provider → Hub → Consumer | 接受通讯 |
| `chat_message` | 双向 | 消息内容 |
| `chat_end` | 任意 | 结束通讯 |
| `chat_history` | Consumer → Hub | 获取历史 |

### 2.3 数据结构

```python
# 频道 (Channel)
{
    "channel_id": "ch_xxx",
    "provider_id": "star",      # 服务提供者
    "consumer_id": "evo",       # 服务使用者
    "service_id": "weather-svc", # 关联服务
    "created_at": "timestamp"
}

# 会话 (Session)
{
    "session_id": "sess_xxx",
    "channel_id": "ch_xxx",
    "service_id": "weather-svc",
    "status": "active|closed",
    "created_at": "timestamp"
}

# 消息 (Message)
{
    "message_id": "msg_xxx",
    "session_id": "sess_xxx",
    "sender_id": "evo",
    "content": "消息内容",
    "timestamp": "timestamp"
}
```

---

## 3. Chat Client

### 3.1 文件结构

```
claw-chat-hub/
├── chat_client.py     # 通讯客户端
├── __init__.py
└── SKILL.md
```

### 3.2 客户端功能

```python
from chat_client import ChatClient

# 创建客户端
chat = ChatClient(hub_url="ws://localhost:8765", agent_id="star")

# 监听消息
async def on_message(msg):
    print(f"收到消息: {msg['content']}")
    # 处理消息

# 启动监听
await chat.listen(on_message)

# 发送消息
await chat.send_message(
    target_agent="evo",      # 目标智能体
    service_id="weather-svc", # 通过服务找到智能体
    content="你好evo"
)

# 获取历史
history = await chat.get_history(service_id="weather-svc")
```

---

## 4. SKILL.md 结构

```markdown
---
name: claw-chat-hub
description: "Chat hub: send messages between agents"
---

# Claw Chat Hub

## 功能
- 服务绑定通讯
- 双向实时消息
- 消息历史

## 使用方法

### Provider (发布服务时自动创建频道)
# 监听消息
async def listen():
    client = ChatClient()
    async for msg in client.messages():
        print(msg)
```

---

## 5. 实施顺序

### Phase 1: 基础通讯
1. 创建 server/chat_channel.py
2. 修改 server/main.py 添加协议
3. 创建 chat_client.py
4. 测试双方通讯

### Phase 2: 消息持久化
1. 创建 chat_storage.py
2. 添加历史记录功能
3. 查找历史功能

### Phase 3: 优化
1. 消息确认机制
2. 离线消息
3. 群组通讯

---

## 6. 关键设计决策

### Q: 如何找到智能体通讯渠道？
### A: 通过 service_id 绑定
   - 服务注册时自动创建 channel
   - service_id → channel_id → provider_id

### Q: 消息如何存储？
### A: SQLite (复用现有 storage.py)

### Q: 是否需要实时在线？
### A: 在线优先，离线存储消息
```
