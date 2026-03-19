# Claw-Service-Hub Key 授权功能规划 (v2)

## 需求分析

**目标**：在服务调用前增加 Key 授权机制，确保只有授权的调用者才能访问服务。

**Key 生命周期管理**：
1. **时间维度** - 有效时长（支持 Provider 自定义）
2. **次数维度** - 调用次数限制（支持 Provider 自定义）
3. **双验证** - Provider 自主管理 + Hub 验证

---

## 架构设计

```
┌──────────────┐     request_key      ┌──────────────┐
│  Consumer   │ ─────────────────────▶│  Provider    │
│ (调用者)     │                        │ (服务提供者)  │
└──────────────┘                        └──────────────┘
       │                                       │
       │  返回 Key (含生命周期参数)              │
       │◀──────────────────────────────────────┘
       │
       │  用 Key 访问隧道                         │
       ▼                                       │
┌──────────────┐     验证 Key                   │
│     Hub      │ ◀ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ▶ │
│  (隧道验证)   │                               │
└──────────────┘                               │
        │                                       │
        │ 验证:                                 │
        │ 1. Key 存在？                         │
        │ 2. 未过期？(时间)                     │
        │ 3. 还有次数？(次数)                    │
        │ 4. 服务端有效？(Provider 备案)        │
```

---

## 实现步骤

### Phase 1: 定义消息协议 (含生命周期)

**Consumer → Hub → Provider: 请求 Key**
```python
{
    "type": "key_request",
    "request_id": "req_xxx",
    "service_id": "svc_xxx",
    "consumer_id": "con_xxx",
    "purpose": "调用天气服务",      # 用途说明
    "timestamp": "2026-03-20T02:47:00Z"
}
```

**Provider → Hub → Consumer: 返回 Key (含生命周期)**
```python
{
    "type": "key_response",
    "request_id": "req_xxx",
    "approved": True,
    "key": "abc123xyz",
    "lifecycle": {
        "valid_from": "2026-03-20T02:47:00Z",    # 生效时间
        "valid_until": "2026-03-20T03:47:00Z",  # 过期时间 (1小时后)
        "max_calls": 100                         # 最大调用次数
    },
    "metadata": {
        "service_name": "weather-service",
        "description": "天气服务 - 每日100次"
    }
}
```

**Provider → Hub: 注册/更新服务的生命周期策略**
```python
{
    "type": "lifecycle_policy",
    "service_id": "svc_xxx",
    "default_lifecycle": {
        "duration_seconds": 3600,    # 默认1小时有效
        "max_calls": 100             # 默认100次
    },
    "custom_policies": {
        "premium_user": {
            "duration_seconds": 86400,  # 24小时
            "max_calls": 1000            # 1000次
        }
    }
}
```

**Consumer → Hub: 带 Key 调用 (含调用计数)**
```python
{
    "type": "call_service",
    "key": "abc123xyz",
    "service_id": "svc_xxx",
    "method": "get_weather",
    "params": {"city": "Shanghai"}
}
```

---

### Phase 2: Key 数据结构

```python
class KeyLifecycle:
    """Key 生命周期"""
    key: str
    service_id: str
    consumer_id: str
    
    # 时间维度
    created_at: datetime
    expires_at: datetime          # 过期时间点
    
    # 次数维度
    max_calls: int                 # 最大调用次数
    call_count: int                # 已调用次数
    
    # 状态
    is_active: bool                # 是否有效
    
    # Provider 备案
    provider_policy: dict         # 提供者的生命周期策略
```

---

### Phase 3: Server 端实现

#### 3.1 KeyManager 核心功能
```python
class KeyManager:
    def register_policy(self, service_id: str, policy: dict):
        """Provider 注册生命周期策略"""
        
    def generate_key(self, service_id: str, consumer_id: str, 
                     duration_seconds: int = 3600, 
                     max_calls: int = 100) -> str:
        """生成 Key"""
        
    def verify_key(self, key: str, service_id: str) -> bool:
        """验证 Key (时间+次数)"""
        
    def use_key(self, key: str) -> bool:
        """使用 Key (调用计数+1)"""
        
    def revoke_key(self, key: str) -> bool:
        """撤销 Key"""
        
    def list_keys(self, service_id: str, consumer_id: str = None) -> list:
        """列出 Key"""
```

#### 3.2 验证逻辑
```python
def verify_key(self, key: str, service_id: str) -> dict:
    """验证 Key 是否有效"""
    
    key_data = self.keys.get(key)
    if not key_data:
        return {"valid": False, "reason": "Key不存在"}
    
    # 1. 检查 Provider 备案
    if service_id != key_data.get("service_id"):
        return {"valid": False, "reason": "服务不匹配"}
    
    # 2. 时间验证
    now = datetime.now()
    if now > key_data.get("expires_at"):
        return {"valid": False, "reason": "已过期"}
    
    # 3. 次数验证
    if key_data.get("call_count", 0) >= key_data.get("max_calls", 0):
        return {"valid": False, "reason": "次数用尽"}
    
    return {"valid": True}
```

#### 3.3 调用时扣减
```python
async def call_service(self, key: str, service_id: str, ...):
    """调用服务时扣减次数"""
    
    result = self.verify_key(key, service_id)
    if not result["valid"]:
        raise PermissionError(result["reason"])
    
    # 扣减次数
    self.keys[key]["call_count"] += 1
    
    return await self.forward_to_provider(...)
```

---

### Phase 4: Provider 端实现

#### 4.1 注册生命周期策略
```python
class LocalServiceRunner:
    def set_lifecycle_policy(self, duration_seconds: int = 3600, 
                             max_calls: int = 100):
        """设置默认生命周期策略"""
        self.lifecycle_policy = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls
        }
    
    def set_custom_policy(self, condition: str, 
                          duration_seconds: int, max_calls: int):
        """设置自定义策略 (如根据 consumer 设置)"""
        self.custom_policies[condition] = {
            "duration_seconds": duration_seconds,
            "max_calls": max_calls
        }
```

#### 4.2 Key 请求处理回调
```python
async def on_key_request(self, consumer_id: str, purpose: str) -> dict:
    """
    处理 Key 请求 - 可自定义审批逻辑
    返回: {"approved": True/False, "custom_lifecycle": {...}}
    """
    # 示例：根据 consumer 设置不同策略
    if consumer_id in self.custom_policies:
        return {
            "approved": True,
            "lifecycle": self.custom_policies[consumer_id]
        }
    
    return {
        "approved": True,
        "lifecycle": self.lifecycle_policy
    }
```

---

### Phase 5: Consumer 端实现

```python
class SkillQueryClient:
    async def request_key(self, service_id: str, 
                          purpose: str = "") -> dict:
        """
        请求 Key
        返回: {"key": "...", "lifecycle": {...}}
        """
        
    async def call_service(self, service_id: str, method: str, 
                           params: dict = None) -> dict:
        """调用服务 (自动带 Key)"""
        
    def get_key_info(self, service_id: str) -> dict:
        """查看 Key 信息 (剩余次数、过期时间)"""
```

---

## 文件变更清单

| 文件 | 变更 |
|------|------|
| `server/key_manager.py` | **新建** - Key 管理核心逻辑 |
| `server/lifecycle.py` | **新建** - 生命周期管理 |
| `server/main.py` | 添加 lifecycle_policy 消息处理 |
| `client/client.py` | Provider 添加 set_lifecycle_policy |
| `client/skill_client.py` | Consumer 添加 request_key |
| `skills/hub-client/SKILL.md` | 更新文档，添加授权示例 |

---

## 测试计划

### 基础测试
1. ✅ Provider 注册服务 + 生命周期策略
2. ✅ Consumer 请求 Key
3. ✅ Provider 批准 + 返回 Key
4. ✅ Consumer 用 Key 调用成功
5. ✅ 无 Key 调用被拒绝

### 生命周期测试
6. ⏱ 时间过期 → 调用被拒绝
7. 🔢 次数用尽 → 调用被拒绝
8. 🔄 Provider 撤销 Key → 调用被拒绝
9. 📊 查看 Key 剩余次数/时间

### 自定义策略测试
10. 不同 Consumer 不同策略
11. Provider 动态更新策略

---

## 配置示例

**Provider 端**：
```python
runner = LocalServiceRunner("my-service", ...)

# 设置默认生命周期: 1小时, 100次
runner.set_lifecycle_policy(
    duration_seconds=3600,
    max_calls=100
)

# 设置自定义策略
runner.set_custom_policy(
    condition="premium_user",
    duration_seconds=86400,  # 24小时
    max_calls=1000            # 1000次
)

runner.register_handler("method", handler)
await runner.run()
```

**Consumer 端**：
```python
client = SkillQueryClient()
await client.connect()

# 请求 Key
key_info = await client.request_key(
    service_id="svc_xxx",
    purpose="日常天气查询"
)
print(f"Key: {key_info['key']}")
print(f"有效至: {key_info['lifecycle']['valid_until']}")
print(f"剩余次数: {key_info['lifecycle']['max_calls']}")

# 调用服务
result = await client.call_service("svc_xxx", "get_weather", {"city": "Shanghai"})
```