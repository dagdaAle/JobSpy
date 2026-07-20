import type {
  AnalyticsResponse,
  ChannelRequest,
  ChannelsResponse,
  JobsResponse,
  JobDetailResponse,
  SearchRequest,
  StatusResponse,
  Verdict,
} from "./types";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    // Never serve GETs from the browser HTTP cache — otherwise an immediate
    // refetch after a mutation can return stale data and revert the UI.
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// The backend returns feedback as { job_url: "like" } (a bare verdict string);
// the rest of the app expects { job_url: { verdict: "like" } }. Normalize here.
function normVerdict(v: unknown): { verdict?: "like" | "dislike" } {
  if (typeof v === "string") return { verdict: v as "like" | "dislike" };
  return (v as { verdict?: "like" | "dislike" }) ?? {};
}
function normJobs(res: JobsResponse): JobsResponse {
  const feedback: Record<string, { verdict?: "like" | "dislike" }> = {};
  for (const [url, v] of Object.entries(res.feedback ?? {})) feedback[url] = normVerdict(v);
  return { ...res, feedback };
}

export const api = {
  status: () => req<StatusResponse>("/status"),

  analytics: () => req<AnalyticsResponse>("/analytics"),

  jobs: () => req<JobsResponse>("/jobs").then(normJobs),

  search: (body: SearchRequest) =>
    req<JobsResponse>("/search", {
      method: "POST",
      body: JSON.stringify(body),
    }).then(normJobs),

  job: (jobUrl: string) =>
    req<JobDetailResponse>(`/job?url=${encodeURIComponent(jobUrl)}`).then((r) => ({
      ...r,
      feedback: r.feedback ? normVerdict(r.feedback) : null,
    })),

  feedback: (jobUrl: string, verdict: Verdict | null, meta?: Partial<{ title: string; company: string; site: string }>) =>
    req<{ ok: boolean }>("/feedback", {
      method: "POST",
      body: JSON.stringify({ job_url: jobUrl, verdict, ...meta }),
    }),

  channels: () => req<ChannelsResponse>("/channels"),

  createChannel: (body: ChannelRequest) =>
    req<{ channel: unknown; new_count: number }>("/channels", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteChannel: (id: number) =>
    req<{ ok: boolean; id: number }>(`/channels/${id}`, { method: "DELETE" }),

  refreshChannel: (id: number) =>
    req<{ ok: boolean; id: number; new_count: number }>(
      `/channels/${id}/refresh`,
      { method: "POST" },
    ),

  channelJobs: (id: number) =>
    req<JobsResponse>(`/channels/${id}/jobs`).then(normJobs),

  exportUrl: (format: "csv" | "xlsx") => `/export?format=${format}`,
};
