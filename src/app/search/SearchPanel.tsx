"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef } from "react";
import { T } from "@/components/Text";
import { CURRENT_DATE, getTopic, searchStories } from "@/data";
import { formatLongDate, startOfWeek } from "@/lib/dates";
import { useLocale } from "@/lib/locale";

export function SearchPanel() {
  const router = useRouter();
  const params = useSearchParams();
  const { locale } = useLocale();
  const q = params.get("q") ?? "";
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const results = useMemo(() => searchStories(q), [q]);
  const weekStart = startOfWeek(CURRENT_DATE);
  const today = results.filter((story) => story.date === CURRENT_DATE);
  const week = results.filter((story) => story.date !== CURRENT_DATE && story.date >= weekStart);
  const earlier = results.filter((story) => story.date < weekStart);

  function onChange(value: string) {
    const next = value ? `/search?q=${encodeURIComponent(value)}` : "/search";
    router.replace(next, { scroll: false });
  }

  return (
    <>
      <input
        ref={inputRef}
        className="search-box"
        type="search"
        value={q}
        onChange={(event) => onChange(event.target.value)}
        placeholder={locale === "zh" ? "Claude 记忆" : "Claude memory"}
        aria-label={locale === "zh" ? "搜索事件簇" : "Search clusters"}
      />
      {!q.trim() ? (
        <p className="empty">
          <T
            zh="输入事件、模型或公司名。搜的是簇，不是原文标题。试试 Claude、Kimi、Rubin。"
            en="Type an event, model, or company. This searches clusters, not raw headlines. Try Claude, Kimi, or Rubin."
          />
        </p>
      ) : results.length === 0 ? (
        <p className="empty">
          <T zh={`没有匹配「${q.trim()}」的事件簇。`} en={`No clusters match “${q.trim()}”.`} />
        </p>
      ) : (
        <>
          <Group titleZh="今日" titleEn="Today" stories={today} />
          <Group titleZh="本周" titleEn="This week" stories={week} />
          <Group titleZh="更早" titleEn="Earlier" stories={earlier} />
        </>
      )}
    </>
  );
}

function Group({
  titleZh,
  titleEn,
  stories
}: {
  titleZh: string;
  titleEn: string;
  stories: ReturnType<typeof searchStories>;
}) {
  if (stories.length === 0) return null;
  return (
    <>
      <h2 className="h2">
        <T zh={titleZh} en={titleEn} />
      </h2>
      {stories.map((story) => {
        const topic = getTopic(story.topicSlug);
        const date = formatLongDate(story.date);
        const rank = story.section === "must" && story.rank
          ? { zh: `必读 ${String(story.rank).padStart(2, "0")}`, en: `Must-read ${String(story.rank).padStart(2, "0")}` }
          : null;
        return (
          <Link key={story.slug} className="hit press" href={`/story/${story.slug}`}>
            <b>
              <T zh={story.title.zh} en={story.title.en} />
            </b>
            <p className="note">
              {rank ? <><T zh={rank.zh} en={rank.en} /> · </> : null}
              <T zh={date.zh} en={date.en} /> · {story.sources.length} <T zh="信源" en="sources" />
              {topic ? <> · <T zh={topic.name.zh} en={topic.name.en} /></> : null}
            </p>
          </Link>
        );
      })}
    </>
  );
}