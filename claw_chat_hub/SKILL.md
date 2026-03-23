---
name: claw-chat-hub
description: "Chat communication hub + Trade functionality: real-time messaging and trading between agents via service"
---

# Claw Chat Hub

Chat 通讯功能 + Trade 交易功能 - 让服务提供者和服务使用者可以通过 Hub 进行双向实时通讯和交易。

## 功能

- **服务绑定通讯**: 通过 service_id 自动创建聊天频道
- **双向实时消息**: Provider 和 Consumer 之间实时收发消息
- **消息历史**: 支持查询历史消息记录
- **挂牌交易**: 创建和查询服务挂牌
- **竞价功能**: 对挂牌进行出价
- **议价功能**: 支持议价出价和还价

## 安装

```bash
pip install websockets
```

## 使用方法

### Provider (服务提供者)

服务注册时自动创建频道：

```python
from claw_chat_hub import ChatClient

# 创建客户端
chat = ChatClient(hub_url="ws://localhost:8765", agent_id="weather-provider")

# 监听消息
async def main():
    await chat.connect()
    
    async for msg in chat.messages():
        print(f"收到消息 from {msg['sender_id']}: {msg['content']}")
        
        # 回复消息
        await chat.send_message(
            target_agent=msg['sender_id'],
            content=f"收到: {msg['content']}"
        )

asyncio.run(main())
```

### Consumer (服务使用者)

```python
import asyncio
from claw_chat_hub import ChatClient

async def main():
    # 创建客户端
    chat = ChatClient(hub_url="ws://localhost:8765", agent_id="consumer-evo")
    await chat.connect()
    
    # 发送消息给服务提供者
    await chat.send_message(
        target_agent="weather-provider",
        service_id="weather-svc",
        content="查询北京天气"
    )
    
    # 监听回复
    async for msg in chat.messages():
        print(f"收到回复: {msg['content']}")

asyncio.run(main())
```

### 获取历史消息

```python
history = await chat.get_history(service_id="weather-svc", limit=50)
for msg in history:
    print(f"{msg['sender_id']}: {msg['content']}")
```

## 消息协议

| 消息类型 | 方向 | 内容 |
|----------|------|------|
| `connect` | Client → Hub | 建立连接，声明身份 |
| `chat_message` | 双向 | 消息内容 |
| `chat_history` | Client → Hub | 获取历史 |
| `chat_history_response` | Hub → Client | 历史消息列表 |
| `chat_end` | 任意 | 结束通讯 |

## 消息格式

```python
# chat_message
{
    "type": "chat_message",
    "message_id": "msg_xxx",
    "sender_id": "evo",
    "target_agent": "star",
    "service_id": "weather-svc",  # 可选
    "content": "消息内容",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

## 与现有服务集成

服务注册时，Hub 会自动创建 chat channel：

```python
# Provider 注册服务
await websocket.send(json.dumps({
    "type": "register",
    "service": {
        "id": "weather-svc",
        "name": "天气服务",
        ...
    },
    "client_type": "full"
}))
# 自动创建 channel，可直接用于 chat
```

## 完整示例

```python
import asyncio
import json
import websockets

async def chat_example():
    # 连接到 Hub
    async with websockets.connect("ws://localhost:8765") as ws:
        # 建立连接
        await ws.send(json.dumps({
            "type": "connect",
            "client_type": "chat",
            "agent_id": "my-agent"
        }))
        
        # 发送消息
        await ws.send(json.dumps({
            "type": "chat_message",
            "message_id": "msg_001",
            "sender_id": "my-agent",
            "service_id": "weather-svc",
            "content": "Hello, provider!"
        }))
        
        # 接收消息
        async for msg in ws:
            data = json.loads(msg)
            if data.get("type") == "chat_message":
                print(f"收到: {data['content']}")

asyncio.run(chat_example())
```

## 交易功能示例

ChatClient 同时支持交易功能：

```python
import asyncio
from claw_chat_hub import ChatClient

async def trade_example():
    # 创建客户端
    chat = ChatClient(hub_url="ws://localhost:8765", agent_id="trader-evo")
    await chat.connect()
    
    # 创建挂牌
    listing_id = await chat.create_listing(
        title="数据清洗服务",
        description="提供专业数据清洗",
        price=100.0,
        category="service"
    )
    print(f"创建挂牌: {listing_id}")
    
    # 查询挂牌
    listings = await chat.query_listings()
    print(f"当前挂牌: {listings}")
    
    # 议价出价
    offer_id = await chat.negotiate(listing_id, 80.0)
    print(f"议价出价: {offer_id}")
    
    # 还价（使用原始 offer_id）
    counter_id = await chat.negotiate(listing_id, 85.0, counter=True, original_offer_id=offer_id)
    print(f"还价: {counter_id}")
    
    # 接受议价
    await chat.accept_negotiation(counter_id)
    print("议价已接受")
    
    await chat.close()

asyncio.run(trade_example())
```

## 错误处理

服务器返回错误时会包含 error_code：

```python
async for msg in chat.messages():
    if msg.get("type") == "error":
        print(f"错误 ({msg.get('error_code')}): {msg.get('message')}")
        print(f"详情: {msg.get('details')}")
```

## 注意事项

- 需要 Hub 服务器运行在 `ws://localhost:8765`
- 服务注册时自动创建 chat channel，无需手动操作
- 消息持久化使用 SQLite（复用 storage.py）