import { tx } from "./text";
import type { Briefing } from "./types";

export type BriefingMeta = Omit<Briefing, "mustRead" | "more">;

function meta(
  date: string,
  weekdayZh: string,
  weekdayEn: string,
  updatedAt: string,
  titleZh: string,
  titleEn: string,
  lede: [string, string][],
  moreZh: string,
  moreEn: string,
  clusters: number,
  articles: number,
  zhEn: string,
  healthy: number,
  pulse: [string, string, number][]
): BriefingMeta {
  return {
    date,
    weekday: tx(weekdayZh, weekdayEn),
    updatedAt,
    title: tx(titleZh, titleEn),
    lede: lede.map(([zh, en]) => tx(zh, en)),
    moreHeading: tx(moreZh, moreEn),
    pulse: {
      clusters,
      articles,
      zhEn,
      healthy,
      totalSources: 26,
      topics: pulse.map(([zh, en, count]) => ({ name: tx(zh, en), count }))
    }
  };
}

export const briefingMeta: Record<string, BriefingMeta> = {
  "2026-09-01": meta("2026-09-01", "星期二", "Tuesday", "07:08",
    "新基准周拉开：幻觉被拆开打分", "Eval week opens: hallucinations get split scores",
    [
      ["新套件把幻觉拆成三类错误，实验室终于能互相比。", "A new suite splits hallucinations into three error types."],
      ["开源推理引擎开始共享前缀缓存。", "Open inference engines start sharing prefix caches."],
      ["欧洲实验室公开红队日志格式。", "European labs publish a red-team log format."]
    ], "更多 · 评测", "More · Evals", 11, 72, "3 : 2", 24,
    [["研究", "Research", 4], ["智能体", "Agents", 3], ["开源权重", "Open weights", 2]]),
  "2026-09-02": meta("2026-09-02", "星期三", "Wednesday", "07:04",
    "开源许可再起争执：能跑不等于能卖", "Licenses flare again: runnable is not sellable",
    [
      ["律师把 Apache-2.0 和「可商用」重新拆开。", "Lawyers split Apache-2.0 from “commercial use” again."],
      ["社区复现被条款拦在模型卡外。", "Replications stall on model-card clauses."],
      ["权重发布开始写地域限制。", "Weight releases start listing regional limits."]
    ], "更多 · 开源", "More · Open source", 9, 61, "1 : 1", 25,
    [["开源权重", "Open weights", 4], ["政策", "Policy", 2], ["中文产业", "China industry", 1]]),
  "2026-09-03": meta("2026-09-03", "星期四", "Thursday", "07:15",
    "推理成本被重新计价", "Inference gets repriced",
    [
      ["批处理折扣从实验区挪进默认价目表。", "Batch discounts move from labs into default price lists."],
      ["长上下文缓存命中率成为新 KPI。", "Long-context cache hit rate becomes a KPI."],
      ["中文云厂商跟进夜间闲时价。", "Chinese clouds follow with off-peak night rates."]
    ], "更多 · 基础设施", "More · Infra", 8, 58, "2 : 3", 24,
    [["芯片", "Chips", 3], ["模型发布", "Model launches", 2], ["中文产业", "China industry", 2]]),
  "2026-09-04": meta("2026-09-04", "星期五", "Friday", "07:11",
    "多模态代理挤进办公套件", "Multimodal agents push into office suites",
    [
      ["表格、邮件、日历被同一条工具链串起来。", "Sheets, mail, and calendar share one tool chain."],
      ["演示很满，审计日志仍然空。", "Demos are full; audit logs are still empty."],
      ["中文办公套件开始卖「代办权限包」。", "Chinese office suites start selling delegated-permission packs."]
    ], "更多 · 产品", "More · Product", 12, 80, "4 : 3", 25,
    [["智能体", "Agents", 5], ["模型发布", "Model launches", 3], ["安全", "Safety", 2]]),
  "2026-09-05": meta("2026-09-05", "星期六", "Saturday", "07:02",
    "监管口径开始对齐，定义仍在打架", "Regulators align on tone, not definitions",
    [
      ["通用模型义务的草稿开始互相抄附录。", "GPAI drafts start copying each other’s annexes."],
      ["开源豁免的边界比禁令更惹火。", "Open-source exemptions draw more heat than bans."],
      ["企业法务要一份「能不能上线」的清单，没有人给得出。", "Counsel wants a ship / no-ship list. Nobody has one."]
    ], "更多 · 政策", "More · Policy", 7, 49, "2 : 5", 24,
    [["政策", "Policy", 4], ["安全", "Safety", 2], ["开源权重", "Open weights", 1]]),
  "2026-09-06": meta("2026-09-06", "星期日", "Sunday", "07:00",
    "周末论文潮：扩散模型改去代码", "Sunday papers: diffusion models go after code",
    [
      ["非自回归解码在补全延迟上第一次像样。", "Non-autoregressive decoding looks serious on completion latency."],
      ["机器人 VLA 论文把仓库拣选写成主任务。", "Robot VLA papers make warehouse picking the headline task."],
      ["中文预训练数据清洗方法被单独开源。", "Chinese pretraining cleanup methods get their own release."]
    ], "更多 · 论文", "More · Papers", 6, 44, "1 : 4", 23,
    [["研究", "Research", 3], ["机器人", "Robotics", 2], ["开源权重", "Open weights", 1]]),
  "2026-09-07": meta("2026-09-07", "星期一", "Monday", "07:09",
    "端侧运行时换代，NPU 抢调度权", "On-device runtimes turn over; NPUs grab the scheduler",
    [
      ["新运行时把 8B 模型的首字延迟压进 200ms。", "A new runtime pushes 8B time-to-first-token under 200ms."],
      ["手机厂商开始在系统设置里暴露「本地模型」。", "Phone makers expose “local model” in system settings."],
      ["开发者文档把 GPU、NPU、CPU 写成三套后端。", "Docs now list GPU, NPU, and CPU as three backends."]
    ], "更多 · 端侧", "More · On-device", 10, 66, "3 : 2", 25,
    [["端侧", "On-device", 4], ["芯片", "Chips", 3], ["开源权重", "Open weights", 2]])
};