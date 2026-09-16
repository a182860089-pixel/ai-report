/** Seed source for backend/fixtures. Runtime pages must not import this module. */
import { lateBriefings } from "./briefings-late";
import { briefingMeta as earlyBriefings } from "./briefings";
import { seedStoriesEarly } from "./stories-seeds";
import { seedStoriesLate } from "./stories-seeds-late";
import { recentStories } from "./stories-recent";
import { todayMoreStories } from "./stories-today-more";
import { todayStories } from "./stories-today";
import { sources, topics } from "./topics";

export const CURRENT_DATE = "2026-09-14";

export { sources, topics };

export const briefingMeta = {
  ...earlyBriefings,
  ...lateBriefings
};

export const stories = [
  ...todayStories,
  ...todayMoreStories,
  ...recentStories,
  ...seedStoriesEarly,
  ...seedStoriesLate
];