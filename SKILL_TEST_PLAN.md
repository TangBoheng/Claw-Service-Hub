# Skill 测试计划

## 目标
让 subagent 可以使用 skill：
1. 写代码**提供**服务（Provider）
2. 写代码**接受**服务（Consumer）

## 原则
- ❌ 不要把测试示例服务需求硬编码进 skill
- ✅ skill 只提供**模板**和**机制**，用户需求由用户指定

---

## 测试阶段

### Phase 1: Skill 基本可用性
- [x] 1.1 验证 skill 文档语法正确
- [x] 1.2 验证 import 路径正确
- [x] 1.3 验证类名和方法名正确

### Phase 2: Provider 模式测试
- [x] 2.1 subagent 能用 skill 启动一个简单服务 ✅
- [x] 2.2 服务能成功注册到 Hub ✅
- [x] 2.3 服务能被正确调用并返回结果 ✅

### Phase 3: Consumer 模式测试  
- [x] 3.1 subagent 能用 skill 发现可用服务 ✅
- [x] 3.2 能建立服务通道 ✅
- [x] 3.3 能调用服务并获取结果 ✅

### Phase 4: 完整流程测试
- [x] 4.1 Provider 注册服务 → Consumer 发现并调用 ✅

---

## 发现的问题及修复

### 问题 1: 服务ID字段名不一致
- **现象**: `discover()` 返回的是 `skill_id`，但文档可能写的是 `service_id`
- **修复**: 确认代码使用 `skill_id`
- **状态**: ✅ 已验证，代码正确

### 问题 2: call_service 参数
- **现象**: 需要使用 `service_id` 参数（会自动关联通道）
- **修复**: 更新示例代码
- **状态**: ✅ 已验证，代码正确

---

## 更新 SKILL.md

需要修复文档中的示例代码：
1. 服务发现返回 `skill_id` 而不是 `service_id`
2. `call_service` 使用 `service_id` 参数