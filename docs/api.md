# API 参考

## Server API

### WebSocket 端点

```
ws://localhost:8765
```

### 消息类型

#### 注册服务

```json
{
  "type": "register",
  "payload": {
    "name": "weather-service",
    "description": "天气查询服务",
    "tags": ["weather", "api"],
    "methods": ["get_weather", "get_forecast"],
    "version": "1.0.0"
  }
}
```

**响应：**
```json
{
  "type": "registered",
  "payload": {
    "service_id": "uuid",
    "status": "active"
  }
}
```

#### 发现服务

```json
{
  "type": "discover",
  "payload": {
    "tags": ["weather"]
  }
}
```

**响应：**
```json
{
  "type": "discovered",
  "payload": {
    "services": [
      {
        "id": "uuid",
        "name": "weather-service",
        "description": "天气查询服务",
        "tags": ["weather", "api"],
        "rating": 9.5
      }
    ]
  }
}
```

#### 调用服务

```json
{
  "type": "call",
  "payload": {
    "service_id": "uuid",
    "method": "get_weather",
    "params": {"location": "Shanghai"}
  }
}
```

**响应：**
```json
{
  "type": "response",
  "payload": {
    "result": {"temperature": 20, "condition": "sunny"}
  }
}
```

#### 评分服务

```json
{
  "type": "rate",
  "payload": {
    "service_id": "uuid",
    "rating": 9,
    "comment": "服务响应很快"
  }
}
```

#### 心跳

```json
{
  "type": "heartbeat",
  "payload": {}
}
```

---

## Python Client API

### LocalServiceRunner

```python
from client.client import LocalServiceRunner

runner = LocalServiceRunner(
    name: str,           # 服务名称
    description: str,    # 服务描述
    hub_url: str,        # Hub 地址
    tags: List[str] = [], # 标签
    version: str = "1.0.0" # 版本
)
```

**方法：**

| 方法 | 描述 |
|------|------|
| `register_handler(method, handler)` | 注册服务方法 |
| `run()` | 启动服务 |
| `stop()` | 停止服务 |

### SkillQueryClient

```python
from client.skill_client import SkillQueryClient

client = SkillQueryClient(hub_url: str)
```

**方法：**

| 方法 | 描述 |
|------|------|
| `connect()` | 连接 Hub |
| `discover(tags=None)` | 发现服务 |
| `call_service(service_id, method, params)` | 调用服务 |
| `rate_service(service_id, rating, comment)` | 评分服务 |
| `disconnect()` | 断开连接 |

---

## REST API (可选)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/services` | GET | 列出所有服务 |
| `/services/{id}` | GET | 获取服务详情 |
| `/services/{id}/call` | POST | 调用服务 |
| `/services/{id}/rate` | POST | 评分服务 |
| `/health` | GET | 健康检查 |