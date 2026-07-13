import type { Job } from "../api/types";

/** Human "N ORE FA" style relative time from an ISO/date string. */
export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return String(dateStr).toUpperCase();
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "ADESSO";
  if (mins < 60) return `${mins} MIN FA`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} ${hrs === 1 ? "ORA" : "ORE"} FA`;
  const days = Math.floor(hrs / 24);
  return `${days} ${days === 1 ? "GIORNO" : "GIORNI"} FA`;
}

/** Compact salary label, e.g. "120K - 150K" or "€120K". */
export function salaryLabel(job: Job): string | null {
  const { salary_min, salary_max, salary_currency } = job;
  if (!salary_min && !salary_max) return null;
  const sym =
    salary_currency === "USD" ? "$" : salary_currency === "GBP" ? "£" : "€";
  const k = (n: number) =>
    n >= 1000 ? `${Math.round(n / 1000)}K` : String(Math.round(n));
  if (salary_min && salary_max) return `${sym}${k(salary_min)} - ${k(salary_max)}`;
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

/** Tailwind class picking a colour for the AI relevance score bar/text. */
export function scoreColor(score: number): { text: string; bar: string } {
  if (score >= 80)
    return { text: "text-secondary-fixed", bar: "bg-secondary-fixed" };
  if (score >= 50)
    return { text: "text-primary-fixed", bar: "bg-primary-fixed" };
  return { text: "text-error", bar: "bg-error" };
}

/** Per-site badge palette so each source is instantly recognisable. */
export function siteBadge(site: string): string {
  const s = site.toLowerCase();
  if (s.includes("linkedin")) return "bg-secondary-fixed text-on-secondary-fixed";
  if (s.includes("indeed")) return "bg-primary-fixed text-on-primary-fixed";
  if (s.includes("glassdoor")) return "bg-secondary-container text-on-secondary-container";
  return "bg-accent-pink text-white";
}

/** First letter for the square company avatar. */
export function initial(name: string | null | undefined): string {
  return (name ?? "?").trim().charAt(0).toUpperCase() || "?";
}
