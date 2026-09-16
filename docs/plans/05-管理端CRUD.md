# 05 · 管理端 CRUD

规格版本：阶段 3  
前置：V1 已落地（公开只读 + auth 脚手架）。**不改** `01`–`04` 已锁死的 V1 示例。  
本文件是阶段 3 的**唯一写接口契约**。冲突时：本文件管管理端路径/allowlist/409；公开 GET 仍服从 `03`；列约束服从 `02`；鉴权/限流服从 `04` + 本节增量。

技能依据：Clean Architecture 模块化单体、REST 资源名词、allowlist、参数化 SQL。不做管理后台页面、不做抓取、不做 LLM。

## 1. 范围

做：

- `GET/POST/PATCH/DELETE /api/v1/admin/{topics,sources,briefings,stories}`
- `POST /api/v1/admin/briefings/{date}/publish|unpublish`
- `GET /api/v1/admin/audit`
- 已有 `GET /api/v1/admin/me` **不动**
- memory + postgres 两边同一套端口
- 每次 mutation 写 `audit_logs`
- refresh 重放 → family revoke（仍 401，不 409）
- CORS 放行 `PATCH`/`DELETE`；写接口 20/min/IP；admin JSON body 64KB

不做：

- 管理后台 UI、`src/` 公开页改动
- 采集表、出网、RSS、LLM
- 用户注册/收藏、Redis、cookie session、CSRF token
- 改公开 `mustRead` 形状、改脉搏为实时聚合
- 把内部 `BIGINT`、`password_hash`、`token_hash` 暴露到 JSON

## 2. 架构

继续同仓模块化单体：`domain` / `application` / `adapters/api` / `adapters/{memory,db}`。

新增写端口：

- `AdminCatalogRepository`：topics / sources
- `AdminEditorialRepository`：briefings / stories（含 draft）
- `IdentityRepository.list_audits`

用例：`application/admin.py`。路由：`adapters/api/routers/admin.py`，前缀 `/api/v1/admin`。

对外资源键仍是 `date` / `slug` / `source.code`。JSON **禁止**内部 id。

公开 GET 只读 `status=published` 且 `topics.is_active=true`。Admin GET 可见 draft 与 inactive。草稿不得泄漏到公开端点。

时区 `Asia/Shanghai`。双语字段始终 `{zh,en}`，不按 `Accept-Language` 裁切。

## 3. 鉴权与安全增量

| 项 | 规则 |
|---|---|
| 鉴权 | 全部 `/api/v1/admin/*`（含 GET 列表）要求 `Authorization: Bearer <access>` |
| 停用 | `is_active=false` → `403 FORBIDDEN` / `Account disabled.`（与 `/me` 相同） |
| 缺/坏 token | `401 UNAUTHORIZED` / `Invalid access token.` |
| 未知字段 | **422** `VALIDATION_ERROR` / `Unknown field.`（禁止 mass assignment） |
| 写限流 | `POST/PATCH/DELETE /api/v1/admin/*` **20/min/IP**；admin GET 仍 60 |
| Body | login 仍 8KB；**admin 写 64KB**；超限 `400 BAD_REQUEST` / `Request body too large.` |
| CORS | `allow_methods` = GET, POST, PATCH, DELETE, OPTIONS；origin 白名单不变 |
| Refresh 重放 | hash 能查到且已撤销/过期 → `revoke_all_refresh(user)`，响应仍 `401` / `Invalid refresh token.`。完全未知 hash 只 401，不扫用户 |
| URL | 只存 `https://` 且 ≤500，**不发外站请求**（对齐 `02` CHECK，http 422） |
| 审计 | 每个成功 mutation 一条；metadata 无密码、无 token、无内部 id |
| 错误 | 仍 `{error:{code,message}}`，无堆栈。阶段 3 **启用 HTTP 409** `CONFLICT` |

无 cookie，无 CSRF。Bearer only。

## 4. 信封与错误码

成功：`{ "data": ... }`。列表：`{ "data": { "items": [...] } }`。删除：`{ "data": { "ok": true } }`。

| HTTP | code | 何时 |
|---|---|---|
| 200 | — | GET / PATCH / publish / unpublish / DELETE |
| 201 | — | POST 创建 |
| 401 | UNAUTHORIZED | 缺/坏 access |
| 403 | FORBIDDEN | 账号停用 |
| 404 | NOT_FOUND | 未知 slug/code/date |
| 409 | CONFLICT | 唯一键冲突；删 published；删仍被引用的 topic/source |
| 422 | VALIDATION_ERROR | 格式、长度、未知字段、不可变键被改 |
| 429 | RATE_LIMITED | 写 20/min 或其它桶 |

## 5. 不可变键与删除规则

| 资源 | 创建唯一 | PATCH 不可改 | 删除 |
|---|---|---|---|
| Topic | `slug` | `slug` | 任意 story 引用 → 409 `Topic still has stories.`；0 簇硬删。也可用 `isActive=false` 下架 |
| Source | `id`（=`code`） | `id` | 任意 citation.`source_id` → 409 `Source still has citations.` |
| Briefing | `date` | `date` | published → 409 `Cannot delete a published briefing.`；draft 可删，**级联删除**其簇 |
| Story | `slug` | `slug` | 硬删；随后重建该日 must/more |

故事必须挂**已存在**的 briefing + topic。draft briefing 的 story：admin 可见，公开 404。

改 story（含创建/删除/改 section/rank/date）后必须重建该日 `mustRead`/`more` 与 `mustReadCount`。脉搏快照**不**随簇数量重算。

## 6. Allowlist 与长度（对齐 `02` CHECK）

未知字段 422。缺必填 / 类型错 / 超长 / 空串 / 控制字符 → 422 `Invalid payload.`（slug/date/time/url 用各自更具体的 message）。

### Topic

POST 必填：`slug, name, blurb`。可选：`sortOrder`（默认 0）。`isActive` 创建时默认 true，POST 里出现则 422（创建后再 PATCH）。

PATCH 允许：`name, blurb, sortOrder, isActive`。出现 `slug` 且与当前不同 → 422 `Slug cannot be changed.`；相同则忽略。

| 字段 | 约束 |
|---|---|
| slug | kebab，1–64 |
| name.zh/en | 1–80 |
| blurb.zh/en | 1–240 |
| sortOrder | 整数 0–1_000_000 |
| isActive | bool |

### Source

POST 必填：`id, name, status, detail`。可选：`lastFetch, todayCount, consecutiveFailures, isQuarantined, homepageUrl, feedUrl`。

PATCH 允许除 `id` 外以上字段。改 `id` → 422 `Code cannot be changed.`

| 字段 | 约束 |
|---|---|
| id | kebab，1–64，对 `sources.code` |
| name | 1–120 |
| status | `ok\|late\|bad` |
| lastFetch | `HH:mm` 或 `—` / null → `last_fetch_at` |
| todayCount | 整数 ≥0，默认 0 |
| consecutiveFailures | 整数 ≥0，默认 0 |
| isQuarantined | bool，默认 false |
| detail.zh/en | 1–240 |
| homepageUrl / feedUrl | null、省略、`""`→null；否则必须 `https://` 且 ≤500 |

公开 `GET /api/v1/sources` **仍不返回** URL / consecutiveFailures / isQuarantined。

### Briefing

POST 必填：`date, title, moreHeading, lede, pulse, updatedAt`。可选：`weekday`（缺则按 `date` + `Asia/Shanghai` 算：`星期一`/`Monday`）。默认 `status=draft`。POST 出现 `status`/`mustRead`/`more` → 422。

PATCH 允许：`title, weekday, moreHeading, lede, pulse, updatedAt`。改 `date` → 422 `Date cannot be changed.`。改状态只走 publish/unpublish。

| 字段 | 约束 |
|---|---|
| date | `YYYY-MM-DD` |
| title.zh/en | 1–200 |
| weekday.zh/en | 1–16 |
| moreHeading.zh/en | 1–80 |
| lede | 0–20 条 Text，每条 1–400 |
| updatedAt | `HH:mm` → `published_at`（草稿也存这个墙钟） |
| pulse.clusters/articles/healthy/totalSources | 整数 ≥0；`healthy <= totalSources` |
| pulse.zhEn | 1–32 |
| pulse.topics | 0–20；name 1–80；count ≥0 |

脉搏是**快照**：CRUD 写 `briefing_pulse*`，禁止用 `COUNT(stories)` / `COUNT(sources)` 覆盖。

### Story

POST 必填：`slug, date, topicSlug, section, title, dek, synthesis, timeline, sources`。`rank`：`must` 必填且 >0；`more` 无论传入什么**入库 NULL**。

PATCH 允许：`date, topicSlug, section, rank, title, dek, synthesis, timeline, sources`。改 slug → 422。改 `date` 时目标早报必须已存在，然后重建旧日与新日排序。

| 字段 | 约束 |
|---|---|
| slug | kebab，1–80 |
| date | 已存在的 briefing.date |
| topicSlug | 已存在的 topic.slug（含 inactive） |
| section | `must\|more` |
| rank | must：整数 >0；more：忽略 |
| title 1–200；dek 1–400 | Text |
| synthesis | 0–40，每条 1–2000 |
| timeline | 0–40；`time`=`HH:mm`；text 1–400；`occurred_at` = 早报日 + 时分 + 上海 |
| sources[] | 0–40；`name` 1–120；`lang` `zh\|en`；`kind` 1–32；`time` HH:mm；`sourceCode` 可选，若给则必须是已有 code |

`sourceCode` 缺省：`source_id` 空，只存 `source_name`（对齐 Wired 等不在目录里的引用）。

## 7. 端点

鉴权：全部 Bearer + active admin。限流：GET 60；写 20。

时间字段对外：`updatedAt` / `lastFetch` / timeline.`time` / citation.`time` = `HH:mm` 或 `—`。

Admin 列表/详情在公开形状上加私有字段，**不加**内部 BIGINT。

---

### 7.1 `GET /api/v1/admin/topics`

200：

```json
{
  "data": {
    "items": [
      {
        "slug": "models",
        "name": { "zh": "模型发布", "en": "Model launches" },
        "blurb": { "zh": "GPT-5.5 降价 · Claude 记忆层", "en": "GPT-5.5 price cut · Claude memory" },
        "clusterCount": 5,
        "sortOrder": 0,
        "isActive": true
      }
    ]
  }
}
```

`clusterCount` 计**所有**挂到该专题的簇（含 draft 早报）。公开 GET 仍只计 published。含 inactive。排序 `sort_order, id`。

401/403 见 §3。

---

### 7.2 `GET /api/v1/admin/topics/{slug}`

200：列表项字段 + `stories: StorySummary[]`（含 draft 日的簇）。404 `Unknown topic.` 未知 slug（inactive 仍 200）。非法 slug 422 `Invalid slug.`

---

### 7.3 `POST /api/v1/admin/topics`

201 示例请求：

```json
{
  "slug": "eval-tools",
  "name": { "zh": "评测工具", "en": "Eval tools" },
  "blurb": { "zh": "新套件", "en": "New suites" },
  "sortOrder": 20
}
```

201 `data` 同列表项（`clusterCount=0`, `isActive=true`）。

409 `Topic slug already exists.`  
422 未知字段 / 非法 slug / 超长。

审计：`action=topic.create` `resource=topics/eval-tools`。

---

### 7.4 `PATCH /api/v1/admin/topics/{slug}`

```json
{ "isActive": false, "sortOrder": 9 }
```

200 返回更新后对象。404 未知。409 不适用。把 `isActive=false` 后公开 `GET /topics` 与 `GET /topics/{slug}` 立即看不到。

---

### 7.5 `DELETE /api/v1/admin/topics/{slug}`

200 `{ "data": { "ok": true } }`  
409 `Topic still has stories.`  
404 `Unknown topic.`

---

### 7.6 `GET /api/v1/admin/sources`

200 `items[]`：公开 Source 字段 + `consecutiveFailures` + `isQuarantined` + `homepageUrl` + `feedUrl`。

```json
{
  "id": "lab-rss",
  "name": "某实验室 RSS",
  "status": "bad",
  "lastFetch": "—",
  "todayCount": 0,
  "detail": { "zh": "…", "en": "…" },
  "consecutiveFailures": 2,
  "isQuarantined": true,
  "homepageUrl": null,
  "feedUrl": null
}
```

公开 JSON 继续只有 `id,name,status,lastFetch,todayCount,detail`。

---

### 7.7 `POST /api/v1/admin/sources`

201：

```json
{
  "id": "papers-with-code",
  "name": "Papers with Code",
  "status": "ok",
  "lastFetch": "06:00",
  "todayCount": 0,
  "consecutiveFailures": 0,
  "isQuarantined": false,
  "detail": { "zh": "正常", "en": "Healthy" },
  "homepageUrl": "https://paperswithcode.com",
  "feedUrl": null
}
```

`http://example.com` → 422 `Invalid URL.`  
409 `Source code already exists.`

---

### 7.8 `PATCH /api/v1/admin/sources/{code}` / `DELETE`

PATCH 200 更新后对象。DELETE 200 `{ok:true}`。有引用 409 `Source still has citations.` 404 `Unknown source.`

---

### 7.9 `GET /api/v1/admin/briefings?from=&to=`

query 与公开归档相同（必填 from/to，跨度 ≤62 天，非法 422 `Invalid date range.`）。**含 draft**。每项 = 公开 `BriefingListItem` + `status`。

```json
{
  "data": {
    "items": [
      {
        "date": "2026-09-15",
        "weekday": { "zh": "星期二", "en": "Tuesday" },
        "title": { "zh": "草稿", "en": "Draft" },
        "updatedAt": "07:00",
        "mustReadCount": 0,
        "clusters": 0,
        "status": "draft"
      }
    ]
  }
}
```

`clusters` 来自脉搏**快照**，不是 COUNT(stories)。

---

### 7.10 `GET /api/v1/admin/briefings/{date}`

200 = 公开 `briefing_out` + `status`。draft 也 200。公开同日 404。非法 date 422。未知 404 `No briefing for this date.`

---

### 7.11 `POST /api/v1/admin/briefings`

201 默认 draft。`mustRead`/`more` 空数组。

```json
{
  "date": "2026-09-15",
  "title": { "zh": "草稿日", "en": "Draft day" },
  "moreHeading": { "zh": "更多", "en": "More" },
  "lede": [{ "zh": "要点", "en": "Lede" }],
  "updatedAt": "07:00",
  "pulse": {
    "clusters": 0,
    "articles": 0,
    "zhEn": "0 : 0",
    "healthy": 0,
    "totalSources": 26,
    "topics": []
  }
}
```

409 `Briefing date already exists.`

---

### 7.12 `PATCH /api/v1/admin/briefings/{date}`

200 更新后详情（含 status）。不改 status。

---

### 7.13 `POST /api/v1/admin/briefings/{date}/publish`

200，`status=published`。已 published 则幂等 200。公开立即可见。404 未知日。

---

### 7.14 `POST /api/v1/admin/briefings/{date}/unpublish`

200，`status=draft`。已 draft 幂等 200。公开立即 404。

---

### 7.15 `DELETE /api/v1/admin/briefings/{date}`

draft：级联删簇后 200 `{ok:true}`。  
published：409 `Cannot delete a published briefing.`

---

### 7.16 `GET /api/v1/admin/stories?date=&topic=`

`date`/`topic` 均可选。非法格式 422。未知 topic slug 格式合法但不存在 → 空列表（不 404）。返回 `StorySummary[]`，含 draft 日，按 date DESC、must 先、rank、id。

---

### 7.17 `GET /api/v1/admin/stories/{slug}`

200 = 公开 `story_out`，且每条 citation 多 `sourceCode`（可 null）。draft 日也 200。404 `Unknown cluster.`

```json
{
  "name": "Wired",
  "lang": "en",
  "kind": { "zh": "媒体", "en": "Press" },
  "time": "06:40",
  "sourceCode": null
}
```

公开 `GET /stories/{slug}` **不带** `sourceCode`。

---

### 7.18 `POST /api/v1/admin/stories`

201。`date` 必须已有 briefing（draft 亦可）。`topicSlug` 必须已有。

```json
{
  "slug": "draft-eval-suite",
  "date": "2026-09-15",
  "topicSlug": "research",
  "section": "must",
  "rank": 1,
  "title": { "zh": "新评测", "en": "New eval" },
  "dek": { "zh": "摘要", "en": "Dek" },
  "synthesis": [{ "zh": "段", "en": "Para" }],
  "timeline": [{ "time": "06:00", "text": { "zh": "发生", "en": "Happened" } }],
  "sources": [
    {
      "name": "OpenAI Blog",
      "lang": "en",
      "kind": { "zh": "一手", "en": "Primary" },
      "time": "06:12",
      "sourceCode": "openai-blog"
    }
  ]
}
```

409 `Story slug already exists.`  
422 未知 briefing/topic/sourceCode：`Unknown briefing.` / `Unknown topic.` / `Unknown source.`

创建后重建该日 must/more。

---

### 7.19 `PATCH /api/v1/admin/stories/{slug}` / `DELETE`

PATCH 200 详情。DELETE 200 `{ok:true}`。之后重建相关日排序。

---

### 7.20 `GET /api/v1/admin/audit?limit=`

`limit` 默认 50，1–200，非法 422 `Invalid payload.`  
按 `id DESC`。**不要** `actor_id`。

```json
{
  "data": {
    "items": [
      {
        "action": "topic.create",
        "resource": "topics/eval-tools",
        "createdAt": "2026-09-14T01:00:00Z",
        "actorEmail": "admin@example.com",
        "metadata": { "slug": "eval-tools" }
      }
    ]
  }
}
```

`createdAt` 为 UTC ISO-8601（`Z`）。login/refresh 产生的审计也会出现。只读。

## 8. 审计 action 表

| action | resource |
|---|---|
| topic.create/update/delete | `topics/{slug}` |
| source.create/update/delete | `sources/{code}` |
| briefing.create/update/publish/unpublish/delete | `briefings/{date}` |
| story.create/update/delete | `stories/{slug}` |
| refresh_replay | `auth`（family revoke 时） |

## 9. 实现目录

```
backend/app/application/admin.py          # 用例 + allowlist 解析
backend/app/adapters/api/routers/admin.py
backend/app/adapters/memory/repositories.py  # 写实现
backend/app/adapters/db/admin_repositories.py
```

测试走 memory。本机不要求 docker/psql。

## 10. 验收

- [ ] 无 token / 坏 token 调任意 admin 写 → 401
- [ ] 停用账号持旧 access 写 → 403 `Account disabled.`
- [ ] 未知字段（如 `id` 塞进 topic POST）→ 422 `Unknown field.`
- [ ] 重复 slug/code/date → 409
- [ ] 有簇的 topic 不能删；inactive 后面公开列表消失
- [ ] 有 citation 的 source 不能删；公开 JSON 仍无 URL
- [ ] 新建 briefing 默认 draft；公开 404；publish 后公开 200；unpublish 再 404
- [ ] 不能删 published；能删 draft（簇一起没）
- [ ] draft 日 story 公开 404；admin GET 200
- [ ] more 的 rank 响应为 `null`
- [ ] 改 story 后当日 must 按 rank 重排；脉搏 clusters 不被重写
- [ ] mutation 后 `GET /admin/audit` 看得到对应 action
- [ ] refresh 轮转后再用旧 refresh → 401，且新 refresh 也 401（family revoke）
- [ ] 第 21 次 admin 写 → 429
- [ ] 公开种子今日早报仍 8 must + 3 more，`pulse.totalSources=26`
- [ ] `http://` 信源 URL 422；`https://` 可存且不发请求

## 11. Out of Scope（本阶段仍不做）

阶段 4 采集管线、管理后台页面、cookie 登录、分布式限流、对象存储。
