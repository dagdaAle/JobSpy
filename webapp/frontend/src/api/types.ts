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
  // UTC "YYYY-MM-DD HH:MM:SS": when we first scraped it (drives the feed expiry).
  first_seen_at?: string | null;
  feed_since?: string | null;
  archived_at?: string | null;
  // Copies with matching content, location and work mode.
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
  assessment?: {
    work_mode: "remote" | "hybrid" | "onsite" | "unknown";
    location_fit: "compatible" | "incompatible" | "unknown";
    location_reason: string;
    confidence: "high" | "medium" | "low";
    missing_requirements: string[];
  };
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
  applications?: Record<string, Application>;
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
  // Jobs in the DB still waiting for an AI analysis.
  analysis_pending: number;
  analysis_running: boolean;
  // Days a job without a verdict stays in the feed before being archived.
  feed_days: number;
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
  // Whole-database totals (archived jobs and full history included).
  database: {
    since: string | null;
    jobs: number;
    in_feed: number;
    archived: number;
    analyzed: number;
    analysis_runs: number;
    analysis_errors: number;
    tokens: number;
    sightings: number;
    versions: number;
    feedback_events: number;
    cv_versions: number;
  };
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
  kind: "refresh" | "analysis" | "archive" | "purge";
  trigger: "scheduler" | "manual" | "create" | "startup";
  channel_id: number | null;
  channel_name: string | null;
  site: string | null;
  status: "running" | "ok" | "error";
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

export type ApplicationStatus = "to_apply" | "applied" | "contacted" | "interview" | "rejected" | "offer" | "withdrawn";
export interface Application {
  cv_label: string;
  contact: string;
  updated_at?: string;
  job_url: string;
  status: ApplicationStatus;
  applied_on: string | null;
  notes: string;
  next_step: string;
  follow_up_on: string | null;
}

export interface ManualApplication extends Application {
  title: string; company: string; url: string | null; location: string;
}
export interface ApplicationEvent {
  id: number; kind: "created" | "updated" | "imported" | "note";
  occurred_on: string; created_at: string;
  content: Record<string, unknown>;
}
