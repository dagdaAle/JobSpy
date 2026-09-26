import type { Job } from "../api/types";

const DAY = 86_400_000;

/** Parse a backend timestamp. Bare "YYYY-MM-DD HH:MM:SS" values are UTC (SQLite). */
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const iso = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
    ? `${value.replace(" ", "T")}Z`
    : value;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "oggi", "ieri", "3 giorni fa"; minutes/hours only when the value has a time. */
export function timeAgo(value: string | null | undefined): string {
  if (!value) return "";
  const d = parseDate(value);
  if (!d) return value;
  // date_posted is a bare date: compare calendar days, not hours.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const [y, m, day] = value.split("-").map(Number);
    const days = Math.round((today.getTime() - new Date(y, m - 1, day).getTime()) / DAY);
    if (days <= 0) return "oggi";
    if (days === 1) return "ieri";
    return `${days} giorni fa`;
  }
  const mins = Math.floor((Date.now() - d.getTime()) / 60_000);
  if (mins < 1) return "adesso";
  if (mins < 60) return `${mins} min fa`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} ${hrs === 1 ? "ora" : "ore"} fa`;
  const days = Math.floor(hrs / 24);
  return days === 1 ? "ieri" : `${days} giorni fa`;
}

/** Whole days before a job without a verdict leaves the feed (can be <= 0). */
export function daysLeftInFeed(firstSeen: string | null | undefined, feedDays: number): number | null {
  const d = parseDate(firstSeen);
  if (!d) return null;
  return Math.ceil((d.getTime() + feedDays * DAY - Date.now()) / DAY);
}

/** Local "26 set, 09:00". */
export function formatDateTime(value: string | null | undefined): string {
  const d = parseDate(value);
  if (!d) return value ?? "";
  return d.toLocaleString("it-IT", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "12,4 s" / "850 ms". */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toLocaleString("it-IT", { maximumFractionDigits: 1 })} s`;
  return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
}

/** Compact salary label, e.g. "€40–48k". */
export function salaryLabel(job: Job): string | null {
  const { salary_min, salary_max, salary_currency } = job;
  if (!salary_min && !salary_max) return null;
  const sym = salary_currency === "USD" ? "$" : salary_currency === "GBP" ? "£" : "€";
  const k = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(Math.round(n)));
  if (salary_min && salary_max && salary_min !== salary_max)
    return `${sym}${k(salary_min).replace("k", "")}–${k(salary_max)}`;
  return `${sym}${k((salary_min ?? salary_max) as number)}`;
}

/** Parse the comma/JSON-ish skills string into a tidy list. */
export function parseSkills(skills: string | null | undefined): string[] {
  if (!skills) return [];
  const raw = String(skills).trim();
  try {
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) return arr.map(String);
  } catch {
    /* not JSON */
  }
  return raw
    .split(/[,;]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Tailwind classes for the AI relevance score (text + bar fill). */
export function scoreColor(score: number): { text: string; bar: string } {
  if (score >= 75) return { text: "text-score-high", bar: "bg-score-high" };
  if (score >= 50) return { text: "text-score-mid", bar: "bg-score-mid" };
  return { text: "text-score-low", bar: "bg-score-low" };
}

const SITE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  google: "Google",
  remotive: "Remotive",
  remoteok: "RemoteOK",
  weworkremotely: "We Work Remotely",
  workingnomads: "Working Nomads",
};

export function siteLabel(site: string | null | undefined): string {
  if (!site) return "";
  return SITE_LABELS[site.toLowerCase()] ?? site.charAt(0).toUpperCase() + site.slice(1);
}

/** Small per-site colour dot so each source is recognisable at a glance. */
export function siteDot(site: string | null | undefined): string {
  const s = (site ?? "").toLowerCase();
  if (s.includes("linkedin")) return "bg-sky-500";
  if (s.includes("indeed")) return "bg-indigo-500";
  if (s.includes("glassdoor")) return "bg-emerald-500";
  return "bg-violet-500";
}

/** First letter for the company avatar. */
export function initial(name: string | null | undefined): string {
  return (name ?? "?").trim().charAt(0).toUpperCase() || "?";
}
