export type Locale = "zh" | "en";

export type Text = {
  zh: string;
  en: string;
};

export type TopicRef = {
  slug: string;
  name: Text;
};

export type SourceRef = {
  name: string;
  lang: Locale;
  kind: Text;
  time: string;
};

export type TimelineItem = {
  time: string;
  text: Text;
};

export type StorySummary = {
  slug: string;
  date: string;
  topicSlug: string;
  rank: number | null;
  section: "must" | "more";
  title: Text;
  dek: Text;
  topic: TopicRef;
  sourceCount: number;
  sourceNames: string[];
};

export type Story = {
  slug: string;
  date: string;
  topicSlug: string;
  rank: number | null;
  section: "must" | "more";
  title: Text;
  dek: Text;
  topic: TopicRef;
  synthesis: Text[];
  sources: SourceRef[];
  timeline: TimelineItem[];
};

export type PulseTopic = {
  name: Text;
  count: number;
};

export type Briefing = {
  date: string;
  weekday: Text;
  updatedAt: string;
  title: Text;
  lede: Text[];
  mustRead: StorySummary[];
  moreHeading: Text;
  more: StorySummary[];
  pulse: {
    clusters: number;
    articles: number;
    zhEn: string;
    healthy: number;
    totalSources: number;
    topics: PulseTopic[];
  };
};

export type BriefingListItem = {
  date: string;
  weekday: Text;
  title: Text;
  updatedAt: string;
  mustReadCount: number;
  clusters: number;
};

export type SourceStatus = "ok" | "late" | "bad";

export type Source = {
  id: string;
  name: string;
  status: SourceStatus;
  lastFetch: string;
  todayCount: number;
  detail: Text;
};

export type Topic = {
  slug: string;
  name: Text;
  blurb: Text;
  clusterCount: number;
};

export type TopicDetail = Topic & {
  stories: StorySummary[];
};

export type Meta = {
  currentDate: string;
  timezone: string;
};

export type MockStory = Omit<Story, "topic" | "rank"> & {
  rank?: number;
};

export type MockTopic = Omit<Topic, "clusterCount">;
