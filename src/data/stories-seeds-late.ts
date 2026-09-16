import { src, tx } from "./text";
import type { MockStory as Story } from "./types";

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
  ["2026-09-08", 1, "must", "chips", "两家云把 Q4 训练集群再往后推", "Two clouds slip Q4 training clusters again", "参数规模新闻让位给到货日期。", "Parameter-count news yields to arrival dates.", [["Bloomberg", "en"], ["财新", "zh"]]],
  ["2026-09-08", 2, "must", "chips", "二手 A100 价格反过来涨", "Used A100 prices tick up", "旧卡成为对冲，不是淘汰品。", "Old cards become a hedge, not scrap.", [["The Information", "en"], ["36氪", "zh"]]],
  ["2026-09-08", 0, "more", "industry-cn", "国内液冷机柜订单被提前锁", "Domestic liquid-cooling racks get locked early", "供电和制冷比芯片本身更早成为瓶颈。", "Power and cooling bottleneck before the chips do.", [["财新", "zh"]]],
  ["2026-09-09", 1, "must", "industry-cn", "采购清单把私有化部署写成第一行", "Procurement puts private deployment on line one", "分数变成附录，部署形态变成标题。", "Scores fall to the appendix. Deployment shape becomes the title.", [["36氪", "zh"], ["晚点", "zh"]]],
  ["2026-09-09", 2, "must", "models", "客服质检和公文草稿成为可签场景", "Support QA and memo drafts become signable scenes", "能进合同的不是通用聊天，是有工单的流程。", "What enters a contract is not general chat. It is a ticketed workflow.", [["机器之心", "zh"], ["36氪", "zh"]]],
  ["2026-09-09", 0, "more", "open-source", "开源权重被用来压价，而不是上生产", "Open weights are used to beat down price, not to ship", "谈判桌上的对照物，未必会进机房。", "The comparison object on the table may never enter the room.", [["晚点", "zh"]]],
  ["2026-09-10", 1, "must", "safety", "跨会话记忆被单独列进红队范围", "Cross-session memory is listed as its own red-team surface", "攻击的是画像，不是单次提示。", "The attack is the profile, not a single prompt.", [["arXiv", "en"], ["Wired", "en"]]],
  ["2026-09-10", 2, "must", "safety", "越狱套件开始打长期用户画像", "Jailbreak kits start targeting long-term user profiles", "今天套一套，下周用你自己的偏好打你。", "Probe this week, then use your own preferences against you next week.", [["Hacker News", "en"], ["机器之心", "zh"]]],
  ["2026-09-10", 0, "more", "policy", "企业同时要关闭、导出和删除", "Enterprises want off, export, and delete together", "三件套缺一，合同就卡着。", "Missing any of the three stalls the contract.", [["Reuters", "en"]]],
  ["2026-09-11", 2, "must", "policy", "采购合同出现「默记关闭」条款", "Procurement contracts add a default-memory-off clause", "产品还没上线，法务已经在改模板。", "The product is not live yet. Counsel is already editing the template.", [["The Information", "en"], ["36氪", "zh"]]],
  ["2026-09-11", 3, "must", "models", "消费级助手把「记得我」写成默认能力", "Consumer assistants make “it remembers me” a default", "个人向产品在训练用户习惯，企业向产品在训练关闭。", "Consumer products train the habit on. Enterprise products train the habit off.", [["The Verge", "en"], ["量子位", "zh"]]],
  ["2026-09-12", 1, "must", "open-source", "两套开源引擎在同一张 H100 上对打", "Two open engines fight on the same H100", "数字打到小数点后两位，配置差异被故意写小。", "Numbers go to two decimals. Config differences are written small on purpose.", [["GitHub", "en"], ["Hacker News", "en"]]],
  ["2026-09-12", 2, "must", "open-source", "前缀缓存和投机解码被写成默认", "Prefix cache and speculative decoding become defaults", "关闭它们才能复现「官方延迟」。", "You have to turn them off to reproduce the “official” latency.", [["GitHub", "en"], ["arXiv", "en"]]],
  ["2026-09-12", 0, "more", "chips", "中文社区给国产卡写推理后端", "Chinese community backends appear for domestic accelerators", "这是适配新闻，也是供应新闻。", "It is an adapter story, and a supply story.", [["机器之心", "zh"], ["GitHub", "en"]]]
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

export const seedStoriesLate: Story[] = rows.map(storyFromRow);