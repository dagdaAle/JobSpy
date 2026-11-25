import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { areaApi, type AreaChannelRequest, type AreaItem, type AreaKey, type AreaProfile, type AreaView } from "../api/areas";
import type { Verdict } from "../api/types";

// Query keys start with the area, so PA and Gare caches never mix with each other or with Lavoro.

export function useAreaChannels(area: AreaKey) {
  return useQuery({ queryKey: [area, "channels"], queryFn: areaApi(area).channels });
}

export function useAreaItems(area: AreaKey, view: AreaView, channelId: number | null, enabled = true) {
  return useQuery({
    queryKey: [area, "items", view, channelId],
    queryFn: () => areaApi(area).items(view, channelId),
    enabled,
    refetchInterval: 60_000,
  });
}

export function useAreaMeta(area: AreaKey) {
  return useQuery({ queryKey: [area, "meta"], queryFn: areaApi(area).meta, staleTime: Infinity });
}

export function useAreaProfile(area: AreaKey) {
  return useQuery({ queryKey: [area, "profile"], queryFn: areaApi(area).profile });
}

export function useSaveAreaProfile(area: AreaKey) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AreaProfile) => areaApi(area).saveProfile(body),
    // The decision is recomputed from the profile, so the lists change too.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [area, "profile"] });
      qc.invalidateQueries({ queryKey: [area, "items"] });
    },
  });
}

export function useCreateAreaChannel(area: AreaKey) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AreaChannelRequest) => areaApi(area).createChannel(body),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: [area, "channels"] });
      qc.invalidateQueries({ queryKey: [area, "items"] });
      qc.invalidateQueries({ queryKey: ["logs"] });
    },
  });
}

export function useDeleteAreaChannel(area: AreaKey) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => areaApi(area).deleteChannel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [area, "channels"] });
      qc.invalidateQueries({ queryKey: [area, "items"] });
      qc.invalidateQueries({ queryKey: ["logs"] });
    },
  });
}

export function useRefreshAreaChannel(area: AreaKey) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => areaApi(area).refreshChannel(id),
    // Settled, not success: a failed refresh is logged too.
    onSettled: () => {
      qc.invalidateQueries({ queryKey: [area, "channels"] });
      qc.invalidateQueries({ queryKey: [area, "items"] });
      qc.invalidateQueries({ queryKey: ["logs"] });
    },
  });
}

type ItemsData = { items: AreaItem[] };

export function useAreaVerdict(area: AreaKey) {
  const qc = useQueryClient();
  const key = [area, "items"];
  return useMutation({
    mutationFn: (v: { key: string; verdict: Verdict | null }) => areaApi(area).verdict(v.key, v.verdict),
    // Patch every cached list so the card moves out of its view at once.
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: key });
      const snapshot = qc.getQueriesData<ItemsData>({ queryKey: key });
      qc.setQueriesData<ItemsData>({ queryKey: key }, (old) =>
        old && { items: old.items.map((it) => (it.key === v.key ? { ...it, verdict: v.verdict } : it)) },
      );
      return { snapshot };
    },
    onError: (err, _v, ctx) => {
      toast.error(`Salvataggio non riuscito: ${err.message}`);
      ctx?.snapshot?.forEach(([k, data]) => qc.setQueryData(k, data));
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}
