import Link from "next/link";
import { CURRENT_DATE, getStories, getTopic } from "@/data";
import type { Briefing, Story } from "@/data/types";
import { formatLongDate } from "@/lib/dates";
import { T } from "./Text";

function sourceLine(story: Story) {
  const names = story.sources.slice(0, 3).map((item) => item.name).join(" · ");
  return names;
}

function StoryRow({ story, index }: { story: Story; index: number }) {
  const topic = getTopic(story.topicSlug);
  return (
    <Link className="story-row press" href={`/story/${story.slug}`}>
      <span className="num">{String(index + 1).padStart(2, "0")}</span>
      <span>
        <h3>
          <T zh={story.title.zh} en={story.title.en} />
        </h3>
        <p>
          <T zh={story.dek.zh} en={story.dek.en} />
        </p>
        <div className="meta">
          {topic ? <span className="chip"><T zh={topic.name.zh} en={topic.name.en} /></span> : null}
          {sourceLine(story)} · {story.sources.length}{" "}
          <T zh="信源" en="sources" />
        </div>
      </span>
    </Link>
  );
}

export function BriefingView({ briefing }: { briefing: Briefing }) {
  const must = getStories(briefing.mustRead);
  const more = getStories(briefing.more);
  const longDate = formatLongDate(briefing.date);
  const isToday = briefing.date === CURRENT_DATE;

  return (
    <div className="home">
      <article>
        <div className="kicker">{isToday ? "TODAY BRIEFING" : "DAILY BRIEFING"}</div>
        <div className="date-line">
          <T zh={longDate.zh} en={longDate.en} />
          {" · "}
          <T zh={`上海 ${briefing.updatedAt} 更新`} en={`Updated ${briefing.updatedAt} CST`} />
        </div>
        <h1 className="display">
          <T zh={briefing.title.zh} en={briefing.title.en} />
        </h1>
        <ul className="lede">
          {briefing.lede.map((item) => (
            <li key={item.zh}>
              <T zh={item.zh} en={item.en} />
            </li>
          ))}
        </ul>
        <h2 className="h2">
          <T zh="今日必读" en="Must read" />
        </h2>
        {must.map((story, index) => (
          <StoryRow key={story.slug} story={story} index={index} />
        ))}
        {more.length > 0 ? (
          <div className="section">
            <h2 className="h2">
              <T zh={briefing.moreHeading.zh} en={briefing.moreHeading.en} />
            </h2>
            {more.map((story) => (
              <Link key={story.slug} className="mini press" href={`/story/${story.slug}`}>
                <strong>
                  <T zh={story.title.zh} en={story.title.en} />
                </strong>
                <span className="note">
                  {story.sources[0]?.name} · {story.sources.length}{" "}
                  <T zh="信源" en="sources" />
                </span>
              </Link>
            ))}
          </div>
        ) : null}
      </article>
      <aside className="rail" aria-labelledby="pulse-heading">
        <h2 id="pulse-heading">
          <T zh="今日脉搏" en="Today's pulse" />
        </h2>
        <div className="stat">
          <span><T zh="事件簇" en="Clusters" /></span>
          <span>{briefing.pulse.clusters}</span>
        </div>
        <div className="stat">
          <span><T zh="原文" en="Articles" /></span>
          <span>{briefing.pulse.articles}</span>
        </div>
        <div className="stat">
          <span><T zh="中 / 英" en="ZH / EN" /></span>
          <span>{briefing.pulse.zhEn}</span>
        </div>
        <div className="stat">
          <span><T zh="信源健康" en="Source health" /></span>
          <span>
            {briefing.pulse.healthy} / {briefing.pulse.totalSources}
          </span>
        </div>
        <ul className="pulse-list">
          {briefing.pulse.topics.map((topic) => (
            <li key={topic.name.zh}>
              <T zh={topic.name.zh} en={topic.name.en} /> · {topic.count}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}