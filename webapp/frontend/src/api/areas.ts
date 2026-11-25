// Client for the Concorsi PA and Gare P.IVA areas. Both expose the same API
// under their own prefix (/pa, /gare), so one client serves both.
import { req } from "./client";
import type { Verdict } from "./types";

export type AreaKey = "pa" | "gare";
export type AreaView = "feed" | "saved" | "dismissed" | "archived";
export type AreaDecision = "adatto" | "da_valutare" | "non_adatto";

// Columns unused by an area stay null (PA: source/query/location; Gare: query/cpv/country/days/max_amount).
export interface AreaChannel {
  id: number;
  name: string | null;
  source: string | null;
  query: string | null;
  location: string | null;
  cpv: string | null; // comma separated CPV codes
  country: string | null;
  days: number | null;
  max_amount: number | null;
  results_wanted: number | null;
  created_at: string;
  last_refresh_at: string | null;
  last_refresh_status: string | null;
}

export type AreaChannelRequest = Partial<Omit<AreaChannel, "id" | "created_at" | "last_refresh_at" | "last_refresh_status">>;

export interface AreaItem {
  key: string;
  source: string;
  title: string;
  body: string | null;
  buyer: string | null;
  kind: string | null;
  place: string | null;
  deadline: string | null; // ISO date
  published_at: string | null;
  url: string | null;
  amount: number | null;
  currency: string | null;
  cpv: string | null;
  first_seen_at: string;
  last_seen_at: string;
  archived_at: string | null;
  verdict: Verdict | null;
  facts: Record<string, unknown> | null;
  decision: AreaDecision | null;
  reasons: string[];
  channel_ids: number[];
}

export interface AreaMeta {
  sources: string[];
  vocabulary?: string[];
}

export interface PaProfile {
  titoli: string[];
  livello_max: "diploma" | "triennale" | "magistrale" | "dottorato";
  aree: string[];
  sedi: string[];
  eta: number | null;
}

export interface GareProfile {
  servizi: string[];
  fatturato_annuo: number | null;
  certificazioni: string[];
  solo_subappalto_ok: boolean;
}

export type AreaProfile = Record<string, unknown>;

export const areaApi = (area: AreaKey) => ({
  channels: () => req<{ channels: AreaChannel[] }>(`/${area}/channels`),
  createChannel: (body: AreaChannelRequest) =>
    req<{ channel: AreaChannel; new_count: number }>(`/${area}/channels`, { method: "POST", body: JSON.stringify(body) }),
  deleteChannel: (id: number) => req<{ ok: boolean }>(`/${area}/channels/${id}`, { method: "DELETE" }),
  refreshChannel: (id: number) => req<{ new_count: number }>(`/${area}/channels/${id}/refresh`, { method: "POST" }),
  items: (view: AreaView, channelId: number | null) =>
    req<{ items: AreaItem[] }>(`/${area}/items?${new URLSearchParams({
      view, ...(channelId !== null ? { channel_id: String(channelId) } : {}),
    })}`),
  verdict: (key: string, verdict: Verdict | null) =>
    req<{ ok: boolean }>(`/${area}/verdict`, { method: "POST", body: JSON.stringify({ key, verdict }) }),
  profile: () => req<AreaProfile>(`/${area}/profile`),
  saveProfile: (body: AreaProfile) => req<AreaProfile>(`/${area}/profile`, { method: "PUT", body: JSON.stringify(body) }),
  meta: () => req<AreaMeta>(`/${area}/meta`),
});
