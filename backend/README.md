# AI 日报后端（V1）

同仓独立服务。规格真值是仓库 `docs/plans/`。本目录已实现 **阶段 1 公开只读 + 阶段 3 管理端 CRUD**。前端已切 API client。

- 公开只读 REST `/api/v1`
- 管理员 JWT + 内容 CRUD（topics/sources/briefings/stories，见 `docs/plans/05`）
- PostgreSQL 16 表结构 + 种子
- 采集管线：RSS 抓取 + template 划版 + 上海 06:30/12:30/18:30 进程内调度

技术栈：FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16。时区 `Asia/Shanghai`。前端 `Text {zh,en}` 原样返回。

## 目录

```
backend/
  app/                 # Clean Architecture：domain / application / adapters
  alembic/             # 首个 revision = 02 的 DDL
  docker/init.sql      # 扩展、角色、GRANT CONNECT（只放这里）
  fixtures/            # 从 src/data mock 导出的 JSON
  tests/               # 默认内存仓储；test_postgres.py 需 AI_REPORT_PG_TEST_URL
  scripts/pg_local.py  # 无 Docker 拉起本机 PostgreSQL 16.15
```

## 内存模式（默认开发 / 测试）

不需要 Docker，不碰数据库。fixture 直接灌进 `MemoryWorld`。

```powershell
cd backend
copy .env.example .env
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --port 8000
```

`.env.example` 里 `REPOSITORY=memory`。健康检查：

- `GET /healthz` — 不碰库
- `GET /readyz` — memory 模式 ping 恒为 true

调试开着时才有 `/docs` 和 `/openapi.json`（`DEBUG=true`）。

跑测试：

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
```

默认 pytest 绿，`test_postgres.py` skip。每个测试 function-scope 新 app，避免进程内限流互相污染。实库测试见下方 pg_local。

## Postgres 模式（compose）

本机没有现成 psql 也没关系，用 compose 起 PG 16：

```powershell
cd backend
docker compose up -d postgres
$env:ALEMBIC_DATABASE_URL = "postgresql+psycopg://ai_report_migrator:ai_report_migrator@localhost:5432/ai_report"
.venv\Scripts\alembic.exe upgrade head
```

`.env` 改成：

```
REPOSITORY=postgres
DATABASE_URL=postgresql+asyncpg://ai_report_app:ai_report_app@localhost:5432/ai_report
ALEMBIC_DATABASE_URL=postgresql+psycopg://ai_report_migrator:ai_report_migrator@localhost:5432/ai_report
JWT_SECRET=please-change-me-to-a-32-byte-secret!!
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-now-12
ALLOWED_ORIGINS=http://localhost:3000
DEBUG=true
```

灌种子（幂等 upsert）：

```powershell
.venv\Scripts\python.exe -m app.adapters.db.seed
```

再启动 API：

`.env` 打开真抓取 + 每天三次：

```
REPOSITORY=postgres
PIPELINE_SCHEDULER_ENABLED=true
PIPELINE_SCHEDULE=06:30,12:30,18:30
PIPELINE_AUTO_CLUSTER=true
```

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Alembic **不要**走完整 `Settings()`（会强制 JWT）。`alembic/env.py` 只读 `ALEMBIC_DATABASE_URL` / `DATABASE_URL`。

`CREATE EXTENSION pg_trgm` 真正执行在 `docker/init.sql`（超级用户）。Alembic 里是「已存在则跳过」的 DO 块。`GRANT CONNECT` 只放 `docker/init.sql`；表级 GRANT 在 `0001_init`，角色不存在则跳过。

compose 密码仅本地草稿，生产必须换。

## Postgres 模式（无 Docker：嵌入式 16）

本机没有 Docker / 安装器时，不要装 Docker Desktop。用 zonky PostgreSQL **16.15** Windows amd64 二进制。

**PGDATA 必须是 ASCII 路径。** 仓库在 `D:\项目\...`，中文路径会让 `initdb` 直接炸，所以数据目录锁死：

`%LOCALAPPDATA%\ai-report-pg`

监听 **`127.0.0.1:55432` 只绑 IPv4**。连接串必须写 `127.0.0.1`，不要写 `localhost`（Windows 常先解析到 `::1`，`pg_hba` 会拒）。

```powershell
cd backend
.venv\Scripts\python.exe scripts\pg_local.py up
. $env:LOCALAPPDATA\ai-report-pg\env.ps1
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

`up` = 解包 → initdb → start → `docker/init.sql`（角色 + `pg_trgm`）→ Alembic → seed → verify。期望计数 **14 / 53 / 10 / 12 / 1**（briefings / stories / topics / sources / admins）。

其它命令：`start` `stop` `status` `migrate` `seed` `verify`。

连接串（`up` 会写进 `env.ps1`）：

```
DATABASE_URL=postgresql+asyncpg://ai_report_app:ai_report_app@127.0.0.1:55432/ai_report
ALEMBIC_DATABASE_URL=postgresql+psycopg://ai_report_migrator:ai_report_migrator@127.0.0.1:55432/ai_report
```

有 Docker 时仍走上面的 compose（**5432**）。两套不要混端口。compose 才是有容器时的正路。

跑实库对拍：

```powershell
. $env:LOCALAPPDATA\ai-report-pg\env.ps1
.venv\Scripts\python.exe -m pytest tests/integration/test_postgres.py -q
```

失败先看 `%LOCALAPPDATA%\ai-report-pg\log\postgresql.log`。需要 VC++ 2015+ runtime（`msvcp140.dll` / `vcruntime140.dll`）。

## 限流（单实例）

V1 用进程内滑动窗口，**不跨多 worker / 多副本**：

| 桶 | 限制 |
|---|---|
| 公开 GET `/api/v1/*` | 60 / min / IP |
| `GET /api/v1/search` | 10 / min / IP |
| `POST /api/v1/auth/login` | 5 / min / IP |
| `POST /api/v1/auth/refresh` | 20 / min / IP |
| `/healthz` `/readyz` OPTIONS | 不限 |

超限 `429 RATE_LIMITED`，带 `Retry-After`。多实例之前不要把这套当集群方案。

## 鉴权

- 公开 GET **不解析** `Authorization`；坏 Bearer 仍 200
- 管理员 JWT：HS256（`JWT_SECRET` ≥ 32 字节）或 RS256，互斥
- access 15 min，refresh 7 天只存 SHA-256 hex，登录后轮转
- 登录失败统一 `401 Invalid credentials.`，不枚举邮箱
- 停用账号 login 401，持有旧 access 调 `/admin/me` → 403

种子管理员：`admin@example.com` / `change-me-now-12`

## 契约要点

成功 `{ "data": ... }`，错误 `{ "error": { "code", "message" } }`。空日 / 未知簇 404。`updatedAt` / `lastFetch` 序列化成 `HH:mm` 或 `—`。

前端映射见 `docs/plans/01-后端开发计划书.md`。字段与状态码以 `03` 为准，列与约束以 `02` 为准，鉴权限流以 `04` 为准。
