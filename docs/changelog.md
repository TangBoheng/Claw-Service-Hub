# 变更日志

All notable changes to this project will be documented in this file.

## [1.0.0] - 2024-03-xx

### Added
- 服务注册与发现系统
- WebSocket 通信支持
- 评分系统 (1-10 分)
- 隧道管理器
- 中英双语支持
- 完整的 Python 客户端
- Docker 支持
- 单元测试套件
- GitHub Actions CI/CD

### Changed
- 重构项目结构
- 优化 WebSocket 消息处理

### Fixed
- 心跳连接问题
- 服务下线处理

---

## [0.9.0] - 2024-02-xx

### Added
- 初始版本
- 基本服务注册
- 简单服务发现

---

## 即将到来

- [ ] CLI 工具 (`claw-hub` 命令)
- [ ] 认证与授权
- [ ] 服务版本管理
- [ ] 更多集成示例
- [ ] 性能优化

---

## 版本规范

遵循 [语义化版本](https://semver.org/lang/zh-CN/)：
- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的新功能
- **PATCH**: 向后兼容的问题修复