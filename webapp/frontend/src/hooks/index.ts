import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  ChannelRequest,
  JobsResponse,
  SearchRequest,
  Verdict,
} from "../api/types";

export function useStatus() {
  return useQuery({ queryKey: ["status"], queryFn: api.status });
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

// The active job list. `channelId === null` means "all stored jobs" (/jobs);
// a number scopes to one channel's jobs.
export function useJobs(channelId: number | null) {
  return useQuery({
    queryKey: ["jobs", channelId],
    queryFn: () =>
      channelId === null ? api.jobs() : api.channelJobs(channelId),
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDeleteChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteChannel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["channels"] }),
  });
}

export function useRefreshChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.refreshChannel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
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
    onError: (_err, _v, ctx) => {
      ctx?.snapshot?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    // Deliberately no jobs refetch here: the optimistic cache already matches
    // the server, and an immediate refetch was reverting the UI. Analytics
    // (favourites count) refreshes on its own next load.
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics"] }),
  });
}
