# 03 · API 契约

Base URL：`http://localhost:8000`（实现阶段）  
前缀：`/api/v1`（health 除外）  
版本策略：URL 版本。破坏性变更才开 `/api/v2`。  
Content-Type：`application/json; charset=utf-8`  
时区：`Asia/Shanghai`  
鉴权：公开 GET 无 token。管理员接口 `Authorization: Bearer <access>`。

实现必须先注册静态路径（`/briefings/today`）再注册参数路径（`/briefings/{date}`）。

200 示例优先用当前 mock 真值，方便阶段 1 做快照测试。形状以本节为准；个别 dek 全文见 `src/data`。

## 0. 约定

### 信封

成功 HTTP 2xx：

```json
{ "data": {} }
```

失败 4xx/5xx：

```json
{ "error": { "code": "NOT_FOUND", "message": "No briefing for this date." } }
```

`message` 用英文短句，不回内部细节。前端是否翻译不在 V1 范围。

### 错误码

| HTTP | code | 何时 |
|---|---|---|
| 400 | `BAD_REQUEST` | JSON 解析失败等 |
| 401 | `UNAUTHORIZED` | 缺/坏 access 或 refresh |
| 403 | `FORBIDDEN` | 账号停用 |
| 404 | `NOT_FOUND` | 空日、未知簇、未知专题 |
| 415 | `BAD_REQUEST` | 错误 Content-Type（可并入 400） |
| 422 | `VALIDATION_ERROR` | 参数格式/长度不合法 |
| 429 | `RATE_LIMITED` | 触发限流 |
| 500 | `INTERNAL_ERROR` | 未预期；不带堆栈 |
| 503 | `INTERNAL_ERROR` | `/readyz` 库不可达 |

V1 **不使用 HTTP 409**。refresh 重放、未知、过期一律 `401 UNAUTHORIZED` + `Invalid refresh token.`，避免泄露 token 是否曾存在。

### 端点总表

| 方法 | 路径 | 鉴权 | 限流键 | 典型 200 | 404 | 422 |
|---|---|---|---|---|---|---|
| GET | `/healthz` | 公开 | 不限 | `status=ok` | 无 | 无 |
| GET | `/readyz` | 公开 | 不限 | `status=ready` | 无 | 无（库挂 503） |
| GET | `/api/v1/meta` | 公开 | 60/min/IP | `currentDate` | 无 | 无 |
| GET | `/api/v1/briefings/today` | 公开 | 60/min/IP | 今日早报，must 8 + more 3 | 无 published | 无 |
| GET | `/api/v1/briefings/{date}` | 公开 | 60/min/IP | 同 today 形状 | 空日 | 非法 date |
| GET | `/api/v1/briefings` | 公开 | 60/min/IP | 归档列表 | 无（空数组） | 缺/非法 from-to |
| GET | `/api/v1/stories/{slug}` | 公开 | 60/min/IP | Story 详情 | 未知簇 | 非法 slug |
| GET | `/api/v1/topics` | 公开 | 60/min/IP | 10 专题 | 无 | 无 |
| GET | `/api/v1/topics/{slug}` | 公开 | 60/min/IP | 专题+簇 | 未知专题 | 非法 slug |
| GET | `/api/v1/sources` | 公开 | 60/min/IP | 12 信源 | 无 | 无 |
| GET | `/api/v1/search` | 公开 | 10/min/IP | 扁平 StorySummary[] | 无（空数组） | q 缺失或 >100 |
| POST | `/api/v1/auth/login` | 公开 | 5/min/IP | tokens + email | 无 | 缺字段 |
| POST | `/api/v1/auth/refresh` | body refresh | 20/min/IP | 新 tokens | 无 | 缺 token |
| POST | `/api/v1/auth/logout` | access 或 refresh | 60/min/IP | `{ok:true}` | 无 | 两者都缺 |
| GET | `/api/v1/admin/me` | Bearer access | 60/min/IP | `{email}` | 无 | 无 |

限流数值、安全头、dummy hash、DB 角色见 `04`。本文件锁字段与状态码。

### 公共 JSON 形状（对齐 `src/data/types.ts`）

```ts
type Text = { zh: string; en: string };

type StorySummary = {
  slug: string;
  date: string;            // YYYY-MM-DD
  topicSlug: string;
  rank: number | null;
  section: "must" | "more";
  title: Text;
  dek: Text;
  topic: { slug: string; name: Text };
  sourceCount: number;
  sourceNames: string[];   // 最多 3 个，引用顺序
};

type SourceRef = {
  name: string;
  lang: "zh" | "en";
  kind: Text;
  time: string;            // HH:mm
};

type TimelineItem = {
  time: string;            // HH:mm
  text: Text;
};
```

`StorySummary` 是 V1 为避免 N+1 新增的；其余字段名与 `types.ts` 一致。

时钟格式化：`TIMESTAMPTZ` → 上海时区 `HH:mm`。`last_fetch_at` 为空 → `"—"`。

公开 GET 一律不返回内部数字 `id`。`Source.id` 对外等于 `sources.code`。

---

## 1. `GET /healthz`

- 方法 / 路径：`GET /healthz`（无 `/api/v1`）
- 鉴权：公开
- Query / Path：无
- 用途：进程存活，不碰数据库
- 200：

```json
{ "data": { "status": "ok" } }
```

无 404。无 422。

---

## 2. `GET /readyz`

- 方法 / 路径：`GET /readyz`
- 鉴权：公开
- Query / Path：无
- 用途：Postgres 可连接
- 200：

```json
{ "data": { "status": "ready" } }
```

- 503（库不可达，仍走错误信封）：

```json
{ "error": { "code": "INTERNAL_ERROR", "message": "Database unavailable." } }
```

无 404。无 422。

---

## 3. `GET /api/v1/meta`

- 方法 / 路径：`GET /api/v1/meta`
- 鉴权：公开
- Query / Path：无
- 200：`currentDate` = 已发布早报最大 `date`（种子为 `2026-09-14`），不是服务器日历。

```json
{
  "data": {
    "currentDate": "2026-09-14",
    "timezone": "Asia/Shanghai"
  }
}
```

无 404。无 422。

---

## 4. `GET /api/v1/briefings/today`

- 方法 / 路径：`GET /api/v1/briefings/today`
- 鉴权：公开
- Query / Path：无
- 等价于对 `meta.currentDate` 调用下一节。无 published 早报时 404。
- 200 示例（字段需能驱动 `BriefingView` + Footer；`mustRead`/`more` 此处各举 1 条，完整种子 **8 must + 3 more**）：

```json
{
  "data": {
    "date": "2026-09-14",
    "weekday": { "zh": "星期一", "en": "Monday" },
    "updatedAt": "07:12",
    "title": {
      "zh": "发布周对撞：闭源降价，开源抢榜",
      "en": "Launch week collision: closed models cut price, open weights grab the board"
    },
    "lede": [
      {
        "zh": "OpenAI 把 GPT-5.5 长上下文默认开到 1M，推理价腰斩。",
        "en": "OpenAI makes 1M context the GPT-5.5 default and halves inference price."
      },
      {
        "zh": "Anthropic 上线跨会话记忆，企业默认关闭。",
        "en": "Anthropic ships cross-session memory, off by default for enterprises."
      },
      {
        "zh": "Kimi 新权重部分开源，LMSYS 冲进前五。",
        "en": "Kimi partially open-sources new weights and cracks LMSYS top five."
      }
    ],
    "moreHeading": { "zh": "更多 · 开源与研究", "en": "More · Open source & research" },
    "pulse": {
      "clusters": 14,
      "articles": 86,
      "zhEn": "4 : 3",
      "healthy": 24,
      "totalSources": 26,
      "topics": [
        { "name": { "zh": "模型发布", "en": "Model launches" }, "count": 4 },
        { "name": { "zh": "开源权重", "en": "Open weights" }, "count": 3 },
        { "name": { "zh": "芯片供应", "en": "Chip supply" }, "count": 2 },
        { "name": { "zh": "政策合规", "en": "Policy" }, "count": 2 },
        { "name": { "zh": "机器人", "en": "Robotics" }, "count": 1 }
      ]
    },
    "mustRead": [
      {
        "slug": "gpt-55-price",
        "date": "2026-09-14",
        "topicSlug": "models",
        "rank": 1,
        "section": "must",
        "title": {
          "zh": "GPT-5.5 API 推理价腰斩，1M 上下文改默认",
          "en": "GPT-5.5 API inference halved; 1M context becomes default"
        },
        "dek": {
          "zh": "价格战打到推理层。媒体和开发者都在算：长文档工作流会不会从 Claude 回流。",
          "en": "The price war hit inference. Press and developers are both doing the math: will long-doc workflows flow back from Claude?"
        },
        "topic": {
          "slug": "models",
          "name": { "zh": "模型发布", "en": "Model launches" }
        },
        "sourceCount": 6,
        "sourceNames": ["OpenAI Blog", "The Verge", "机器之心"]
      }
    ],
    "more": [
      {
        "slug": "diffusion-lm-code",
        "date": "2026-09-14",
        "topicSlug": "research",
        "rank": null,
        "section": "more",
        "title": {
          "zh": "扩散语言模型在代码补全追上自回归",
          "en": "Diffusion LMs catch autoregressive models on code completion"
        },
        "dek": {
          "zh": "延迟曲线第一次看起来能进编辑器。",
          "en": "The latency curve looks editor-ready for the first time."
        },
        "topic": {
          "slug": "research",
          "name": { "zh": "研究", "en": "Research" }
        },
        "sourceCount": 2,
        "sourceNames": ["arXiv", "GitHub"]
      }
    ]
  }
}
```

说明：

- `mustRead` 按 `rank` 升序，种子 **8** 条：
  1. `gpt-55-price`
  2. `claude-memory`
  3. `kimi-open-weights`
  4. `gemini-robotics-2`
  5. `llama-41-8b`（`section=must`，`rank=5`。文件在 `stories-today-more.ts`，**不是 more**）
  6. `rubin-supply`
  7. `eu-ai-act-phase-2`
  8. `glm-agent-bench`
- `more` 按 `stories.id ASC`（种子插入顺序 = `catalog.ts` 的 `stories` 数组），种子 **3** 条：`diffusion-lm-code`、`hf-free-tier`、`tongyi-cockpit`。
- `llama-41-8b` 真值：title `Llama 4.1 8B：手机端 30 tok/s` / `Llama 4.1 8B: 30 tok/s on phones`；`sourceNames` = `["Meta", "GitHub", "量子位"]`；`sourceCount` = 3。禁止用捏造 dek，禁止把 Hugging Face 写成它的信源。
- `pulse.totalSources` 来自快照，是 26，禁止改成 12。`clusters` 是 14，禁止改成 11。
- `updatedAt` 为 `published_at` 的 `HH:mm`，今日为 `07:12`。
- Footer 用 `mustRead.length`，种子今日是 **8**。
- 无 published 早报：`404 NOT_FOUND`

```json
{ "error": { "code": "NOT_FOUND", "message": "No briefing for this date." } }
```

无 422（无参数）。上例 `more` 只举第 1 条真值；实现必须返回全部 3 条。

---

## 5. `GET /api/v1/briefings/{date}`

- 方法 / 路径：`GET /api/v1/briefings/{date}`
- 鉴权：公开
- Path：`date` = `YYYY-MM-DD`
- Query：无
- 200：与 `/today` 相同形状。`2026-09-01` 的 `title.zh` = `新基准周拉开：幻觉被拆开打分`，`updatedAt` = `07:08`，`pulse.clusters` = 11。
- 404：该日无 **published** 早报（含 `2099-01-01`）

```json
{ "error": { "code": "NOT_FOUND", "message": "No briefing for this date." } }
```

- 422：日期非法（`2026-13-01`、`20260914`）。`today` 已被静态路由吃掉，不会当 date。

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid date. Use YYYY-MM-DD." } }
```

`from`/`to` 不属于本端点。

---

## 6. `GET /api/v1/briefings`

- 方法 / 路径：`GET /api/v1/briefings`
- 鉴权：公开
- 用途：归档月历 + 「已生成」列表
- Query：

| 名 | 必填 | 规则 |
|---|---|---|
| `from` | 是 | `YYYY-MM-DD` |
| `to` | 是 | `YYYY-MM-DD`，且 `from <= to` |
| 跨度 | — | 最多 62 天（含首尾） |

- 200：只含 published。按 `date` 升序。`mustReadCount` 给列表；`clusters` 给日历小字（快照，不是 COUNT）。

```json
{
  "data": {
    "items": [
      {
        "date": "2026-09-01",
        "weekday": { "zh": "星期二", "en": "Tuesday" },
        "title": {
          "zh": "新基准周拉开：幻觉被拆开打分",
          "en": "Eval week opens: hallucinations get split scores"
        },
        "updatedAt": "07:08",
        "mustReadCount": 2,
        "clusters": 11
      }
    ]
  }
}
```

`2026-09-01` 种子：2 条 must + 1 条 more，故 `mustReadCount=2`。`2026-09-14` 的 `mustReadCount=8`，`clusters` 仍是快照 **14**（不是 11）。空区间返回 `"items": []`，不是 404。

- 422：缺参数、非法日期、`from > to`、跨度 > 62

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid date range." } }
```

前端 `archive/page.tsx` 用 `CURRENT_DATE` 所在月；client 以后用 `meta.currentDate` 算 `from`/`to`。

---

## 7. `GET /api/v1/stories/{slug}`

- 方法 / 路径：`GET /api/v1/stories/{slug}`
- 鉴权：公开
- Path：`slug` kebab，`^[a-z0-9]+(?:-[a-z0-9]+)*$`，1–80 字符（含生成式 `20260901-01-research`）
- Query：无
- 200：对齐 `Story`，并带 `topic`。无 `confidence` 字段。

```json
{
  "data": {
    "slug": "claude-memory",
    "date": "2026-09-14",
    "topicSlug": "models",
    "rank": 2,
    "section": "must",
    "title": {
      "zh": "Claude 记忆层上线，个人开、企业关",
      "en": "Claude memory ships: on for consumers, off for work"
    },
    "dek": {
      "zh": "跨会话记忆变成产品能力，也变成合规开关。这不是聊天记录，是可检索的用户状态。",
      "en": "Cross-session memory is now a product, and a compliance switch. This is not chat history. It is retrievable user state."
    },
    "topic": {
      "slug": "models",
      "name": { "zh": "模型发布", "en": "Model launches" }
    },
    "synthesis": [
      {
        "zh": "Anthropic 把「还记得上次」做成一层可开关的记忆，而不是藏在上下文窗口里的小聪明。个人默认开，企业默认关，这条分割线写进了发布说明第一屏。",
        "en": "Anthropic made “it remembers last time” a switchable layer, not a parlor trick inside the context window. Consumer default on, enterprise default off — the split is on the first screen of the notes."
      },
      {
        "zh": "它会改变周报、客服和顾问类工作流，也会把数据保留从日志问题升级成画像问题。法务要的不是更好的摘要，是关闭、导出、删除三件套。",
        "en": "It will change weekly notes, support, and advisory workflows. It also upgrades retention from a logging issue to a profiling issue. Counsel does not want a nicer summary. They want off, export, and delete."
      }
    ],
    "timeline": [
      {
        "time": "06:28",
        "text": {
          "zh": "Anthropic 发布记忆层，企业租户默认关闭。",
          "en": "Anthropic ships memory; enterprise tenants default off."
        }
      }
    ],
    "sources": [
      {
        "name": "Anthropic News",
        "lang": "en",
        "kind": { "zh": "一手", "en": "Primary" },
        "time": "06:28"
      },
      {
        "name": "Wired",
        "lang": "en",
        "kind": { "zh": "媒体", "en": "Press" },
        "time": "06:55"
      },
      {
        "name": "36氪",
        "lang": "zh",
        "kind": { "zh": "媒体", "en": "Press" },
        "time": "07:08"
      },
      {
        "name": "The Information",
        "lang": "en",
        "kind": { "zh": "媒体", "en": "Press" },
        "time": "07:31"
      }
    ]
  }
}
```

`synthesis` / `timeline` / `sources` 按 `sort_order`。上例 `timeline` 只列第 1 条定形状；种子 `claude-memory` 有 **4** 条时间线，实现必须全返回。所属 briefing 非 published → 404。`Wired` / `The Information` 的 `source_id` 在库里为空，JSON 仍只回 `name`。

- 404：

```json
{ "error": { "code": "NOT_FOUND", "message": "Unknown cluster." } }
```

- 422：slug 不符合 kebab

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid slug." } }
```

---

## 8. `GET /api/v1/topics`

- 方法 / 路径：`GET /api/v1/topics`
- 鉴权：公开
- Query / Path：无
- 200：`is_active=true`，按 `sort_order, id`。`clusterCount` = 该专题下、所属 published 早报的簇数量。

```json
{
  "data": {
    "items": [
      {
        "slug": "models",
        "name": { "zh": "模型发布", "en": "Model launches" },
        "blurb": {
          "zh": "GPT-5.5 降价 · Claude 记忆层",
          "en": "GPT-5.5 price cut · Claude memory"
        },
        "clusterCount": 5
      }
    ]
  }
}
```

`clusterCount` 锁死见 `02` 种子表（`models=5`，`open-source=10`，合计 53）。无 404。无 422。种子应 10 条，顺序与 `topics.ts` 一致。

---

## 9. `GET /api/v1/topics/{slug}`

- 方法 / 路径：`GET /api/v1/topics/{slug}`
- 鉴权：公开
- Path：`slug` 同专题 kebab（1–64，与表约束一致；校验按 1–80 亦可）
- Query：无
- 200：专题 + 该专题簇列表，排序 `date DESC`，其次 must rank。条目用 `StorySummary`。

```json
{
  "data": {
    "slug": "models",
    "name": { "zh": "模型发布", "en": "Model launches" },
    "blurb": {
      "zh": "GPT-5.5 降价 · Claude 记忆层",
      "en": "GPT-5.5 price cut · Claude memory"
    },
    "clusterCount": 5,
    "stories": [
      {
        "slug": "gpt-55-price",
        "date": "2026-09-14",
        "topicSlug": "models",
        "rank": 1,
        "section": "must",
        "title": {
          "zh": "GPT-5.5 API 推理价腰斩，1M 上下文改默认",
          "en": "GPT-5.5 API inference halved; 1M context becomes default"
        },
        "dek": {
          "zh": "价格战打到推理层。媒体和开发者都在算：长文档工作流会不会从 Claude 回流。",
          "en": "The price war hit inference. Press and developers are both doing the math: will long-doc workflows flow back from Claude?"
        },
        "topic": {
          "slug": "models",
          "name": { "zh": "模型发布", "en": "Model launches" }
        },
        "sourceCount": 6,
        "sourceNames": ["OpenAI Blog", "The Verge", "机器之心"]
      },
      {
        "slug": "claude-memory",
        "date": "2026-09-14",
        "topicSlug": "models",
        "rank": 2,
        "section": "must",
        "title": {
          "zh": "Claude 记忆层上线，个人开、企业关",
          "en": "Claude memory ships: on for consumers, off for work"
        },
        "dek": {
          "zh": "跨会话记忆变成产品能力，也变成合规开关。这不是聊天记录，是可检索的用户状态。",
          "en": "Cross-session memory is now a product, and a compliance switch. This is not chat history. It is retrievable user state."
        },
        "topic": {
          "slug": "models",
          "name": { "zh": "模型发布", "en": "Model launches" }
        },
        "sourceCount": 4,
        "sourceNames": ["Anthropic News", "Wired", "36氪"]
      }
    ]
  }
}
```

专题存在但无簇：`stories: []`，`clusterCount: 0`，仍 200。`models` 完整 5 条排序：`gpt-55-price`、`claude-memory`、`20260911-03-models`、`20260909-02-models`、`20260903-02-models`（date DESC，其次 rank）。上例只列前 2 条定形状。

- 404 未知或不 active：

```json
{ "error": { "code": "NOT_FOUND", "message": "Unknown topic." } }
```

- 422 非法 slug：

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid slug." } }
```

---

## 10. `GET /api/v1/sources`

- 方法 / 路径：`GET /api/v1/sources`
- 鉴权：公开
- Query / Path：无
- 200：对齐 `types.ts` 的 `Source`。`id` = `code`。

```json
{
  "data": {
    "items": [
      {
        "id": "openai-blog",
        "name": "OpenAI Blog",
        "status": "ok",
        "lastFetch": "06:12",
        "todayCount": 2,
        "detail": { "zh": "正常 · 06:12 · 今日 2 篇", "en": "Healthy · 06:12 · 2 today" }
      },
      {
        "id": "lab-rss",
        "name": "某实验室 RSS",
        "status": "bad",
        "lastFetch": "—",
        "todayCount": 0,
        "detail": { "zh": "失败 · 连续 2 次 · 已隔离", "en": "Failed · 2 times in a row · quarantined" }
      }
    ]
  }
}
```

**锁死顺序**：按 `src/data/topics.ts` 的 `sources` 数组声明顺序返回（`openai-blog` 第一，`lab-rss` 最后），不要按 `code` 字母序。测试按这个顺序快照。

`status` 仅 `ok | late | bad`。不暴露 `homepage_url` / `feed_url`。无 404。无 422。

---

## 11. `GET /api/v1/search`

- 方法 / 路径：`GET /api/v1/search`
- 鉴权：公开
- Path：无
- Query：

| 名 | 必填 | 规则 |
|---|---|---|
| `q` | 是 | 先去掉 ASCII 控制字符（U+0000–U+001F、U+007F），再 trim；trim 后 1–100 才搜库 |

空 `q`、纯空白、或剥离控制字符后为空：不要搜全库。返回 `items: []` 且 `query` 为 `""`，HTTP 200（对齐前端未输入时的空态；前端目前不发空请求，但契约要确定）。缺少 `q` 参数才 422。

- 200：扁平列表，**不分组**。排序：`date DESC`，must 先于 more，`rank NULLS LAST`。

```json
{
  "data": {
    "query": "Claude",
    "items": [
      {
        "slug": "claude-memory",
        "date": "2026-09-14",
        "topicSlug": "models",
        "rank": 2,
        "section": "must",
        "title": {
          "zh": "Claude 记忆层上线，个人开、企业关",
          "en": "Claude memory ships: on for consumers, off for work"
        },
        "dek": {
          "zh": "跨会话记忆变成产品能力，也变成合规开关。这不是聊天记录，是可检索的用户状态。",
          "en": "Cross-session memory is now a product, and a compliance switch. This is not chat history. It is retrievable user state."
        },
        "topic": {
          "slug": "models",
          "name": { "zh": "模型发布", "en": "Model launches" }
        },
        "sourceCount": 4,
        "sourceNames": ["Anthropic News", "Wired", "36氪"]
      }
    ]
  }
}
```

无命中：`items: []`，200，不是 404。

- 422：`q` 缺失、或 trim 后 > 100

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid query." } }
```

匹配范围：slug、title/dek 中英、synthesis 中英、citation `source_name`、专题名中英。与 `searchStories()` 的 haystack 一致。

V1 不加 `limit`/`cursor`。种子量级全量返回。

---

## 12. `POST /api/v1/auth/login`

- 方法 / 路径：`POST /api/v1/auth/login`
- 鉴权：公开（严格限流，见 `04`）
- Query / Path：无
- Body：

```json
{ "email": "admin@example.com", "password": "string" }
```

- 200：

```json
{
  "data": {
    "accessToken": "<jwt>",
    "refreshToken": "<opaque>",
    "tokenType": "Bearer",
    "expiresIn": 900,
    "admin": { "email": "admin@example.com" }
  }
}
```

- 401 邮箱或密码错误、账号停用，**同一消息**：

```json
{ "error": { "code": "UNAUTHORIZED", "message": "Invalid credentials." } }
```

- 422：缺字段、email 不像邮箱、password 空或 > 256

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid login payload." } }
```

成功写 `audit_logs`：`action=login`，`resource=auth`。失败也写 `login_failed`，metadata 不含密码，email 可记。

V1 无内容写接口；login 只为阶段 3 预埋。

---

## 13. `POST /api/v1/auth/refresh`

- 方法 / 路径：`POST /api/v1/auth/refresh`
- 鉴权：无 Bearer。Body 带 refresh。
- Query / Path：无
- Body：`{ "refreshToken": "<opaque>" }`
- 200：形状同 login（新 access + 新 refresh）。旧 refresh 立即 `revoked_at`。
- 401：未知、过期、已撤销：

```json
{ "error": { "code": "UNAUTHORIZED", "message": "Invalid refresh token." } }
```

- 422：缺 `refreshToken`

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Invalid refresh payload." } }
```

已撤销、未知、过期都 401，避免泄露 token 是否曾存在。**V1 禁止 409**，重放与未知同一文案。

---

## 14. `POST /api/v1/auth/logout`

- 方法 / 路径：`POST /api/v1/auth/logout`
- 鉴权：`Authorization: Bearer <access>` **或** body `refreshToken`（至少一种）
- Query：无
- Body 可选：`{ "refreshToken": "<opaque>" }`
- 行为：撤销该用户当前 refresh（有 body 则只撤这一条；仅 access 则撤该用户全部未过期 refresh）
- 200：

```json
{ "data": { "ok": true } }
```

access 无效且无合法 refresh → 401。

```json
{ "error": { "code": "UNAUTHORIZED", "message": "Invalid access token." } }
```

缺两者 → 422。

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Missing access or refresh token." } }
```

---

## 15. `GET /api/v1/admin/me`

- 方法 / 路径：`GET /api/v1/admin/me`
- 鉴权：`Authorization: Bearer <access>`
- Query / Path：无
- 200：

```json
{
  "data": {
    "email": "admin@example.com"
  }
}
```

- 401 缺/过期/签名失败：

```json
{ "error": { "code": "UNAUTHORIZED", "message": "Invalid access token." } }
```

- 403 `is_active=false`：

```json
{ "error": { "code": "FORBIDDEN", "message": "Account disabled." } }
```

无 404。无 422（无参数）。不返回 `password_hash`、内部 id。

---

## 16. 明确不存在的 V1 端点

不要实现：

- `POST/PATCH/DELETE /api/v1/briefings|stories|topics|sources`
- 用户注册、收藏
- 文件上传
- GraphQL
- SSE / WebSocket

需要时走阶段 3/4 新契约。

## 17. 前端接线备忘（阶段 2，非本轮）

| 页面 | 调用 |
|---|---|
| `BriefingView` | `/briefings/today` 或 `/briefings/{date}`，直接用内嵌 summary |
| `Footer` | 用 today 的 `updatedAt`、`mustRead.length`、`pulse` |
| 归档 | `/briefings?from=&to=` |
| 专题列表 | `/topics` 的 `clusterCount` |
| 专题详情 | `/topics/{slug}` 的 `stories` |
| 信源 | `/sources`，顺序锁 `topics.ts` |
| 搜索 | `/search?q=`，前端按 `date` 与 `meta.currentDate` 分组 |
| 簇页 | `/stories/{slug}`；返回今日用 `date === meta.currentDate` |

CORS、安全头、限流数值见 `04`。
