# 部署指南

## 本地部署

### 快速启动

```bash
pip install claw-service-hub
python -m server.main
```

### 配置

支持通过环境变量配置：

```bash
# .env 文件
HUB_HOST=0.0.0.0
HUB_PORT=8765
LOG_LEVEL=INFO
STORAGE_TYPE=memory  # 或 file
```

详见 [.env.example](../.env.example)

---

## Docker 部署

### 使用 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  hub:
    image: claw-service-hub:latest
    ports:
      - "8765:8765"
    environment:
      - HUB_HOST=0.0.0.0
      - HUB_PORT=8765
    volumes:
      - ./data:/app/data
```

```bash
docker-compose up -d
```

### 构建自定义镜像

```bash
docker build -t claw-service-hub:custom .
```

---

## 生产环境部署

### 使用 systemd (Linux)

```ini
# /etc/systemd/system/claw-hub.service
[Unit]
Description=Claw Service Hub
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/claw-hub
ExecStart=/usr/bin/python -m server.main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable claw-hub
sudo systemctl start claw-hub
```

### 使用 PM2 (Node.js 生态)

```bash
pip install -e .
pm2 start "python -m server.main" --name claw-hub
```

---

## 负载均衡

对于大规模部署，可以使用 Nginx 作为 WebSocket 负载均衡器：

```nginx
upstream hub_cluster {
    server 127.0.0.1:8765;
    server 127.0.0.1:8766;
    server 127.0.0.1:8767;
}

map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 8765;
    location / {
        proxy_pass http://hub_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
    }
}
```

---

## 监控

### 健康检查

```bash
curl http://localhost:8765/health
# {"status": "ok", "services": 5}
```

### 日志

默认日志输出到 stdout。生产环境建议配置日志收集：

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## 安全建议

1. **使用防火墙**限制对 8765 端口的访问
2. **启用 TLS**（需要配置 SSL 证书）
3. **认证机制**（计划中）
4. **速率限制**（计划中）

---

## 下一步

- 📖 查看 [API 参考](api.md)
- 📖 查看 [故障排查](./troubleshooting.md)