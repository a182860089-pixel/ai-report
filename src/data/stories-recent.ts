import { src, tx } from "./text";
import type { Story } from "./types";

export const recentStories: Story[] = [
  {
    slug: "ide-local-8b",
    date: "2026-09-13",
    topicSlug: "on-device",
    rank: 1,
    section: "must",
    title: tx("IDE 把本地 8B 补全写成正式设置项", "IDEs promote local 8B completion to a real setting"),
    dek: tx("补全不再必须出公网。编辑器把「本地模型」和「云端模型」并列。", "Completion no longer has to leave the building. Editors put local and cloud models side by side."),
    synthesis: [
      tx("两家主流 IDE 在设置里给出本地 8B 补全。默认仍是云，但离线包、模型和缓存路径都露出了产品化的边。", "Two mainstream IDEs add local 8B completion in settings. Cloud stays default, but the offline pack, model, and cache path now look like a product."),
      tx("这会改写代码隐私叙事：不是「我们不训练你的代码」，而是「代码根本没出门」。", "This rewrites the code-privacy line: not “we do not train on your code,” but “the code never left.”")
    ],
    sources: [
      src("GitHub Changelog", "en", "产品", "Product", "06:40"),
      src("机器之心", "zh", "媒体", "Press", "07:08"),
      src("Hacker News", "en", "讨论", "Forum", "07:22")
    ],
    timeline: [
      { time: "06:40", text: tx("编辑器更新说明出现 Local model 开关。", "Editor notes show a Local model toggle.") },
      { time: "07:22", text: tx("开发者开始比本地补全和云端补全的延迟。", "Developers start comparing local vs cloud completion latency.") }
    ]
  },
  {
    slug: "copilot-multirepo",
    date: "2026-09-13",
    topicSlug: "agents",
    rank: 2,
    section: "must",
    title: tx("Copilot 多仓库上下文进入预览", "Copilot multi-repo context enters preview"),
    dek: tx("单文件补全不够了。Agent 要在组织里找接口定义。", "Single-file completion is not enough. The agent has to find interface defs across the org."),
    synthesis: [
      tx("多仓库检索被放进 Copilot 预览。演示是跨服务改接口，风险是权限边界：只读索引还是能开 PR。", "Multi-repo retrieval lands in Copilot preview. The demo is a cross-service interface change. The risk is the permission boundary: read-only index, or it can open PRs.")
    ],
    sources: [
      src("GitHub Blog", "en", "一手", "Primary", "06:18"),
      src("The New Stack", "en", "媒体", "Press", "07:01")
    ],
    timeline: [
      { time: "06:18", text: tx("GitHub 宣布多仓库上下文预览。", "GitHub announces multi-repo context preview.") }
    ]
  },
  {
    slug: "laptop-quant-8b",
    date: "2026-09-13",
    topicSlug: "on-device",
    rank: 3,
    section: "must",
    title: tx("量化方案把 8B 塞进 16GB 笔记本", "Quantization fits 8B into a 16GB laptop"),
    dek: tx("目标机器不是工作站，是公司标配本。", "The target machine is not a workstation. It is the company laptop."),
    synthesis: [
      tx("新的量化脚本把 8B 的内存占用压到 16GB 机器可跑，并保住补全可用的 perplexity。这是采购新闻：还要不要给每人加内存。", "New quant scripts fit 8B onto 16GB machines without killing completion perplexity. This is a procurement story: do you still upgrade everyone’s RAM?")
    ],
    sources: [
      src("Hugging Face", "en", "产品", "Product", "06:52"),
      src("GitHub", "en", "代码", "Code", "07:15")
    ],
    timeline: [
      { time: "06:52", text: tx("量化卡片给出 16GB 可运行配置。", "The quant card lists a 16GB runnable config.") }
    ]
  },
  {
    slug: "code-stays-on-device",
    date: "2026-09-13",
    topicSlug: "safety",
    rank: 4,
    section: "must",
    title: tx("隐私团队开始推「代码不离机」开关", "Privacy teams start selling a code-stays-local switch"),
    dek: tx("这不是模型能力，是采购条款改写成了产品按钮。", "This is not a model skill. It is a procurement clause turned into a button."),
    synthesis: [
      tx("安全团队要的是可审计的本地模式：补全请求不离开网段，日志可关。厂商把这项写成设置页上的一句话。", "Security wants an auditable local mode: completion never leaves the subnet, logs can go off. Vendors put that in one sentence on the settings page.")
    ],
    sources: [
      src("36氪", "zh", "媒体", "Press", "07:04"),
      src("Wired", "en", "媒体", "Press", "07:30")
    ],
    timeline: [
      { time: "07:04", text: tx("国内媒体先报「代码不离机」作为卖点。", "Domestic press leads with “code never leaves” as the pitch.") }
    ]
  },
  {
    slug: "offline-terminal-agent",
    date: "2026-09-13",
    topicSlug: "agents",
    section: "more",
    title: tx("终端 Agent 在无网环境跑测试", "Terminal agents run tests with the network down"),
    dek: tx("断网不是故障，是测试夹具。", "No network is not a failure. It is the fixture."),
    synthesis: [
      tx("有人把终端 Agent 的工具调用限制在本地 shell 和测试运行器，断网作为 CI 作业。这比聊天演示更接近工程。", "A terminal agent is boxed to local shell and the test runner, with network-off as a CI job. That is closer to engineering than a chat demo.")
    ],
    sources: [
      src("GitHub", "en", "代码", "Code", "07:44"),
      src("Hacker News", "en", "讨论", "Forum", "08:02")
    ],
    timeline: [
      { time: "07:44", text: tx("无网 CI 作业说明出现在仓库 README。", "A network-off CI note appears in a repo README.") }
    ]
  },
  {
    slug: "anthropic-retention",
    date: "2026-09-11",
    topicSlug: "safety",
    rank: 1,
    section: "must",
    title: tx("Anthropic 企业控制台增加数据保留开关", "Anthropic adds retention controls to the enterprise console"),
    dek: tx("记忆还没成为今日头条时，保留策略先改了。", "Retention policy moved before memory became the Monday headline."),
    synthesis: [
      tx("企业控制台增加保留窗口、可关闭训练和可导出对话。这是给法务看的页面，不是给模型评测看的页面。", "The enterprise console adds a retention window, a training-off switch, and conversation export. This page is for counsel, not for model evals.")
    ],
    sources: [
      src("Anthropic News", "en", "一手", "Primary", "06:22"),
      src("Wired", "en", "媒体", "Press", "07:05")
    ],
    timeline: [
      { time: "06:22", text: tx("控制台更新：保留策略可按工作区设置。", "Console update: retention can be set per workspace.") },
      { time: "07:05", text: tx("媒体把它读成记忆功能的前奏。", "Press reads it as a prelude to memory.") }
    ]
  },
  {
    slug: "memory-privacy-papers",
    date: "2026-09-11",
    topicSlug: "safety",
    section: "more",
    title: tx("跨会话记忆的隐私论文开始集中出现", "Privacy papers on cross-session memory start to cluster"),
    dek: tx("威胁模型从「模型记住训练数据」改成「产品记住你」。", "The threat model shifts from “the model memorized training data” to “the product remembers you.”"),
    synthesis: [
      tx("一批隐私论文把跨会话记忆写成独立攻击面：检索泄漏、画像拼接、删除不彻底。下周一的产品发布会把这些句子变成检查清单。", "A cluster of privacy papers treats cross-session memory as its own surface: retrieval leaks, profile stitching, incomplete delete. Next Monday’s product launch will turn those sentences into a checklist.")
    ],
    sources: [
      src("arXiv", "en", "论文", "Paper", "06:00"),
      src("Twitter/X", "en", "讨论", "Forum", "07:18")
    ],
    timeline: [
      { time: "06:00", text: tx("三篇相关论文同一早出现在 cs.CR。", "Three related papers drop the same morning on cs.CR.") }
    ]
  }
];