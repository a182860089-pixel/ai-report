import { tx } from "./text";
import type { BriefingMeta } from "./briefings";

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

export const lateBriefings: Record<string, BriefingMeta> = {
  "2026-09-08": meta("2026-09-08", "星期二", "Tuesday", "07:06",
    "训练集群交付延期，供应新闻压过参数新闻", "Cluster slips: supply beats parameter counts",
    [
      ["两家云把 Q4 训练集群交付再往后推。", "Two clouds slip Q4 training-cluster delivery again."],
      ["二手 A100 价格反过来涨。", "Used A100 prices tick up."],
      ["国内液冷机柜订单被提前锁。", "Domestic liquid-cooling racks get locked early."]
    ], "更多 · 供应", "More · Supply", 13, 77, "5 : 4", 24,
    [["芯片", "Chips", 5], ["中文产业", "China industry", 3], ["政策", "Policy", 2]]),
  "2026-09-09": meta("2026-09-09", "星期三", "Wednesday", "07:13",
    "中文模型抢企业合同，基准分数退居附录", "Chinese models hunt contracts; benches fall to the appendix",
    [
      ["采购清单把私有化部署写成第一行。", "Procurement lists put private deployment on line one."],
      ["客服质检和公文草稿成了可签的场景。", "QA for support and draft memos become signable scenes."],
      ["开源权重被用来压价，而不是上生产。", "Open weights are used to beat down price, not to ship."]
    ], "更多 · 产业", "More · Industry", 9, 63, "5 : 2", 24,
    [["中文产业", "China industry", 4], ["模型发布", "Model launches", 3], ["开源权重", "Open weights", 2]]),
  "2026-09-10": meta("2026-09-10", "星期四", "Thursday", "07:07",
    "安全评测集中发布，记忆功能被写成威胁模型", "Safety evals land; memory becomes a threat model",
    [
      ["跨会话记忆第一次被单独列进红队范围。", "Cross-session memory is listed as its own red-team surface."],
      ["越狱套件开始打「长期用户画像」。", "Jailbreak kits start targeting long-term user profiles."],
      ["企业要可关、可导出、可删除，三件事一起要。", "Enterprises want off, export, and delete — all three."]
    ], "更多 · 安全", "More · Safety", 8, 55, "2 : 3", 25,
    [["安全", "Safety", 4], ["政策", "Policy", 2], ["产品", "Product", 2]]),
  "2026-09-11": meta("2026-09-11", "星期五", "Friday", "07:16",
    "记忆功能变成合规问题", "Memory turns into a compliance problem",
    [
      ["Anthropic 企业控制台增加数据保留开关。", "Anthropic adds retention controls to the enterprise console."],
      ["隐私论文开始把跨会话记忆写成独立题目。", "Privacy papers start treating cross-session memory as its own topic."],
      ["采购合同出现「默记关闭」条款。", "Procurement contracts add a default-memory-off clause."]
    ], "更多 · 合规", "More · Compliance", 11, 70, "3 : 4", 25,
    [["安全", "Safety", 4], ["政策", "Policy", 3], ["模型发布", "Model launches", 2]]),
  "2026-09-12": meta("2026-09-12", "星期六", "Saturday", "07:03",
    "开源推理引擎对打，吞吐数字满天飞", "Open inference engines trade blows; throughput numbers fly",
    [
      ["两套引擎在同一张 H100 上把数字打到小数点后两位。", "Two engines fight to two decimal places on the same H100."],
      ["前缀缓存和投机解码被写成默认。", "Prefix cache and speculative decoding become defaults."],
      ["中文社区开始给国产卡写后端。", "Chinese community backends appear for domestic accelerators."]
    ], "更多 · 推理", "More · Inference", 10, 64, "4 : 3", 24,
    [["开源权重", "Open weights", 4], ["芯片", "Chips", 3], ["研究", "Research", 2]]),
  "2026-09-13": meta("2026-09-13", "星期日", "Sunday", "07:10",
    "端侧小模型挤进 IDE", "Tiny on-device models squeeze into IDEs",
    [
      ["补全不再必须出公网。本地 8B 被写进编辑器设置。", "Completion no longer needs the public net. Local 8B lands in editor settings."],
      ["隐私团队把「代码不离机」当成可卖的开关。", "Privacy teams sell “code never leaves the machine” as a switch."],
      ["离线 Agent 开始在无网环境跑测试。", "Offline agents start running tests with the network down."]
    ], "更多 · 开发者工具", "More · Developer tools", 9, 59, "3 : 2", 24,
    [["端侧", "On-device", 3], ["智能体", "Agents", 3], ["安全", "Safety", 2]]),
  "2026-09-14": meta("2026-09-14", "星期一", "Monday", "07:12",
    "发布周对撞：闭源降价，开源抢榜", "Launch week collision: closed models cut price, open weights grab the board",
    [
      ["OpenAI 把 GPT-5.5 长上下文默认开到 1M，推理价腰斩。", "OpenAI makes 1M context the GPT-5.5 default and halves inference price."],
      ["Anthropic 上线跨会话记忆，企业默认关闭。", "Anthropic ships cross-session memory, off by default for enterprises."],
      ["Kimi 新权重部分开源，LMSYS 冲进前五。", "Kimi partially open-sources new weights and cracks LMSYS top five."]
    ], "更多 · 开源与研究", "More · Open source & research", 14, 86, "4 : 3", 24,
    [["模型发布", "Model launches", 4], ["开源权重", "Open weights", 3], ["芯片供应", "Chip supply", 2], ["政策合规", "Policy", 2], ["机器人", "Robotics", 1]])
};