# AI 日报

Next.js 前端 + FastAPI 后端。页面数据走公开只读 `GET /api/v1/*`，不再读本地 mock。

`src/data/*.ts` 里的 mock 只留给后端种子对照，运行时不要再 import `catalog`。

## 启动

两个进程，缺后端前端会报错。

**1. 后端**（默认 memory，不需要 Postgres）

```powershell
cd backend
copy .env.example .env
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

健康检查：http://127.0.0.1:8000/healthz

**2. 前端**

根目录 `.env.local`：

```
API_BASE=http://127.0.0.1:8000
```

本机 8000 已被占用时，Postgres FastAPI 跑在 8001，把 `API_BASE` 改成 `http://127.0.0.1:8001` 后必须重启 Next（rewrite 只在启动时读配置）。

```powershell
npm install
npm run dev
```

打开 http://localhost:3000

浏览器搜索走同源 `/api/v1`（Next rewrite 到 FastAPI）。服务端组件直连 `API_BASE`。不要把 `NEXT_PUBLIC_API_BASE` 指到 8000，除非你同时把该 origin 加进后端 CORS。

## 页面

- `/` 今日早报 → `GET /api/v1/briefings/today`
- `/d/2026-09-13` 历史早报 → `GET /api/v1/briefings/{date}`
- `/story/claude-memory` 事件簇 → `GET /api/v1/stories/{slug}`
- `/archive` 月历 → `GET /api/v1/meta` + `GET /api/v1/briefings?from=&to=`
- `/topics`、`/topics/{slug}` → `GET /api/v1/topics`、`/topics/{slug}`
- `/sources` → `GET /api/v1/sources`
- `/search` → 客户端 `GET /api/v1/search?q=`

种子「今日」= `2026-09-14`。空日 / 未知簇 404。后端挂了走 `error.tsx`。

规格：`docs/plans/`。编辑部案头：http://localhost:3000/admin （种子账号 `admin@example.com` / `change-me-now-12`）。不要接抓取 / LLM。

## 管理后台

`/admin` 走同源 `/api/v1/admin/*`。JWT 放 sessionStorage，关标签即丢。不要设 `NEXT_PUBLIC_API_BASE`。

不要 publish 未来日期：公开 `/briefings/today` 会跟着最大 published 日走。

## 生产部署（VPS）

规格和命令见 `deploy/README.md`。仓库根目录 `docker-compose.yml` 起 Postgres 16 + FastAPI + Next + Caddy(:9080，VPS 上 80/443 已被现有 nginx 占用)。

- 调度：上海 `06:30/12:30/18:30`，API **单进程**，不要 scale
- 密钥只放服务器 `.env`，`password.txt` / `.env` 不进 Git
- 公开 today 仍是已 publish 的最大日；草稿不会抢首页
