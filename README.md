# 🛠️ Tool Service Hub

服务撮合云端 - OpenClaw 工具服务发现与调用平台

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      云端服务撮合平台                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Service     │  │  Tunnel     │  │ Rating      │         │
│  │ Registry    │  │  Manager    │  │ Manager     │         │
│  │ (内存Map)    │  │  (WS Server)│  │ (评分存储)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                         │                                    │
│                    WebSocket :8765                          │
└─────────────────────────────────────────────────────────────┘
           ▲                ▲                 ▲
           │                │                 │
    ┌──────┴──────┐  ┌──────┴──────┐   ┌──────┴──────┐
    │ OpenClaw   │  │ OpenClaw   │   │ OpenClaw   │
    │ 节点 A     │  │ 节点 B     │   │ 节点 C     │
    │ (工具服务) │  │ (工具服务) │   │ (工具服务) │
    └────────────┘  └────────────┘   └────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install websockets aiohttp
```

### 2. 启动云端服务器

```bash
cd tool-service-hub
python -m server.main
```

服务器会监听 `ws://localhost:8765`

### 3. 启动一个工具服务 (客户端)

```bash
cd tool-service-hub/client
python example.py
```

## 项目结构

```
tool-service-hub/
├── server/
│   ├── main.py       # WebSocket 服务器入口
│   ├── registry.py   # 服务注册与发现
│   ├── tunnel.py     # 隧道管理
│   └── rating.py    # 评分系统
├── client/
│   ├── client.py    # 客户端库
│   └── example.py   # 使用示例
├── test.py           # 单元测试
└── requirements.txt
```

## 核心模块

### ServiceRegistry (服务注册)

类似 OpenClaw skill 的快速发现机制：
- 节点启动时主动注册服务元数据
- 支持按名称、标签、状态过滤查找
- 心跳保活，自动清理离线服务

### TunnelManager (隧道管理)

- WebSocket 长连
- 请求转发：云端 → 节点
- 响应回传：节点 → 云端

### RatingManager (评分系统)

- 1-10 分制
- 评价标签：["fast", "accurate", "reliable"]
- 统计：平均分、标签聚合

## 消息协议

### 客户端 → 云端

```json
// 注册服务
{
  "type": "register",
  "service": {
    "name": "csv-processor",
    "description": "处理CSV数据",
    "version": "1.0.0",
    "endpoint": "http://localhost:8080",
    "tags": ["data", "csv"]
  }
}

// 心跳
{
  "type": "heartbeat",
  "service_id": "xxx"
}

// 请求响应
{
  "type": "response",
  "request_id": "xxx",
  "response": {"result": "..."}
}
```

### 云端 → 客户端

```json
// 注册确认
{
  "type": "registered",
  "service_id": "xxx",
  "tunnel_id": "xxx",
  "status": "online"
}

// 远程请求
{
  "type": "request",
  "request_id": "xxx",
  "method": "process_csv",
  "params": {"filename": "data.csv"}
}

// 服务列表更新
{
  "type": "service_list",
  "services": [...]
}
```

## REST API (可选)

启动服务器后，可选使用 REST API：

```bash
# 列出所有服务
curl http://localhost:8765/api/services

# 获取服务评分
curl http://localhost:8765/api/services/{service_id}/ratings

# 提交评分
curl -X POST http://localhost:8765/api/ratings \
  -H "Content-Type: application/json" \
  -d '{"service_id": "xxx", "score": 9, "comment": "很好用"}'

# 列出隧道
curl http://localhost:8765/api/tunnels
```

## Phase 1 功能清单

| 功能 | 状态 |
|------|------|
| 服务注册 | ✅ |
| 服务发现 (名称/标签) | ✅ |
| 心跳保活 | ✅ |
| WebSocket 隧道 | ✅ |
| 1-10 分评分 | ✅ |
| REST API | 🔄 可选 |

## TODO (Phase 2+)

- [ ] 服务发现 HTTP API 完整实现
- [ ] 评分持久化 (文件/数据库)
- [ ] 服务调用代理 (通过云端调用其他节点服务)
- [ ] 认证与授权
- [ ] 流量统计与监控