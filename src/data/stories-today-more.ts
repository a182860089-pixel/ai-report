import { src, tx } from "./text";
import type { MockStory as Story } from "./types";

export const todayMoreStories: Story[] = [
  {
    slug: "llama-41-8b",
    date: "2026-09-14",
    topicSlug: "on-device",
    rank: 5,
    section: "must",
    title: tx("Llama 4.1 8B：手机端 30 tok/s", "Llama 4.1 8B: 30 tok/s on phones"),
    dek: tx("Meta 继续压端侧。这条新闻的读者不是研究者，是要做离线助手的应用团队。", "Meta keeps pushing on-device. The reader is not a researcher. It is the app team that needs an offline assistant."),
    synthesis: [
      tx("8B 在旗舰手机上跑到 30 tok/s，足够做输入法、离线翻译和本地摘要。电量和热是下一篇评测，不是今天的新闻。", "8B hits 30 tok/s on flagship phones — enough for keyboards, offline translate, and local summaries. Battery and heat are the next review, not today’s news.")
    ],
    sources: [
      src("Meta", "en", "一手", "Primary", "06:33"),
      src("GitHub", "en", "代码", "Code", "07:00"),
      src("量子位", "zh", "媒体", "Press", "07:26")
    ],
    timeline: [
      { time: "06:33", text: tx("Meta 发布 Llama 4.1 8B 与端侧数字。", "Meta ships Llama 4.1 8B with on-device numbers.") },
      { time: "07:00", text: tx("参考实现和量化脚本进 GitHub。", "Reference builds and quant scripts land on GitHub.") }
    ]
  },
  {
    slug: "rubin-supply",
    date: "2026-09-14",
    topicSlug: "chips",
    rank: 6,
    section: "must",
    title: tx("Rubin 架构细节公布，推理卡仍然缺货", "Rubin architecture details land; inference cards still missing"),
    dek: tx("规格单很满，交付日历很空。芯片新闻今天仍然是供应新闻。", "The spec sheet is full. The delivery calendar is empty. Chip news is still supply news."),
    synthesis: [
      tx("Nvidia 把 Rubin 的互连和推理吞吐写得很细。采购关心的仍是：现有推理卡什么时候能提到货。Bloomberg 和财新都把「缺货」放进标题。", "Nvidia is specific on Rubin interconnect and inference throughput. Buyers still want to know when current inference cards actually arrive. Bloomberg and Caixin both put “shortage” in the headline.")
    ],
    sources: [
      src("Nvidia", "en", "一手", "Primary", "06:20"),
      src("Bloomberg", "en", "媒体", "Press", "06:58"),
      src("财新", "zh", "媒体", "Press", "07:17")
    ],
    timeline: [
      { time: "06:20", text: tx("Nvidia 放出 Rubin 架构说明。", "Nvidia posts the Rubin architecture note.") },
      { time: "06:58", text: tx("Bloomberg 把重点放在推理卡交付。", "Bloomberg puts the weight on inference-card delivery.") }
    ]
  },
  {
    slug: "eu-ai-act-phase-2",
    date: "2026-09-14",
    topicSlug: "policy",
    rank: 7,
    section: "must",
    title: tx("欧盟 AI Act 通用模型义务进入第二阶段", "EU AI Act GPAI duties enter phase two"),
    dek: tx("评估报告、系统风险和开源豁免边界被一起拿出来吵。政策开始碰到权重发布节奏。", "Eval reports, systemic risk, and open-source exemptions are argued as one bundle. Policy is now touching weight-release cadence."),
    synthesis: [
      tx("第二阶段不再是原则声明。通用模型提供方要交评估、标系统风险、解释开源豁免。开源实验室会问：权重一公布算不算提供方。", "Phase two is not a principles memo. GPAI providers must file evals, mark systemic risk, and explain open-source exemptions. Open labs will ask whether publishing weights makes them a provider.")
    ],
    sources: [
      src("European Commission", "en", "一手", "Primary", "06:05"),
      src("Reuters", "en", "媒体", "Press", "06:42"),
      src("机器之心", "zh", "媒体", "Press", "07:12")
    ],
    timeline: [
      { time: "06:05", text: tx("欧委会公布第二阶段义务说明。", "The Commission publishes the phase-two duty note.") },
      { time: "06:42", text: tx("Reuters 聚焦开源豁免边界。", "Reuters focuses on the open-source exemption line.") }
    ]
  },
  {
    slug: "glm-agent-bench",
    date: "2026-09-14",
    topicSlug: "agents",
    rank: 8,
    section: "must",
    title: tx("GLM 放出多模态 Agent 基准，中文任务单独切分", "GLM ships a multimodal agent bench with a Chinese split"),
    dek: tx("又一个基准。有用的部分是中文工具调用被单独打分，不再混在英文套件里。", "Another bench. The useful part: Chinese tool-use is scored alone, not folded into an English suite."),
    synthesis: [
      tx("智谱把视觉操作、浏览器和中文工具调用拆开打分。英文套件里「看起来能用」的模型，在中文任务上会掉一截。这才是今天值得记的点。", "Zhipu splits visual ops, browser use, and Chinese tool-use. Models that “look fine” on English suites drop on the Chinese split. That is the thing to keep.")
    ],
    sources: [
      src("清华 / 智谱", "zh", "一手", "Primary", "06:36"),
      src("arXiv", "en", "论文", "Paper", "06:36"),
      src("机器之心", "zh", "媒体", "Press", "07:21")
    ],
    timeline: [
      { time: "06:36", text: tx("GLM Agent 基准与论文同步放出。", "The GLM agent bench and paper drop together.") },
      { time: "07:21", text: tx("中文媒体强调中文任务切分。", "Chinese press highlights the Chinese task split.") }
    ]
  },
  {
    slug: "diffusion-lm-code",
    date: "2026-09-14",
    topicSlug: "research",
    section: "more",
    title: tx("扩散语言模型在代码补全追上自回归", "Diffusion LMs catch autoregressive models on code completion"),
    dek: tx("延迟曲线第一次看起来能进编辑器。", "The latency curve looks editor-ready for the first time."),
    synthesis: [
      tx("非自回归解码在代码补全上追平主流自回归模型，且把尾延迟压下来。还不是训练新闻，是编辑器能不能用的新闻。", "Non-autoregressive decoding ties mainstream AR models on code completion and cuts tail latency. This is not a training story. It is an editor-readiness story.")
    ],
    sources: [
      src("arXiv", "en", "论文", "Paper", "06:00"),
      src("GitHub", "en", "代码", "Code", "07:40")
    ],
    timeline: [
      { time: "06:00", text: tx("论文上线，代码补全数字打平。", "The paper lands; code-completion numbers tie.") },
      { time: "07:40", text: tx("参考实现出现在 GitHub。", "A reference implementation appears on GitHub.") }
    ]
  },
  {
    slug: "hf-free-tier",
    date: "2026-09-14",
    topicSlug: "open-source",
    section: "more",
    title: tx("Hugging Face 免费推理额度下调", "Hugging Face cuts the free inference allowance"),
    dek: tx("免费演示还能做，免费生产不能再装。", "Free demos still work. Free production does not."),
    synthesis: [
      tx("免费推理额度下调后，教学和 demo 还撑得住，把 HF 当生产推理后端的项目要搬家。这是平台定价，不是模型新闻。", "After the cut, teaching and demos still hold. Projects using HF as a production inference backend need to move. This is platform pricing, not a model story.")
    ],
    sources: [
      src("HF Blog", "en", "一手", "Primary", "07:11"),
      src("Hacker News", "en", "讨论", "Forum", "07:28")
    ],
    timeline: [
      { time: "07:11", text: tx("Hugging Face 宣布免费额度调整。", "Hugging Face announces the free-tier change.") }
    ]
  },
  {
    slug: "tongyi-cockpit",
    date: "2026-09-14",
    topicSlug: "industry-cn",
    section: "more",
    title: tx("通义与三家车厂签座舱模型", "Tongyi signs cockpit-model deals with three automakers"),
    dek: tx("车舱要的是可关麦、可离线、可追责，不是聊天分数。", "Cabins want mute, offline, and accountability — not chat scores."),
    synthesis: [
      tx("签约新闻的重点不是又一个车载助手，是座舱场景把端侧、语音和责任链条写进了合同附件。", "The news is not another in-car assistant. It is that cockpit scenes wrote on-device, voice, and liability into the contract annex.")
    ],
    sources: [
      src("36氪", "zh", "媒体", "Press", "07:02"),
      src("晚点", "zh", "媒体", "Press", "07:25")
    ],
    timeline: [
      { time: "07:02", text: tx("36氪先报三家车厂签约。", "36Kr reports the three automaker deals first.") }
    ]
  }
];