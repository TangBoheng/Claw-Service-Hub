# 测试策略 - Claw-Service-Hub

## 测试分层

| 层级 | 覆盖范围 | 工具 | 目标 |
|------|----------|------|------|
| **单元测试** | 核心逻辑 (registry, tunnel, key_manager) | pytest | 每个 P0 函数有测试 |
| **集成测试** | API 调用、WebSocket | asyncio | 关键路径覆盖 |
| **端到端** | 完整流程 | subprocess | 冒烟测试 |

---

## 测试目录结构

```
tests/
├── unit/                   # 单元测试
│   ├── test_registry.py
│   ├── test_tunnel.py
│   └── test_key_manager.py
│
├── integration/            # 集成测试
│   ├── test_service_flow.py
│   └── test_trade_flow.py
│
└── e2e/                   # 端到端
    ├── test_server_start.py
    └── test_full_flow.py
```

---

## 测试优先级

### P0 (必须覆盖)
- [ ] 服务注册成功
- [ ] 服务发现返回列表
- [ ] 服务调用隧道建立
- [ ] 交易挂牌创建
- [ ] 交易竞价创建

### P1 (应该覆盖)
- [ ] 用户认证通过/拒绝
- [ ] 速率限制触发
- [ ] 错误处理

### P2 (可选覆盖)
- [ ] 消息持久化
- [ ] 并发连接

---

## 运行测试

```bash
# 全部测试
pytest tests/ -v

# 仅单元测试
pytest tests/unit/ -v

# 仅集成测试
pytest tests/integration/ -v

# 仅端到端
pytest tests/e2e/ -v
```

---

## 覆盖率目标

- P0 功能: 90%+
- P1 功能: 70%+
- 总体: 80%+