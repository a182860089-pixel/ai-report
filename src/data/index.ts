import { cache } from "react";
import * as api from "@/lib/api";

export const getMeta = cache(() => api.getMeta());
export const todayBriefing = cache(() => api.todayBriefing());
export const getBriefing = cache((date: string) => api.getBriefing(date));
export const listBriefings = cache((from: string, to: string) => api.listBriefings(from, to));
export const getStory = cache((slug: string) => api.getStory(slug));
export const listTopics = cache(() => api.listTopics());
export const getTopic = cache((slug: string) => api.getTopic(slug));
export const listSources = cache(() => api.listSources());
// Client search uses @/lib/api directly so AbortSignal works in the browser.
export const searchStories = api.searchStories;

export { ApiError, isNotFoundError } from "@/lib/api";

export type {
  Briefing,
  BriefingListItem,
  Locale,
  Meta,
  PulseTopic,
  Source,
  SourceStatus,
  Story,
  StorySummary,
  Text,
  Topic,
  TopicDetail,
  TopicRef
} from "./types";
