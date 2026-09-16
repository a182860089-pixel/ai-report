# VPS 部署

目标：Debian VPS 上跑 Postgres 16 + FastAPI（单进程，含上海 06:30/12:30/18:30 调度）+ Next.js + Caddy(:9080，因为 VPS 的 80/443 已被 nginx 占用)。

**不要**把 `password.txt`、`.env`、JWT、管理员密码推进 Git。

## 前置

- Docker Engine + Compose v2
- 开放 9080/tcp（80/443 给现有 nginx，不要抢）
- 仓库放到 `/opt/ai-report`

## 启动

```bash
cd /opt/ai-report
cp deploy/env.example .env
# 把四个密码和 JWT_SECRET 换成强随机值
chmod +x backend/docker/init-prod.sh
docker compose up -d --build
```

验收：

- `curl -fsS http://127.0.0.1:9080/healthz`
- `curl -fsS http://127.0.0.1:9080/readyz`
- `curl -fsS http://127.0.0.1:9080/api/v1/briefings/today`
- 浏览器打开 `http://<IP>:9080/` 和 `/admin/login`

调度是进程内单实例：`docker compose up --scale api=2` 会抓两次，禁止。

采集要出网。LLM writer 本阶段不上。自动付印不上。
