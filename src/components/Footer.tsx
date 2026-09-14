import { CURRENT_DATE, todayBriefing } from "@/data";
import { T } from "./Text";

export function Footer() {
  const briefing = todayBriefing();
  return (
    <footer className="foot">
      <span>
        <T zh="截止" en="As of" /> <b>{briefing.updatedAt} CST</b>
      </span>
      <span>
        <T zh="必读" en="Must-read" /> <b>{briefing.mustRead.length}</b>
      </span>
      <span>
        <T zh="事件簇" en="Clusters" /> <b>{briefing.pulse.clusters}</b>
      </span>
      <span>
        <T zh="原文" en="Articles" /> <b>{briefing.pulse.articles}</b>
      </span>
      <span>
        <T zh="信源" en="Sources" />{" "}
        <b>
          {briefing.pulse.healthy}/{briefing.pulse.totalSources}
        </b>
      </span>
      <span className="t-zh">{CURRENT_DATE}</span>
      <span className="t-en">{CURRENT_DATE}</span>
    </footer>
  );
}