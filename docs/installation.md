# 安装指南

## 系统要求

- Python 3.10 或更高版本
- Linux/macOS/Windows

## 使用 pip 安装

```bash
pip install claw-service-hub
```

## 从源码安装

```bash
# 克隆仓库
git clone https://github.com/TangBoheng/Claw-Service-Hub.git
cd Claw-Service-Hub

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

## 依赖项

核心依赖：
- `websockets` - WebSocket 通信
- `aiohttp` - HTTP 客户端/服务器
- `python-dotenv` - 环境变量管理

开发依赖：
- `pytest` - 测试框架
- `black` - 代码格式化
- `isort` - import 排序

## Docker 部署

```bash
# 构建镜像
docker build -t claw-service-hub .

# 运行容器
docker run -p 8765:8765 claw-service-hub
```

## 验证安装

```bash
python -m server.main
# 应该看到服务器启动在 ws://localhost:8765
```