import type {
  Briefing,
  BriefingListItem,
  Meta,
  Source,
  Story,
  StorySummary,
  Topic,
  TopicDetail
} from "@/data/types";

type ErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
  };
};

type SuccessEnvelope<T> = {
  data: T;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 422);
}

function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return (
      process.env.API_BASE?.replace(/\/$/, "") ||
      process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
      "http://127.0.0.1:8000"
    );
  }
  return (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "");
}

export function apiUrl(path: string): string {
  const base = resolveApiBase();
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${base}/api/v1${suffix}`;
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const url = apiUrl(path);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort);

  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal
    });

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
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (isAbortError(error)) {
      if (signal?.aborted) throw error;
      throw new ApiError(503, "INTERNAL_ERROR", "API unreachable. Start FastAPI and set API_BASE.");
    }
    throw new ApiError(503, "INTERNAL_ERROR", "API unreachable. Start FastAPI and set API_BASE.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

export async function getMeta(signal?: AbortSignal): Promise<Meta> {
  return apiGet<Meta>("/meta", signal);
}

export async function todayBriefing(signal?: AbortSignal): Promise<Briefing> {
  return apiGet<Briefing>("/briefings/today", signal);
}

export async function getBriefing(date: string, signal?: AbortSignal): Promise<Briefing | undefined> {
  try {
    return await apiGet<Briefing>(`/briefings/${encodeURIComponent(date)}`, signal);
  } catch (error) {
    if (isNotFoundError(error)) return undefined;
    throw error;
  }
}

export async function listBriefings(from: string, to: string, signal?: AbortSignal): Promise<BriefingListItem[]> {
  const query = new URLSearchParams({ from, to });
  const data = await apiGet<{ items: BriefingListItem[] }>(`/briefings?${query.toString()}`, signal);
  return data.items;
}

export async function getStory(slug: string, signal?: AbortSignal): Promise<Story | undefined> {
  try {
    return await apiGet<Story>(`/stories/${encodeURIComponent(slug)}`, signal);
  } catch (error) {
    if (isNotFoundError(error)) return undefined;
    throw error;
  }
}

export async function listTopics(signal?: AbortSignal): Promise<Topic[]> {
  const data = await apiGet<{ items: Topic[] }>("/topics", signal);
  return data.items;
}

export async function getTopic(slug: string, signal?: AbortSignal): Promise<TopicDetail | undefined> {
  try {
    return await apiGet<TopicDetail>(`/topics/${encodeURIComponent(slug)}`, signal);
  } catch (error) {
    if (isNotFoundError(error)) return undefined;
    throw error;
  }
}

export async function listSources(signal?: AbortSignal): Promise<Source[]> {
  const data = await apiGet<{ items: Source[] }>("/sources", signal);
  return data.items;
}

export async function searchStories(query: string, signal?: AbortSignal): Promise<StorySummary[]> {
  const needle = query.trim();
  if (!needle) return [];
  if (needle.length > 100) {
    throw new ApiError(422, "VALIDATION_ERROR", "Invalid query.");
  }
  const params = new URLSearchParams({ q: needle });
  const data = await apiGet<{ query: string; items: StorySummary[] }>(`/search?${params.toString()}`, signal);
  return data.items;
}
