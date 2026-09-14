import { tx } from "./text";
import type { Source, Topic } from "./types";

export const topics: Topic[] = [
  { slug: "models", name: tx("模型发布", "Model launches"), blurb: tx("GPT-5.5 降价 · Claude 记忆层", "GPT-5.5 price cut · Claude memory") },
  { slug: "open-source", name: tx("开源权重", "Open weights"), blurb: tx("Kimi 部分开源 · Llama 4.1 8B", "Kimi partial release · Llama 4.1 8B") },
  { slug: "agents", name: tx("智能体", "Agents"), blurb: tx("GLM Agent 基准 · Copilot 多仓库", "GLM agent bench · Copilot multi-repo") },
  { slug: "chips", name: tx("芯片", "Chips"), blurb: tx("Rubin 细节 · 推理卡缺货", "Rubin details · inference GPUs short") },
  { slug: "policy", name: tx("政策", "Policy"), blurb: tx("EU AI Act 第二阶段", "EU AI Act phase two") },
  { slug: "robotics", name: tx("机器人", "Robotics"), blurb: tx("Gemini Robotics 2", "Gemini Robotics 2") },
  { slug: "on-device", name: tx("端侧", "On-device"), blurb: tx("手机 30 tok/s", "30 tok/s on phones") },
  { slug: "industry-cn", name: tx("中文产业", "China industry"), blurb: tx("通义座舱签约", "Tongyi cockpit deals") },
  { slug: "research", name: tx("研究", "Research"), blurb: tx("扩散语言模型 · 新基准", "Diffusion LMs · new benches") },
  { slug: "safety", name: tx("安全", "Safety"), blurb: tx("记忆与数据保留", "Memory and retention") }
];

export const sources: Source[] = [
  { id: "openai-blog", name: "OpenAI Blog", status: "ok", lastFetch: "06:12", todayCount: 2, detail: tx("正常 · 06:12 · 今日 2 篇", "Healthy · 06:12 · 2 today") },
  { id: "anthropic", name: "Anthropic News", status: "ok", lastFetch: "06:28", todayCount: 1, detail: tx("正常 · 06:28 · 今日 1 篇", "Healthy · 06:28 · 1 today") },
  { id: "deepmind", name: "DeepMind", status: "ok", lastFetch: "06:51", todayCount: 1, detail: tx("正常 · 06:51 · 今日 1 篇", "Healthy · 06:51 · 1 today") },
  { id: "jiqizhixin", name: "机器之心", status: "ok", lastFetch: "07:05", todayCount: 6, detail: tx("正常 · 07:05 · 今日 6 篇", "Healthy · 07:05 · 6 today") },
  { id: "qbitai", name: "量子位", status: "late", lastFetch: "05:40", todayCount: 4, detail: tx("延迟 · 05:40 · 今日 4 篇", "Late · 05:40 · 4 today") },
  { id: "hf", name: "Hugging Face", status: "ok", lastFetch: "07:11", todayCount: 3, detail: tx("正常 · 07:11 · 今日 3 篇", "Healthy · 07:11 · 3 today") },
  { id: "arxiv", name: "arXiv cs.AI", status: "ok", lastFetch: "06:00", todayCount: 18, detail: tx("正常 · 06:00 · 今日 18 篇", "Healthy · 06:00 · 18 today") },
  { id: "hn", name: "Hacker News", status: "ok", lastFetch: "07:18", todayCount: 9, detail: tx("正常 · 07:18 · 今日 9 条", "Healthy · 07:18 · 9 today") },
  { id: "github", name: "GitHub Trending", status: "ok", lastFetch: "07:00", todayCount: 5, detail: tx("正常 · 07:00 · 今日 5 条", "Healthy · 07:00 · 5 today") },
  { id: "verge", name: "The Verge", status: "ok", lastFetch: "06:40", todayCount: 2, detail: tx("正常 · 06:40 · 今日 2 篇", "Healthy · 06:40 · 2 today") },
  { id: "36kr", name: "36氪", status: "late", lastFetch: "04:12", todayCount: 3, detail: tx("延迟 · 04:12 · 今日 3 篇", "Late · 04:12 · 3 today") },
  { id: "lab-rss", name: "某实验室 RSS", status: "bad", lastFetch: "—", todayCount: 0, detail: tx("失败 · 连续 2 次 · 已隔离", "Failed · 2 times in a row · quarantined") }
];