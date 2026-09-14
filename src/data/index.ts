import {
  CURRENT_DATE,
  briefingMeta,
  sources,
  stories,
  topics
} from "./catalog";
import type { Briefing, Source, Story, Topic } from "./types";

export { CURRENT_DATE, stories };
export type {
  Briefing,
  Locale,
  PulseTopic,
  Source,
  SourceStatus,
  Story,
  Text,
  Topic
} from "./types";

function byRank(a: Story, b: Story) {
  return (a.rank ?? 99) - (b.rank ?? 99);
}

export function listBriefingDates(): string[] {
  return Object.keys(briefingMeta).sort();
}

export function getBriefing(date: string = CURRENT_DATE): Briefing | undefined {
  const meta = briefingMeta[date];
  if (!meta) return undefined;
  const day = stories.filter((story) => story.date === date);
  return {
    ...meta,
    mustRead: day
      .filter((story) => story.section === "must")
      .sort(byRank)
      .map((story) => story.slug),
    more: day.filter((story) => story.section === "more").map((story) => story.slug)
  };
}

export function getStory(slug: string): Story | undefined {
  return stories.find((story) => story.slug === slug);
}

export function getStories(slugs: string[]): Story[] {
  return slugs
    .map((slug) => getStory(slug))
    .filter((story): story is Story => Boolean(story));
}

export function listTopics(): Topic[] {
  return topics;
}

export function getTopic(slug: string): Topic | undefined {
  return topics.find((topic) => topic.slug === slug);
}

export function storiesByTopic(slug: string): Story[] {
  return stories
    .filter((story) => story.topicSlug === slug)
    .sort((a, b) => b.date.localeCompare(a.date) || byRank(a, b));
}

export function listSources(): Source[] {
  return sources;
}

export function searchStories(query: string): Story[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  return stories
    .filter((story) => {
      const hay = [
        story.slug,
        story.title.zh,
        story.title.en,
        story.dek.zh,
        story.dek.en,
        ...story.synthesis.flatMap((text) => [text.zh, text.en]),
        ...story.sources.map((source) => source.name),
        getTopic(story.topicSlug)?.name.zh ?? "",
        getTopic(story.topicSlug)?.name.en ?? ""
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    })
    .sort((a, b) => b.date.localeCompare(a.date) || byRank(a, b));
}

export function todayBriefing(): Briefing {
  const briefing = getBriefing(CURRENT_DATE);
  if (!briefing) {
    throw new Error(`Missing briefing for ${CURRENT_DATE}`);
  }
  return briefing;
}