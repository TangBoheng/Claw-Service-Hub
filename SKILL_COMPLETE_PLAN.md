# Skill 完善计划

## 目标
基于测试经验，创建**完整的、可发布的** tool-service-hub skill

---

## 需求确认（最高优先级）

**不是实现测试功能！是从测试中提炼出通用的 skill 框架。**

### 核心原则
1. ✅ 使用 LocalServiceRunner 让 subagent 提供服务
2. ✅ 使用 SkillQueryClient 让 subagent 调用服务  
3. ✅ 不硬编码测试需求，让用户指定任意数据源
4. ✅ subagent 能独立根据 skill 写代码，不需要我辅助

---

## 当前问题

❌ 之前我只是"替" subagent 写代码执行
✅ 真正需要的是：subagent 自己读 skill → 理解 → 写代码 → 执行

---

## 完成标准

skill 包含：
1. [ ] **Provider 模板** - 完整的 LocalServiceRunner 使用示例
2. [ ] **Consumer 模板** - 完整的 SkillQueryClient 使用示例
3. [ ] **故障排查** - 常见问题和解决方案
4. [ ] **环境配置** - 依赖安装、环境变量
5. [ ] **测试验证** - 如何验证服务正常工作

---

## 文件位置

- 主 skill: `/home/t/.openclaw/workspace/Claw-Service-Hub/skills/hub-client/SKILL.md`
- subagent1: `/home/t/.openclaw/workspace-subagent1/skills/hub-client/SKILL.md`
- subagent2: `/home/t/.openclaw/workspace-subagent2/skills/hub-client/SKILL.md`
- subagent3: `/home/t/.openclaw/workspace-subagent3/skills/hub-client/SKILL.md`

---

## 待完成

1. 更新 SKILL.md - 添加更完整的模板
2. 确保 skill 同步到所有 subagent workspace
3. 测试 subagent 能否独立使用 skill