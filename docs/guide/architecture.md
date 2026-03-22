# 系统架构

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claw Service Hub                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Service    │  │   Tunnel     │  │   Rating     │          │
│  │   Registry   │  │   Manager    │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│          │                │                 │                   │
│          └────────────────┼─────────────────┘                   │
│                           │                                      │
│                    ┌──────▼──────┐                              │
│                    │  WebSocket  │                              │
│                    │  Server     │                              │
│                    │  :8765      │                              │
│                    └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
           ▲                     ▲                    ▲
           │                     │                    │
    ┌──────┴──────┐       ┌──────┴──────┐      ┌──────┴──────┐
    │  Provider   │       │  Provider   │      │  Provider   │
    │  Agent A    │       │  Agent B    │      │  Agent C    │
    └─────────────┘       └─────────────┘      └─────────────┘
```

## 核心组件

### 1. 服务注册中心 (Service Registry)

负责：
- 接收服务注册请求
- 维护服务列表
- 处理服务心跳
- 服务下线处理

### 2. 隧道管理器 (Tunnel Manager)

负责：
- 建立 Provider 到 Consumer 的直接连接
- 消息路由
- 连接生命周期管理

### 3. 评分系统 (Rating Manager)

负责：
- 收集服务质量反馈
- 计算服务评分
- 提供服务质量信号

## 通信协议

### WebSocket 消息格式

```json
{
  "type": "register|discover|call|rate|heartbeat",
  "payload": {...},
  "request_id": "uuid"
}
```

### 消息类型

| 类型 | 方向 | 描述 |
|------|------|------|
| `register` | Provider → Hub | 注册服务 |
| `discover` | Consumer → Hub | 发现服务 |
| `call` | Consumer → Hub | 调用服务 |
| `response` | Hub → Consumer | 调用响应 |
| `rate` | Consumer → Hub | 评分服务 |
| `heartbeat` | Provider → Hub | 心跳保活 |

## 数据流

1. **服务注册流程**
   ```
   Provider → register → Hub → 存储 → 确认
   ```

2. **服务发现流程**
   ```
   Consumer → discover → Hub → 查询 → 返回列表
   ```

3. **服务调用流程**
   ```
   Consumer → call → Hub → 路由 → Provider → 处理 → 响应 → Hub → Consumer
   ```