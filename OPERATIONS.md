# Claw-Service-Hub 操作手册

> 本地下载 -> 服务部署 -> skill 发布到 clawhub.ai 的完整流程。

## 0. 前置条件

| 项 | 要求 |
|----|------|
| Python | >= 3.10 |
| Git | 任意版本 |
| clawhub CLI | v0.7.0+（用于发布 skill） |
| clawhub 账户 | 已登录且已接受 MIT-0 发布条款 |

---

## 1. 下载项目（任何人都能执行）

```bash
git clone https://github.com/TangBoheng/Claw-Service-Hub.git
cd Claw-Service-Hub
```

确认 skill 源文件存在：

```bash
ls skills/
# claw-service-hub  claw-chat-hub  claw-trade-hub
```

---

## 2. 自部署 Hub 服务

Claw-Service-Hub 是一个 **WebSocket 服务**，是三个 skill 依赖的运行时后端。可二选一部署。

### 2.1 方式 A：直接运行（开发/测试推荐）

```bash
# 1) 安装依赖
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) 配置环境变量
cp .env.example .env
# 按需编辑 .env（端口、API_KEY 等）

# 3) 安装客户端 SDK（可选，skill 调用需要）
pip install -e client/

# 4) 启动服务
python start_server.py
# 或: python -m server.main
```

启动成功标志：
```
Starting Tool Service Hub...
WebSocket server will listen on ws://0.0.0.0:8765
```

服务监听 `ws://0.0.0.0:8765`，提供：服务注册/发现/调用、Key 授权、Chat 通讯、Trade 交易议价。

### 2.2 方式 B：Docker 部署（生产推荐）

```bash
docker build -f docker/Dockerfile -t claw-service-hub:latest .
docker run -d --name claw-hub -p 8765:8765 \
  -e HUB_HOST=0.0.0.0 -e HUB_PORT=8765 \
  --env-file .env \
  claw-service-hub:latest
```

### 2.3 验证服务

```bash
# 健康检查（用客户端 SDK）
python -c "
import asyncio
from claw_client.hub.client import HubClient
async def t():
    c = HubClient(url='ws://localhost:8765', name='probe')
    await c.connect()
    print('connected, id=', c.client_id)
    await c.disconnect()
asyncio.run(t())
"
```

### 2.4 关键配置项（.env）

| 变量 | 默认 | 说明 |
|------|------|------|
| `HUB_HOST` | `0.0.0.0` | 监听地址 |
| `HUB_PORT` | `8765` | WebSocket 端口 |
| `API_KEY` | 空 | 服务访问密钥（生成：`python -c "import secrets; print(secrets.token_hex(32))"`） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

---

## 3. 发布 skill 到 clawhub.ai

> ⚠️ 这是**对外发布动作**，会把 skill 推送到公开 registry `https://clawhub.ai`。

### 3.1 安装并登录 clawhub CLI

```bash
# 安装 CLI（若未装）
npm install -g clawhub

# 登录（浏览器授权，或用 token）
clawhub login
# 或: clawhub login --token <YOUR_TOKEN>

# 确认登录身份
clawhub whoami
# 期望输出: ✔ <你的用户名>
```

### 3.2 接受 MIT-0 发布条款（首次发布必做）

clawhub 要求发布者接受 MIT-0 许可条款。CLI 没有对应命令，**必须在网站操作一次**：

1. 浏览器打开 https://clawhub.ai/skills/publish
2. 用 GitHub 登录（与 CLI 同一账户）
3. 按页面提示接受 **MIT-0 许可条款**

> 完成后该账户即可用 CLI 发布，无需重复接受。

### 3.3 发布 / 更新三个 skill

在项目根目录执行：

```bash
# 1) claw-service-hub
clawhub publish skills/claw-service-hub \
  --slug claw-service-hub \
  --version 1.1.0 \
  --changelog "English description + add GitHub source/homepage URLs; bilingual overview"

# 2) claw-chat-hub
clawhub publish skills/claw-chat-hub \
  --slug claw-chat-hub \
  --version 1.1.0 \
  --changelog "English description + add GitHub source/homepage URLs; bilingual overview"

# 3) claw-trade-hub
clawhub publish skills/claw-trade-hub \
  --slug claw-trade-hub \
  --version 1.1.0 \
  --changelog "English description + add GitHub source/homepage URLs; bilingual overview"
```

每个成功后会输出：
```
OK. Published <slug>@1.1.0 (<versionId>)
```

### 3.4 验证发布结果

```bash
clawhub inspect claw-service-hub
clawhub inspect claw-chat-hub
clawhub inspect claw-trade-hub
```

确认：
- ✅ `Summary` 已变为英文（不再是纯中文）
- ✅ `Latest` 版本为 `1.1.0`
- ✅ 在网站 https://clawhub.ai/skills/<slug> 上能看到 GitHub 源链接

---

## 4. 本次改进内容（1.1.0）

三个 skill 的 `SKILL.md` 统一做了以下改动：

| 改动项 | 之前 | 之后 |
|--------|------|------|
| `description` | 纯中文 | 英文为主 + 中文副标题 |
| `version` | `1.0.0` | `1.1.0` |
| `homepage` | 无 | 指向 GitHub 仓库 |
| `source` | 无 | 指向 skill 子目录 |
| 正文 | 中文 | 新增英文 Overview + Source 段落 |
| `license` | 无 | `MIT` |
| `tags` | 4 个 | 增加 `hub` |

对应 commit：`71b854e docs(skills): SKILL.md 英文化 + 补全 git 源地址`

---

## 5. 故障排查

| 现象 | 原因 / 解决 |
|------|-------------|
| `MIT-0 license terms must be accepted` | 未在网站接受条款，见 3.2 |
| `Not logged in. Run: clawhub login` | token 失效，重新 `clawhub login` |
| `--version must be valid semver` | 版本号格式错，需 `x.y.z` |
| publish 时 `Path must be a folder` | 传的是文件路径，应传 skill 目录 |
| 服务启动报 `ImportError` | 检查是否在项目根目录、`pip install -e client/` 是否执行 |
| 客户端连不上 `ws://localhost:8765` | 服务未启动 / 端口被占 / 防火墙 |
