export type Locale = "zh" | "en";

export type Text = {
  zh: string;
  en: string;
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

export type Story = {
  slug: string;
  date: string;
  topicSlug: string;
  rank?: number;
  section: "must" | "more";
  title: Text;
  dek: Text;
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
  mustRead: string[];
  moreHeading: Text;
  more: string[];
  pulse: {
    clusters: number;
    articles: number;
    zhEn: string;
    healthy: number;
    totalSources: number;
    topics: PulseTopic[];
  };
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
};
