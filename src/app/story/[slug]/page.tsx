import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeftIcon } from "@/components/Icons";
import { T } from "@/components/Text";
import { CURRENT_DATE, getStory, getTopic, listBriefingDates, stories } from "@/data";
import { formatLongDate } from "@/lib/dates";

type Props = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return stories.map((story) => ({ slug: story.slug }));
}

export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const story = getStory(slug);
  return { title: story?.title.zh ?? "事件簇" };
}

export default async function StoryPage({ params }: Props) {
  const { slug } = await params;
  const story = getStory(slug);
  if (!story) notFound();
  const topic = getTopic(story.topicSlug);
  const backHref = story.date === CURRENT_DATE ? "/" : `/d/${story.date}`;
  const backDate = formatLongDate(story.date);
  const times = story.timeline.map((item) => item.time);
  const range = times.length > 1 ? `${times[0]}–${times[times.length - 1]}` : times[0] ?? "";
  const hasZh = story.sources.some((item) => item.lang === "zh");
  const hasEn = story.sources.some((item) => item.lang === "en");
  const confidence = story.sources.length >= 5
    ? { zh: "置信度高", en: "High confidence" }
    : { zh: "置信度中", en: "Medium confidence" };
  const knownDates = new Set(listBriefingDates());

  return (
    <article>
      <Link className="back press" href={knownDates.has(story.date) ? backHref : "/"}>
        <ArrowLeftIcon />
        <T
          zh={story.date === CURRENT_DATE ? "返回今日早报" : `返回 ${backDate.zh}早报`}
          en={story.date === CURRENT_DATE ? "Back to today’s briefing" : `Back to ${backDate.en}`}
        />
      </Link>
      <div className="kicker kicker-sp">
        CLUSTER · {topic ? <T zh={topic.name.zh} en={topic.name.en} /> : story.topicSlug}
      </div>
      <h1 className="display display-sm">
        <T zh={story.title.zh} en={story.title.en} />
      </h1>
      <p className="meta">
        {range} · {story.sources.length} <T zh="篇原文" en="articles" /> ·{" "}
        {hasZh && hasEn ? <T zh="中英都有" en="ZH and EN" /> : hasZh ? <T zh="中文" en="Chinese" /> : <T zh="英文" en="English" />}
        {" · "}
        <T zh={confidence.zh} en={confidence.en} />
      </p>
      {story.synthesis.map((item) => (
        <p className="synth" key={item.zh}>
          <T zh={item.zh} en={item.en} />
        </p>
      ))}
      <h2 className="h2">
        <T zh="时间线" en="Timeline" />
      </h2>
      <ol className="timeline">
        {story.timeline.map((item) => (
          <li key={`${item.time}-${item.text.zh}`}>
            <time>{item.time}</time>
            <span>
              <T zh={item.text.zh} en={item.text.en} />
            </span>
          </li>
        ))}
      </ol>
      <h2 className="h2 h2-sp">
        <T zh="信源" en="Sources" />
      </h2>
      <div className="card-grid">
        {story.sources.map((item) => (
          <article className="source-card" key={`${item.name}-${item.time}`}>
            <b>{item.name}</b>
            <p className="note">
              {item.lang === "zh" ? <T zh="中文" en="Chinese" /> : "EN"} · <T zh={item.kind.zh} en={item.kind.en} /> · {item.time}
            </p>
          </article>
        ))}
      </div>
    </article>
  );
}