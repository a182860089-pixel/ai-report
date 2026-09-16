"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { T } from "@/components/Text";
import { ApiError, searchStories } from "@/lib/api";
import type { StorySummary } from "@/data/types";
import { formatLongDate, startOfWeek } from "@/lib/dates";
import { useLocale } from "@/lib/locale";

export function SearchPanel({ currentDate }: { currentDate: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const { locale } = useLocale();
  const q = params.get("q") ?? "";
  const inputRef = useRef<HTMLInputElement>(null);
  const [results, setResults] = useState<StorySummary[]>([]);
  const [error, setError] = useState<"query" | "rate" | "fail" | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const needle = q.trim();
    if (!needle) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }
    if (needle.length > 100) {
      setResults([]);
      setError("query");
      setLoading(false);
      return;
    }

    setLoading(true);
    setResults([]);
    const ac = new AbortController();
    const timer = window.setTimeout(() => {
      searchStories(needle, ac.signal)
        .then((items) => {
          setResults(items);
          setError(null);
          setLoading(false);
        })
        .catch((err) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          if (err instanceof ApiError && err.status === 429) {
            setError("rate");
            setLoading(false);
            return;
          }
          setError("fail");
          setLoading(false);
        });
    }, 350);

    return () => {
      window.clearTimeout(timer);
      ac.abort();
    };
  }, [q]);

  const weekStart = startOfWeek(currentDate);
  const today = results.filter((story) => story.date === currentDate);
  const week = results.filter((story) => story.date !== currentDate && story.date >= weekStart);
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
      ) : loading ? (
        <p className="empty">
          <T zh="搜索中…" en="Searching…" />
        </p>
      ) : error === "query" ? (
        <p className="empty">
          <T zh="查询太长，最多 100 个字符。" en="Query is too long. 100 characters max." />
        </p>
      ) : error === "rate" ? (
        <p className="empty">
          <T zh="搜得太快，稍等再试。" en="Too many searches. Wait a moment and try again." />
        </p>
      ) : error === "fail" ? (
        <p className="empty">
          <T zh="搜索服务不可用。确认 FastAPI 已启动。" en="Search is unavailable. Is FastAPI running?" />
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
  stories: StorySummary[];
}) {
  if (stories.length === 0) return null;
  return (
    <>
      <h2 className="h2">
        <T zh={titleZh} en={titleEn} />
      </h2>
      {stories.map((story) => {
        const date = formatLongDate(story.date);
        const rank = story.section === "must" && story.rank != null
          ? { zh: `必读 ${String(story.rank).padStart(2, "0")}`, en: `Must-read ${String(story.rank).padStart(2, "0")}` }
          : null;
        return (
          <Link key={story.slug} className="hit press" href={`/story/${story.slug}`}>
            <b>
              <T zh={story.title.zh} en={story.title.en} />
            </b>
            <p className="note">
              {rank ? <><T zh={rank.zh} en={rank.en} /> · </> : null}
              <T zh={date.zh} en={date.en} /> · {story.sourceCount} <T zh="信源" en="sources" />
              {story.topic ? <> · <T zh={story.topic.name.zh} en={story.topic.name.en} /></> : null}
            </p>
          </Link>
        );
      })}
    </>
  );
}
