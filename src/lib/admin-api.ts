import type { Briefing, Source, Story, StorySummary, Text, Topic } from "@/data/types";
import { ApiError, isNotFoundError } from "@/lib/api";

export { ApiError, isNotFoundError };

const SESSION_KEY = "ai-report.admin.session";

export type AdminSession = {
  accessToken: string;
  refreshToken: string;
  email: string;
};

export type AdminTopic = Topic & {
  sortOrder: number;
  isActive: boolean;
  stories?: StorySummary[];
};

export type AdminSource = Source & {
  consecutiveFailures: number;
  isQuarantined: boolean;
  homepageUrl: string | null;
  feedUrl: string | null;
};

export type AdminBriefingListItem = {
  date: string;
  weekday: Text;
  title: Text;
  updatedAt: string;
  mustReadCount: number;
  clusters: number;
  status: "draft" | "published";
};

export type AdminBriefing = Briefing & {
  status: "draft" | "published";
};

export type AdminCitation = {
  name: string;
  lang: "zh" | "en";
  kind: Text;
  time: string;
  sourceCode: string | null;
};

export type AdminStory = Omit<Story, "sources"> & {
  sources: AdminCitation[];
};

export type AuditItem = {
  action: string;
  resource: string;
  createdAt: string;
  actorEmail: string;
  metadata: Record<string, unknown>;
};


export type PipelineRun = {
  sourceCode: string;
  status: "running" | "ok" | "error" | "blocked";
  feedUrl: string;
  httpStatus: number | null;
  bytesRead: number;
  articleCount: number;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string;
  finishedAt: string | null;
};

export type PipelineSkip = {
  code: string;
  reason: string;
};

export type PipelineArticle = {
  sourceCode: string;
  guid: string;
  canonicalUrl: string;
  title: string;
  summary: string;
  lang: "zh" | "en" | "und";
  publishedAt: string | null;
  fetchedAt: string;
  clustered: boolean;
};

export type PipelineJob = {
  date: string;
  status: "ok" | "error";
  writer: "template" | "llm";
  storyCount: number;
  articleCount: number;
  createdAt: string;
  createdByEmail: string | null;
  slugs?: string[];
};

export type PipelineTick = {
  startedAt: string;
  finishedAt: string;
  trigger: "manual" | "schedule";
  fetchRunCount: number;
  skippedCount: number;
  clusterStatus: string;
  storyCount: number;
  articleCount: number;
  slugs: string[];
  date: string | null;
  errorCode: string | null;
  errorMessage: string | null;
};

export type PipelineSchedule = {
  enabled: boolean;
  times: string[];
  timezone: string;
  autoCluster: boolean;
  nextRunAt: string | null;
  lastTick: PipelineTick | null;
};

type SuccessEnvelope<T> = { data: T };
type ErrorEnvelope = { error?: { code?: string; message?: string } };

let refreshGate: Promise<boolean> | null = null;

export function loadAdminSession(): AdminSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AdminSession;
    if (!parsed.accessToken || !parsed.refreshToken || !parsed.email) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveAdminSession(session: AdminSession | null) {
  if (typeof window === "undefined") return;
  if (!session) sessionStorage.removeItem(SESSION_KEY);
  else sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function adminUrl(path: string) {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `/api/v1${suffix}`;
}

async function parseBody<T>(response: Response): Promise<T> {
  const body = (await response.json().catch(() => null)) as SuccessEnvelope<T> | ErrorEnvelope | null;
  if (!response.ok) {
    const code = body && "error" in body ? body.error?.code ?? "INTERNAL_ERROR" : "INTERNAL_ERROR";
    const message =
      body && "error" in body ? body.error?.message ?? `HTTP ${response.status}` : `HTTP ${response.status}`;
    throw new ApiError(response.status, code, message);
  }
  if (!body || !("data" in body)) {
    throw new ApiError(500, "INTERNAL_ERROR", "Malformed API response.");
  }
  return body.data;
}

async function rawSend<T>(path: string, init: RequestInit, timeoutMs = 10000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(adminUrl(path), {
      cache: "no-store",
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers ?? {})
      }
    });
    return await parseBody<T>(response);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (typeof error === "object" && error !== null && "name" in error && error.name === "AbortError") {
      throw new ApiError(503, "INTERNAL_ERROR", "API unreachable. Start FastAPI and set API_BASE.");
    }
    throw new ApiError(503, "INTERNAL_ERROR", "API unreachable. Start FastAPI and set API_BASE.");
  } finally {
    clearTimeout(timer);
  }
}

export async function loginAdmin(email: string, password: string): Promise<AdminSession> {
  const data = await rawSend<{
    accessToken: string;
    refreshToken: string;
    admin: { email: string };
  }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  const session = { accessToken: data.accessToken, refreshToken: data.refreshToken, email: data.admin.email };
  saveAdminSession(session);
  return session;
}

async function refreshSession(): Promise<boolean> {
  if (refreshGate) return refreshGate;
  refreshGate = (async () => {
    const session = loadAdminSession();
    if (!session) return false;
    try {
      const data = await rawSend<{
        accessToken: string;
        refreshToken: string;
        admin: { email: string };
      }>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refreshToken: session.refreshToken })
      });
      saveAdminSession({
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
        email: data.admin.email
      });
      return true;
    } catch {
      saveAdminSession(null);
      return false;
    }
  })();
  try {
    return await refreshGate;
  } finally {
    refreshGate = null;
  }
}

async function authSend<T>(method: string, path: string, body?: unknown, retried = false, timeoutMs = 10000): Promise<T> {
  const session = loadAdminSession();
  if (!session) throw new ApiError(401, "UNAUTHORIZED", "Invalid access token.");
  try {
    return await rawSend<T>(path, {
      method,
      headers: { Authorization: `Bearer ${session.accessToken}` },
      body: body === undefined ? undefined : JSON.stringify(body)
    }, timeoutMs);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401 && !retried) {
      const ok = await refreshSession();
      if (ok) return authSend<T>(method, path, body, true, timeoutMs);
    }
    if (error instanceof ApiError && error.status === 403 && error.code === "FORBIDDEN") {
      saveAdminSession(null);
    }
    throw error;
  }
}

export async function logoutAdmin() {
  const session = loadAdminSession();
  try {
    if (session) {
      await rawSend("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.accessToken}` },
        body: JSON.stringify({ refreshToken: session.refreshToken })
      });
    }
  } catch {
    // local session still drops
  } finally {
    saveAdminSession(null);
  }
}

export const adminApi = {
  me: () => authSend<{ email: string }>("GET", "/admin/me"),
  topics: () => authSend<{ items: AdminTopic[] }>("GET", "/admin/topics").then((d) => d.items),
  topic: (slug: string) => authSend<AdminTopic>("GET", `/admin/topics/${encodeURIComponent(slug)}`),
  createTopic: (body: unknown) => authSend<AdminTopic>("POST", "/admin/topics", body),
  patchTopic: (slug: string, body: unknown) =>
    authSend<AdminTopic>("PATCH", `/admin/topics/${encodeURIComponent(slug)}`, body),
  deleteTopic: (slug: string) => authSend<{ ok: true }>("DELETE", `/admin/topics/${encodeURIComponent(slug)}`),
  sources: () => authSend<{ items: AdminSource[] }>("GET", "/admin/sources").then((d) => d.items),
  source: (code: string) => authSend<AdminSource>("GET", `/admin/sources/${encodeURIComponent(code)}`),
  createSource: (body: unknown) => authSend<AdminSource>("POST", "/admin/sources", body),
  patchSource: (code: string, body: unknown) =>
    authSend<AdminSource>("PATCH", `/admin/sources/${encodeURIComponent(code)}`, body),
  deleteSource: (code: string) => authSend<{ ok: true }>("DELETE", `/admin/sources/${encodeURIComponent(code)}`),
  briefings: (from: string, to: string) =>
    authSend<{ items: AdminBriefingListItem[] }>(
      "GET",
      `/admin/briefings?${new URLSearchParams({ from, to }).toString()}`
    ).then((d) => d.items),
  briefing: (date: string) => authSend<AdminBriefing>("GET", `/admin/briefings/${encodeURIComponent(date)}`),
  createBriefing: (body: unknown) => authSend<AdminBriefing>("POST", "/admin/briefings", body),
  patchBriefing: (date: string, body: unknown) =>
    authSend<AdminBriefing>("PATCH", `/admin/briefings/${encodeURIComponent(date)}`, body),
  publish: (date: string) => authSend<AdminBriefing>("POST", `/admin/briefings/${encodeURIComponent(date)}/publish`),
  unpublish: (date: string) =>
    authSend<AdminBriefing>("POST", `/admin/briefings/${encodeURIComponent(date)}/unpublish`),
  deleteBriefing: (date: string) =>
    authSend<{ ok: true }>("DELETE", `/admin/briefings/${encodeURIComponent(date)}`),
  stories: (query?: { date?: string; topic?: string }) => {
    const params = new URLSearchParams();
    if (query?.date) params.set("date", query.date);
    if (query?.topic) params.set("topic", query.topic);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return authSend<{ items: StorySummary[] }>("GET", `/admin/stories${suffix}`).then((d) => d.items);
  },
  story: (slug: string) => authSend<AdminStory>("GET", `/admin/stories/${encodeURIComponent(slug)}`),
  createStory: (body: unknown) => authSend<AdminStory>("POST", "/admin/stories", body),
  patchStory: (slug: string, body: unknown) =>
    authSend<AdminStory>("PATCH", `/admin/stories/${encodeURIComponent(slug)}`, body),
  deleteStory: (slug: string) => authSend<{ ok: true }>("DELETE", `/admin/stories/${encodeURIComponent(slug)}`),
  audit: (limit = 50) =>
    authSend<{ items: AuditItem[] }>("GET", `/admin/audit?limit=${limit}`).then((d) => d.items),
  fetchPipeline: (codes?: string[]) =>
    authSend<{ runs: PipelineRun[]; skipped: PipelineSkip[] }>(
      "POST",
      "/admin/pipeline/fetch",
      codes === undefined ? {} : { codes },
      false,
      120000
    ),
  pipelineRuns: (limit = 50) =>
    authSend<{ items: PipelineRun[] }>("GET", `/admin/pipeline/runs?limit=${limit}`).then((d) => d.items),
  pipelineArticles: (query?: { source?: string; from?: string; to?: string }) => {
    const params = new URLSearchParams();
    if (query?.source) params.set("source", query.source);
    if (query?.from) params.set("from", query.from);
    if (query?.to) params.set("to", query.to);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return authSend<{ items: PipelineArticle[] }>("GET", `/admin/pipeline/articles${suffix}`).then((d) => d.items);
  },
  clusterPipeline: (date: string) =>
    authSend<PipelineJob>("POST", "/admin/pipeline/cluster", { date }, false, 120000),
  pipelineJobs: (limit = 50) =>
    authSend<{ items: PipelineJob[] }>("GET", `/admin/pipeline/jobs?limit=${limit}`).then((d) => d.items),
  pipelineSchedule: () => authSend<PipelineSchedule>("GET", "/admin/pipeline/schedule"),
  pipelineTick: () => authSend<PipelineTick>("POST", "/admin/pipeline/tick", {}, false, 120000)
};
