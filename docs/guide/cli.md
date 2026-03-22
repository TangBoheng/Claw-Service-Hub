# CLI 工具

提供命令行接口快速启动和管理 Hub。

## 安装

```bash
pip install claw-service-hub
```

## 使用

### 启动 Hub 服务器

```bash
claw-hub start
# 或
python -m server.main
```

### 查看帮助

```bash
claw-hub --help
```

### 配置选项

```bash
claw-hub start --host 0.0.0.0 --port 8765 --log-level DEBUG
```

## 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `HUB_HOST` | `0.0.0.0` | 绑定地址 |
| `HUB_PORT` | `8765` | 绑定端口 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `STORAGE` | `memory` | 存储类型 |