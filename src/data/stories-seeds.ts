import { src, tx } from "./text";
import type { Story } from "./types";

type Row = [
  date: string,
  rank: number,
  section: "must" | "more",
  topic: string,
  zhTitle: string,
  enTitle: string,
  zhDek: string,
  enDek: string,
  names: [string, "zh" | "en"][]
];

const rows: Row[] = [
  ["2026-09-01", 1, "must", "research", "新基准把幻觉拆成三类错误", "New bench splits hallucinations into three error types", "事实错误、过时、胡编被分开打分，总榜失去意义。", "Factual errors, stale facts, and fabrications get separate scores. The grand ranking loses meaning.", [["arXiv", "en"], ["机器之心", "zh"]]],
  ["2026-09-01", 2, "must", "open-source", "开源推理引擎支持前缀缓存共享", "Open inference engines share prefix caches", "同一条系统提示不再被每个请求重算一遍。", "The same system prompt is no longer recomputed per request.", [["GitHub", "en"], ["Hacker News", "en"]]],
  ["2026-09-01", 0, "more", "safety", "欧洲实验室公开红队日志格式", "European labs publish a red-team log format", "可交换的攻击轨迹，比又一份原则声明有用。", "Exchangeable attack traces beat another principles note.", [["arXiv", "en"]]],
  ["2026-09-02", 1, "must", "open-source", "律师把 Apache-2.0 和「可商用」拆开", "Lawyers split Apache-2.0 from “commercial use”", "能跑权重不代表能卖服务。模型卡开始写禁止项。", "Runnable weights are not a license to sell a service. Model cards grow a prohibitions list.", [["Hugging Face", "en"], ["Reuters", "en"]]],
  ["2026-09-02", 2, "must", "policy", "权重发布开始写地域限制", "Weight releases start listing regional limits", "下载按钮旁边出现一张地图，这比许可证更难绕。", "A map appears next to the download button. That is harder to route around than a license.", [["GitHub", "en"], ["量子位", "zh"]]],
  ["2026-09-02", 0, "more", "open-source", "社区复现被条款拦在模型卡外", "Replications stall outside the model card", "脚本齐了，法律意见不齐。", "The scripts are ready. The legal memo is not.", [["Hacker News", "en"]]],
  ["2026-09-03", 1, "must", "chips", "批处理折扣写进默认价目表", "Batch discounts enter the default price list", "异步任务终于有了正式价格，而不只是内部优惠。", "Async jobs finally have a public price, not a private discount.", [["OpenAI Blog", "en"], ["The Verge", "en"]]],
  ["2026-09-03", 2, "must", "models", "长上下文缓存命中率成为新 KPI", "Long-context cache hit rate becomes a KPI", "省钱不靠更短的提示，靠提示被重复用。", "Savings come from reuse, not from shorter prompts.", [["GitHub", "en"], ["机器之心", "zh"]]],
  ["2026-09-03", 0, "more", "industry-cn", "中文云厂商跟进夜间闲时价", "Chinese clouds follow with off-peak night rates", "训练可以等夜里，推理不行。价格开始承认这件事。", "Training can wait for night. Inference cannot. Pricing starts to admit it.", [["36氪", "zh"]]],
  ["2026-09-04", 1, "must", "agents", "办公套件把表格邮件日历串成一条工具链", "Office suites chain sheets, mail, and calendar into one tool path", "演示能改三份文件。审计日志还是空的。", "The demo can touch three files. The audit log is still empty.", [["The Verge", "en"], ["36氪", "zh"]]],
  ["2026-09-04", 2, "must", "safety", "代理权限包开始按部门卖", "Agent permission packs go on sale by department", "市场部能发邮件，财务不能。这是产品，也是事故预演。", "Marketing can send mail. Finance cannot. It is a product, and an incident rehearsal.", [["Wired", "en"], ["机器之心", "zh"]]],
  ["2026-09-04", 0, "more", "agents", "中文办公套件推出「代办权限包」", "Chinese office suites ship delegated-permission packs", "授权粒度写到了文件夹，而不是整盘。", "Delegation is scoped to a folder, not the whole drive.", [["晚点", "zh"]]],
  ["2026-09-05", 1, "must", "policy", "通用模型义务草稿开始互抄附录", "GPAI drafts start copying each other’s annexes", "口径在对齐，定义还没有。", "The tone is aligning. The definitions are not.", [["Reuters", "en"], ["European Commission", "en"]]],
  ["2026-09-05", 2, "must", "open-source", "开源豁免边界比禁令更惹火", "Open-source exemptions draw more heat than bans", "吵的不是能不能做，是谁算提供方。", "The fight is not “may we.” It is “who is a provider.”", [["Hugging Face", "en"], ["机器之心", "zh"]]],
  ["2026-09-05", 0, "more", "policy", "企业法务要一份上线清单，没人给得出", "Counsel wants a ship list; nobody has one", "合规团队开始自己画红黄绿。", "Compliance teams start drawing their own red / amber / green.", [["财新", "zh"]]],
  ["2026-09-06", 1, "must", "research", "非自回归解码在补全延迟上第一次像样", "Non-autoregressive decoding looks serious on completion latency", "周末论文把尾延迟写进主表，而不是附录。", "A Sunday paper puts tail latency in the main table, not the appendix.", [["arXiv", "en"]]],
  ["2026-09-06", 2, "must", "robotics", "机器人 VLA 把仓库拣选写成主任务", "Robot VLA papers make warehouse picking the headline task", "家庭机器人新闻退到第二段。", "Home-robot news falls to paragraph two.", [["DeepMind", "en"], ["TechCrunch", "en"]]],
  ["2026-09-06", 0, "more", "open-source", "中文预训练数据清洗方法被单独开源", "Chinese pretraining cleanup methods get their own release", "这比再发一个 7B 更有复用价值。", "This is more reusable than another 7B dump.", [["GitHub", "en"], ["量子位", "zh"]]],
  ["2026-09-07", 1, "must", "on-device", "新运行时把 8B 首字延迟压进 200ms", "A new runtime pushes 8B time-to-first-token under 200ms", "输入法能用了，聊天助手还要看热。", "Keyboards can use it. Chat assistants still depend on thermals.", [["GitHub", "en"], ["量子位", "zh"]]],
  ["2026-09-07", 2, "must", "on-device", "手机系统设置出现「本地模型」", "Phone settings gain a “local model” row", "这标志着端侧从应用功能变成系统能力。", "On-device moves from an app feature to a system capability.", [["The Verge", "en"], ["机器之心", "zh"]]],
  ["2026-09-07", 0, "more", "chips", "开发者文档把 GPU、NPU、CPU 写成三套后端", "Docs list GPU, NPU, and CPU as three backends", "调度策略比模型选择更难讲清楚。", "Scheduling is harder to explain than model choice.", [["GitHub", "en"]]]
];

function storyFromRow(row: Row): Story {
  const [date, rank, section, topic, zhTitle, enTitle, zhDek, enDek, names] = row;
  const title = tx(zhTitle, enTitle);
  const dek = tx(zhDek, enDek);
  const key = section === "more" ? "m" : String(rank).padStart(2, "0");
  return {
    slug: `${date.replace(/-/g, "")}-${key}-${topic}`,
    date,
    topicSlug: topic,
    rank: section === "must" ? rank : undefined,
    section,
    title,
    dek,
    synthesis: [dek],
    sources: names.map(([name, lang], index) =>
      src(name, lang, lang === "zh" ? "媒体" : "Press", lang === "zh" ? "媒体" : "Press", index === 0 ? "06:40" : "07:10")
    ),
    timeline: [{ time: "07:00", text: title }]
  };
}

export const seedStoriesEarly: Story[] = rows.map(storyFromRow);