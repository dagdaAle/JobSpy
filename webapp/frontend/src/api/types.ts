// Types mirroring the FastAPI backend payloads (see webapp/app.py).

export type Site = string;
export type Verdict = "like" | "dislike";
export type SearchMode = "italy" | "remote";

export interface Job {
  site: Site;
  title: string;
  company: string | null;
  location: string | null;
  is_remote: boolean | null;
  job_type: string | null;
  date_posted: string | null;
  job_url: string;
  is_new?: boolean;
  // Copies of the same offer (same title+company) collapsed into this card.
  duplicates?: number;
  duplicate_urls?: string[];
  // Rich fields (present on stored/channel jobs).
  job_url_direct?: string | null;
  company_url?: string | null;
  company_industry?: string | null;
  company_logo?: string | null;
  banner_photo_url?: string | null;
  job_level?: string | null;
  job_function?: string | null;
  emails?: string | null;
  skills?: string | null;
  description?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_interval?: string | null;
}

export interface Analysis {
  relevance_score?: number | null;
  tags?: string[];
  summary?: string;
  reasons?: string[];
}

export interface Feedback {
  verdict?: Verdict | null;
}

export interface Channel {
  id: number;
  site: Site;
  search_term: string;
  name: string;
  location: string;
  distance_km: number;
  results_wanted: number;
  hours_old: number | null;
  is_remote: boolean;
  created_at?: string;
  // Counts only jobs still to review (no like/dislike yet).
  total_count?: number;
  new_count?: number;
  last_refresh_at?: string | null;
  last_refresh_status?: "ok" | "error" | null;
}

export interface SearchRequest {
  mode: SearchMode;
  search_term: string;
  location?: string;
  distance_km?: number;
  results_wanted?: number;
  hours_old?: number | null;
  sites?: string[] | null;
  include_linkedin?: boolean;
}

export interface ChannelRequest {
  site: string;
  search_term: string;
  name?: string;
  location?: string;
  distance_km?: number;
  results_wanted?: number;
  hours_old?: number | null;
  is_remote?: boolean;
}

// Envelope shared by /search, /jobs and /channels/{id}/jobs.
export interface JobsResponse {
  jobs: Job[];
  analysis: Record<string, Analysis>;
  feedback: Record<string, Feedback>;
  count?: number;
  analyzer_configured?: boolean;
}

export interface ChannelsResponse {
  channels: Channel[];
  sites: string[];
}

export interface StatusResponse {
  analyzer_configured: boolean;
  cv_loaded: boolean;
  cv_chars: number;
  max_analysis_per_search: number;
}

export interface JobDetailResponse {
  job: Job;
  analysis: Analysis | null;
  feedback: Feedback | null;
}

export interface Count {
  name: string;
  count: number;
}

export interface AnalyticsResponse {
  kpis: {
    total: number;
    new_7d: number;
    remote_pct: number;
    avg_score: number | null;
    analyzed: number;
    favorites: number;
    dismissed: number;
    channels: number;
  };
  salary: {
    count: number;
    min?: number;
    max?: number;
    median?: number;
    currency?: string;
    buckets?: { range: string; count: number }[];
  };
  top_skills: Count[];
  top_companies: Count[];
  top_industries: Count[];
  remote_by_site: { site: string; remote: number; onsite: number }[];
}

// One update event from /logs. Timestamps are UTC "YYYY-MM-DD HH:MM:SS".
export interface LogEntry {
  id: number;
  started_at: string;
  finished_at: string;
  kind: "refresh" | "purge";
  trigger: "scheduler" | "manual" | "create";
  channel_id: number | null;
  channel_name: string | null;
  site: string | null;
  status: "ok" | "error";
  found: number;
  new_count: number;
  analyzed: number;
  analysis_failed: number;
  removed: number;
  duration_ms: number;
  error: string | null;
}

export interface LogsResponse {
  logs: LogEntry[];
}
