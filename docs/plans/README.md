# AI 日报 · 后端计划书

本目录是后续 `backend/` 实现的**唯一规格**。先读完再写代码，不要另开一份「更合理」的表名或路径。

V1 公开只读 API 已在 `backend/`。阶段 2 前端 `src/data` 已换成 `src/lib/api.ts`。阶段 3 管理端 CRUD 以 [05-管理端CRUD.md](./05-管理端CRUD.md) 为唯一写接口规格；**不要改** 01–04 已锁死的 V1 示例。阶段 3 不改公开契约。`/admin` 编辑部案头见 [06-管理后台.md](./06-管理后台.md)。阶段 4 采集管线见 [07-采集管线.md](./07-采集管线.md)。RSS 抓取 + template 划版；进程内每天三次。不上 LLM，不自动付印。

## 阅读顺序

1. [01-后端开发计划书.md](./01-后端开发计划书.md) — 范围、架构、前端映射、目录、阶段、验收
2. [02-库表设计.md](./02-库表设计.md) — PostgreSQL DDL、ERD、索引、种子
3. [03-API契约.md](./03-API契约.md) — REST `/api/v1` 每个端点的请求/响应
4. [04-API安全设计.md](./04-API安全设计.md) — 鉴权、限流、校验、DB 权限、威胁对照
5. [05-管理端CRUD.md](./05-管理端CRUD.md) — 阶段 3 管理端写接口（V1 公开契约仍以 01–04 为准）
6. [06-管理后台.md](./06-管理后台.md) — `/admin` 编辑部案头（JWT sessionStorage，不改 01–05）
7. [07-采集管线.md](./07-采集管线.md) — 阶段 4 采集 / 划版（不改 01–05；06 只补路由）

## V1 边界

| 做 | 不做 |
|---|---|
| FastAPI + PostgreSQL 16 公开只读 API | 采集、RSS、外站请求 |
| 从现有 `src/data` mock 灌种子 | 抓取、RSS、外站请求 |
| 管理员 JWT 登录 / 刷新 / me 脚手架 | 普通用户注册、收藏、订阅 |
| 中英双语字段始终返回 | 按 `Accept-Language` 裁切 |
| RSS 抓取 + template 划版 + 每天三次进程内调度 | LLM 撰写、自动付印、系统 cron |
| OpenAPI 与契约文档一致 | 微服务 / CQRS / Temporal / Redis |

## 种子规模（锁死，来自当前 mock）

| 对象 | 数量 | 来源 |
|---|---|---|
| 早报 | 14 | `2026-09-01` … `2026-09-14` |
| 事件簇 | **53** | 今日 **8 must + 3 more** + 近况 7 + 早期种子 21 + 后期种子 14 |
| 专题 | 10 | `src/data/topics.ts` |
| 信源目录 | 12 | 同上；脉搏快照 `totalSources=26`，禁止改成 12 |
| 管理员 | 1 | 仅 env，不进 git |

「今日」=`2026-09-14`，`updatedAt=07:12`，脉搏 `14 / 86 / 4 : 3 / 24/26`。

`stories-today-more.ts` **文件名有误导**：里面 4 条是 `section: "must"`（`llama-41-8b` rank 5、`rubin-supply` rank 6、`eu-ai-act-phase-2` rank 7、`glm-agent-bench` rank 8），真正 more 只有 `diffusion-lm-code` / `hf-free-tier` / `tongyi-cockpit`。灌库以 `section` 字段为准，禁止按文件名把 llama 写成 more。

## 已锁定的技术选择

- 同仓独立服务：后续实现放 `backend/`
- Python 3.12、FastAPI、SQLAlchemy、Alembic
- PostgreSQL 16，时区 `Asia/Shanghai`
- 模块化单体 + Clean Architecture
- 对外键：`date` / `slug` / `source.code`；内部 PK：`BIGINT IDENTITY`
- 成功包 `{ "data": ... }`，错误包 `{ "error": { "code", "message" } }`

## 前端对齐对象

现有页面（全部只读）：

- `/` 今日早报
- `/d/{date}` 历史早报
- `/story/{slug}` 事件簇
- `/archive` 月历
- `/topics`、`/topics/{slug}` 专题
- `/sources` 信源健康
- `/search` 搜索事件簇

类型源：`src/data/types.ts`。数据访问源：`src/data/index.ts`。
