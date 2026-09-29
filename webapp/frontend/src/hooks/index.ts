import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../api/client";
import type {
  ChannelRequest,
  JobsResponse,
  SearchRequest,
  Verdict,
} from "../api/types";

// Polls while the AI backlog is being worked through, so the header counter
// and the cards' scores fill in without a reload.
export function useStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: api.status,
    refetchInterval: (q) => (q.state.data?.analysis_pending ? 10_000 : 60_000),
  });
}

export function useAnalytics() {
  return useQuery({ queryKey: ["analytics"], queryFn: api.analytics });
}

// Full detail for one job (description, skills, industry, analysis) — the list
// payload omits these heavy fields, so the detail modal fetches them on open.
export function useJobDetail(jobUrl: string | null) {
  return useQuery({
    queryKey: ["job", jobUrl],
    queryFn: () => api.job(jobUrl as string),
    enabled: !!jobUrl,
  });
}

export function useChannels() {
  return useQuery({ queryKey: ["channels"], queryFn: api.channels });
}

// Update log. Polls while the page is open so a running refresh shows up.
export function useLogs(enabled = true) {
  return useQuery({
    queryKey: ["logs"],
    queryFn: () => api.logs(),
    enabled,
    refetchInterval: 30_000,
  });
}

// The active job list. `channelId === null` means "all stored jobs" (/jobs);
// a number scopes to one channel's jobs.
export function useJobs(channelId: number | null, scope: "active" | "archived" | "applications" = "active") {
  return useQuery({
    queryKey: ["jobs", channelId, scope],
    queryFn: () =>
      scope === "applications" ? api.applications() : channelId === null ? api.jobs(scope === "archived") : api.channelJobs(channelId),
    refetchInterval: 60_000,
  });
}

export function useSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SearchRequest) => api.search(body),
    onSuccess: (data) => {
      // Feed the result straight into the "all jobs" cache.
      qc.setQueryData(["jobs", null], data);
    },
  });
}

export function useCreateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ChannelRequest) => api.createChannel(body),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["logs"] });
    },
  });
}

export function useDeleteChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteChannel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
      qc.invalidateQueries({ queryKey: ["logs"] });
    },
  });
}

export function useRefreshChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.refreshChannel(id),
    // Settled, not success: a failed refresh is logged too.
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["logs"] });
    },
  });
}

interface FeedbackVars {
  jobUrl: string;
  verdict: Verdict | null;
  meta?: { title?: string; company?: string; site?: string };
}

export function useFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: FeedbackVars) => api.feedback(v.jobUrl, v.verdict, v.meta),
    // Optimistically patch every cached jobs list so the ♥ fills / a dismissed
    // card disappears instantly, without waiting for a refetch.
    onMutate: async (v: FeedbackVars) => {
      await qc.cancelQueries({ queryKey: ["jobs"] });
      const snapshot = qc.getQueriesData<JobsResponse>({ queryKey: ["jobs"] });
      qc.setQueriesData<JobsResponse>({ queryKey: ["jobs"] }, (old) => {
        if (!old) return old;
        const feedback = { ...old.feedback };
        if (v.verdict) feedback[v.jobUrl] = { verdict: v.verdict };
        else delete feedback[v.jobUrl];
        return { ...old, feedback };
      });
      return { snapshot };
    },
    onError: (err, _v, ctx) => {
      toast.error(`Salvataggio non riuscito: ${err.message}`);
      ctx?.snapshot?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["job"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["channels"] });
    },
  });
}
