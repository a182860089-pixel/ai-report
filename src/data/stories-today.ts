import { src, tx } from "./text";
import type { MockStory as Story } from "./types";

export const todayStories: Story[] = [
  {
    slug: "gpt-55-price",
    date: "2026-09-14",
    topicSlug: "models",
    rank: 1,
    section: "must",
    title: tx("GPT-5.5 API 推理价腰斩，1M 上下文改默认", "GPT-5.5 API inference halved; 1M context becomes default"),
    dek: tx("价格战打到推理层。媒体和开发者都在算：长文档工作流会不会从 Claude 回流。", "The price war hit inference. Press and developers are both doing the math: will long-doc workflows flow back from Claude?"),
    synthesis: [
      tx("OpenAI 把长上下文从加价项改成默认能力，同时砍推理单价。表面是促销，实际是在抢文档、代码库和客服日志这类「长输入、短输出」的工作负载。", "OpenAI turned long context from a surcharge into a default, and cut inference unit price. The promo is cover. The target is long-in, short-out work: documents, repos, support logs."),
      tx("中文报道多在写「降价 50%」，英文报道在写 1M 默认和批处理折扣。事件本身没有分歧，分歧在谁会被抢走：Claude 的长上下文口碑，还是 Gemini 的价格地板。", "Chinese coverage leads with “50% off.” English coverage leads with 1M default and batch discounts. The facts are not in dispute. The fight is over who loses: Claude’s long-context reputation, or Gemini’s price floor.")
    ],
    sources: [
      src("OpenAI Blog", "en", "一手", "Primary", "06:12"),
      src("The Verge", "en", "媒体", "Press", "06:40"),
      src("机器之心", "zh", "媒体", "Press", "07:05"),
      src("Hacker News", "en", "讨论", "Forum", "07:18"),
      src("量子位", "zh", "媒体", "Press", "07:22"),
      src("GitHub Changelog", "en", "产品", "Product", "08:01")
    ],
    timeline: [
      { time: "06:12", text: tx("OpenAI 发布博客与价格表，1M 上下文改为 API 默认。", "OpenAI posts the blog and price sheet; 1M context becomes the API default.") },
      { time: "06:40", text: tx("The Verge 对比例：128k 以上工作负载成本大约腰斩。", "The Verge runs the comparison: workloads over 128k roughly drop by half.") },
      { time: "07:05", text: tx("机器之心、量子位同步，标题集中在降价而非上下文。", "Jiqizhixin and QbitAI follow; headlines stay on the cut, not the context window.") },
      { time: "08:20", text: tx("开发者对照帖出现：批处理、缓存命中、长文档 RAG 的新账。", "Developer comparison posts appear: batch, cache hits, and the new long-doc RAG bill.") }
    ]
  },
  {
    slug: "claude-memory",
    date: "2026-09-14",
    topicSlug: "models",
    rank: 2,
    section: "must",
    title: tx("Claude 记忆层上线，个人开、企业关", "Claude memory ships: on for consumers, off for work"),
    dek: tx("跨会话记忆变成产品能力，也变成合规开关。这不是聊天记录，是可检索的用户状态。", "Cross-session memory is now a product, and a compliance switch. This is not chat history. It is retrievable user state."),
    synthesis: [
      tx("Anthropic 把「还记得上次」做成一层可开关的记忆，而不是藏在上下文窗口里的小聪明。个人默认开，企业默认关，这条分割线写进了发布说明第一屏。", "Anthropic made “it remembers last time” a switchable layer, not a parlor trick inside the context window. Consumer default on, enterprise default off — the split is on the first screen of the notes."),
      tx("它会改变周报、客服和顾问类工作流，也会把数据保留从日志问题升级成画像问题。法务要的不是更好的摘要，是关闭、导出、删除三件套。", "It will change weekly notes, support, and advisory workflows. It also upgrades retention from a logging issue to a profiling issue. Counsel does not want a nicer summary. They want off, export, and delete.")
    ],
    sources: [
      src("Anthropic News", "en", "一手", "Primary", "06:28"),
      src("Wired", "en", "媒体", "Press", "06:55"),
      src("36氪", "zh", "媒体", "Press", "07:08"),
      src("The Information", "en", "媒体", "Press", "07:31")
    ],
    timeline: [
      { time: "06:28", text: tx("Anthropic 发布记忆层，企业租户默认关闭。", "Anthropic ships memory; enterprise tenants default off.") },
      { time: "06:55", text: tx("Wired 把它写成「可检索的用户状态」。", "Wired frames it as retrievable user state.") },
      { time: "07:08", text: tx("36氪关注个人版默认开启。", "36Kr focuses on the consumer default-on.") },
      { time: "07:44", text: tx("企业客户开始问导出和删除 API。", "Enterprise customers start asking for export and delete APIs.") }
    ]
  },
  {
    slug: "kimi-open-weights",
    date: "2026-09-14",
    topicSlug: "open-source",
    rank: 3,
    section: "must",
    title: tx("Kimi 新模型部分开源，LMSYS 前五", "Kimi partially open-sources a new model; LMSYS top five"),
    dek: tx("中文场的叙事从「能用」变成「可部署」。权重、许可和基准分数被绑在同一条新闻里。", "The Chinese-language story shifts from “it works” to “it deploys.” Weights, license, and bench scores are one item."),
    synthesis: [
      tx("月之暗面放出部分权重，并在 LMSYS 挤进前五。真正被转发的不是聊天截图，是许可条款和私有化部署说明。", "Moonshot releases partial weights and cracks LMSYS top five. What gets forwarded is not chat screenshots. It is the license and the private-deploy note."),
      tx("「部分开源」三个字会在本周被律师和社区各读一遍。能微调的层、不能商用的工具调用、以及基准是否可复现，会拆成三条后续。", "“Partial open source” will be read twice this week, once by lawyers and once by the community. Which layers fine-tune, which tool-use stays closed, and whether the bench reproduces — those become three follow-ups.")
    ],
    sources: [
      src("月之暗面", "zh", "一手", "Primary", "06:48"),
      src("Hugging Face", "en", "产品", "Product", "07:11"),
      src("量子位", "zh", "媒体", "Press", "07:19"),
      src("LMSYS", "en", "基准", "Benchmark", "07:33")
    ],
    timeline: [
      { time: "06:48", text: tx("Kimi 宣布部分权重与许可。", "Kimi announces partial weights and license.") },
      { time: "07:11", text: tx("Hugging Face 模型卡上线。", "The Hugging Face model card goes up.") },
      { time: "07:33", text: tx("LMSYS 排行更新，进入前五。", "LMSYS updates; it enters the top five.") }
    ]
  },
  {
    slug: "gemini-robotics-2",
    date: "2026-09-14",
    topicSlug: "robotics",
    rank: 4,
    section: "must",
    title: tx("Gemini Robotics 2 刷新仓库拣选基准", "Gemini Robotics 2 resets the warehouse-picking bench"),
    dek: tx("DeepMind 把多模态模型重新包装成机器人策略。工业演示多于落地时间表。", "DeepMind repackages a multimodal model as a robot policy. Industrial demos outrun any shipping calendar."),
    synthesis: [
      tx("仓库拣选被写成主指标，视频里的成功率很好看。现场集成、夹具、安全停机这些句子仍在附录。", "Warehouse picking is the headline metric; the video success rate looks clean. Integration, grippers, and safe-stop still live in the appendix.")
    ],
    sources: [
      src("DeepMind", "en", "一手", "Primary", "06:51"),
      src("TechCrunch", "en", "媒体", "Press", "07:14"),
      src("机器之心", "zh", "媒体", "Press", "07:29")
    ],
    timeline: [
      { time: "06:51", text: tx("DeepMind 发布 Gemini Robotics 2。", "DeepMind releases Gemini Robotics 2.") },
      { time: "07:14", text: tx("TechCrunch 强调拣选基准，不给交付日期。", "TechCrunch stresses the picking bench and gives no ship date.") }
    ]
  }
];