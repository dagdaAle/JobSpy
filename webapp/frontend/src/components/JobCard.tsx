import { Clock } from "lucide-react";
import type { Analysis, Job } from "../api/types";
import { daysLeftInFeed, salaryLabel, siteLabel, timeAgo } from "../lib/format";
import { CardNumber, DecisionCard, type CardState } from "./DecisionCard";
import { InfoChip, jobDecision, Tag } from "./decision";

export type CardMode = "feed" | "saved" | "dismissed" | "archived" | "applications";

interface Props {
  job: Job;
  analysis?: Analysis;
  mode: CardMode;
  feedDays: number;
  onOpen: () => void;
  onLike: () => void;
  onDismiss: () => void;
  onRestore: () => void;
}

const STATE: Record<CardMode, CardState> = { feed: "open", applications: "open", saved: "saved", dismissed: "dismissed", archived: "archived" };

/** One line of "why": the blocker first, then the AI summary. */
export function jobReason(analysis?: Analysis): string | null {
  const a = analysis?.assessment;
  if (a?.blockers?.length) return `Bloccante: ${a.blockers[0]}`;
  if (analysis?.summary) return analysis.summary;
  if (analysis?.reasons?.length) return analysis.reasons[0];
  if (!analysis) return "Analisi AI non ancora fatta: leggi l’annuncio e decidi tu.";
  return null;
}

export function workModeLabel(job: Job, analysis?: Analysis | null): string | null {
  const m = analysis?.assessment?.work_mode;
  if (job.is_remote || m === "remote") return "remoto";
  if (m === "hybrid") return "ibrido";
  if (m === "onsite") return "in sede";
  return null;
}

export function JobCard({ job, analysis, mode, feedDays, onOpen, onLike, onDismiss, onRestore }: Props) {
  const decision = jobDecision(analysis);
  const sources = [siteLabel(job.site), (job.duplicates ?? 1) > 1 ? `+${(job.duplicates ?? 1) - 1}` : null].filter(Boolean).join(" ");
  const age = timeAgo(job.date_posted);
  const left = mode === "feed" ? daysLeftInFeed(job.feed_since ?? job.first_seen_at, feedDays) : null;
  const where = [job.location?.split(" · ")[0], workModeLabel(job, analysis)].filter(Boolean).join(" · ");
  const salary = salaryLabel(job);

  return (
    <DecisionCard
      decision={decision}
      badgeLabel={decision === "nonnoto" ? (analysis ? "Non noto · dati insufficienti" : "Non noto · da analizzare") : undefined}
      top={
        <>
          <InfoChip icon={<Clock />}>{[age, sources].filter(Boolean).join(" · ")}</InfoChip>
          {job.is_new && <InfoChip>Nuova</InfoChip>}
          {left !== null && left <= 2 && <InfoChip>{left <= 0 ? "esce oggi" : left === 1 ? "esce domani" : `esce tra ${left} g`}</InfoChip>}
          {job.source_closed_at && <span className="rounded-full bg-destructive-soft px-2.5 py-1 text-xs font-semibold text-destructive">Chiusa alla fonte</span>}
        </>
      }
      org={job.company}
      title={job.title}
      reason={jobReason(analysis)}
      tags={(analysis?.tags ?? []).slice(0, 4).map((t) => <Tag key={t}>{t}</Tag>)}
      number={<CardNumber value={salary ?? analysis?.assessment?.salary ?? null} unit={salary ? "RAL" : undefined} unknown="RAL non indicata" />}
      place={where || "Sede non indicata"}
      state={STATE[mode]}
      onOpen={onOpen}
      onSave={onLike}
      onDismiss={onDismiss}
      onRestore={onRestore}
    />
  );
}
