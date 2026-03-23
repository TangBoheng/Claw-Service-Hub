# Claw-Service-Hub 统一解决方案

## 五大问题与解决方案

| # | 问题 | 解决方案 | 状态 |
|---|------|----------|------|
| 1 | 优先级冲突 | P0/P1/P2 分层 | ✅ 已定义 |
| 2 | 技术栈过重 | 精简依赖，只保留核心 | 🔄 执行中 |
| 3 | 测试策略模糊 | TEST_STRATEGY.md | ✅ 已完成 |
| 4 | 安全复杂度高 | 简化 key_manager | 🔄 执行中 |
| 5 | 文档矛盾 | 统一文档 | 🔄 执行中 |

---

## 优先级定义 (P0/P1/P2)

### P0 核心 (必须保留)
- 服务注册/发现 (registry.py)
- 服务调用隧道 (tunnel.py)
- 基础交易 (挂牌/竞价/议价)

### P1 重要 (可选)
- API Key 认证 (key_manager.py)
- 速率限制 (ratelimit.py)
- 数据持久化 (storage.py)

### P2 可移除 (精简)
- Chat 通讯 (chat_channel.py)
- 评分系统 (rating.py)
- 复杂验证 (validators.py)

---

## 技术栈精简

### 保留依赖
```
websockets>=12.0
aiohttp>=3.9.0
pyyaml
```

### 精简后目标
- 文件数: 28 → 18 (减少 36%)
- 依赖: 5 → 3

---

## 测试分层

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元 | 核心逻辑 | pytest |
| 集成 | API调用 | asyncio |
| 端到端 | 完整流程 | subprocess |

目标覆盖率: P0 90%+, 总体 80%+

---

## 三个独立 Skill

| Skill | 功能 | 核心文件 |
|-------|------|----------|
| hub-service | 服务注册/发现/调用 | registry.py, tunnel.py |
| hub-chat | 智能体通讯 | chat_channel.py |
| hub-trade | 挂牌/竞价/议价 | trade_client.py |

客户端可选择性安装

---

## 执行状态

- [x] 定义 P0/P1/P2 优先级
- [x] 创建 TEST_STRATEGY.md
- [ ] 精简技术栈 (删除 P2 文件)
- [ ] 简化 key_manager
- [ ] 统一文档
- [ ] 推送 GitHub