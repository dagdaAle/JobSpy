import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import type { Analysis, Job } from "../api/types";
import { jobDecision, type DecisionKey } from "./decision";
import { CARD_GRID, FeedSection } from "./FeedSection";
import { JobCard, type CardMode } from "./JobCard";

interface Props {
  jobs: Job[];
  analysis: Record<string, Analysis>;
  mode: CardMode;
  feedDays: number;
  loading?: boolean;
  empty: ReactNode;
  // Feed: one section per decision, in this order. Other views: a single grid.
  sections?: { key: DecisionKey; title: string }[];
  onOpen: (job: Job) => void;
  onLike: (job: Job) => void;
  onDismiss: (job: Job) => void;
  onRestore: (job: Job) => void;
}

export function JobGrid({ jobs, analysis, mode, feedDays, loading, empty, sections, onOpen, onLike, onDismiss, onRestore }: Props) {
  if (loading) return <CardSkeletons />;
  if (jobs.length === 0) return <>{empty}</>;

  const card = (job: Job) => (
    <JobCard
      key={job.job_url}
      job={job}
      analysis={analysis[job.job_url]}
      mode={mode}
      feedDays={feedDays}
      onOpen={() => onOpen(job)}
      onLike={() => onLike(job)}
      onDismiss={() => onDismiss(job)}
      onRestore={() => onRestore(job)}
    />
  );

  if (!sections) return <div className={CARD_GRID}>{jobs.map(card)}</div>;

  return (
    <div className="space-y-10">
      {sections.map((s) => {
        const list = jobs.filter((j) => jobDecision(analysis[j.job_url]) === s.key);
        return list.length > 0 && <FeedSection key={s.key} title={s.title} count={list.length}>{list.map(card)}</FeedSection>;
      })}
    </div>
  );
}

export function CardSkeletons() {
  return (
    <div className={CARD_GRID} aria-busy>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="rounded-xl border bg-card p-1.5">
          <div className="space-y-3 rounded-[14px] bg-muted p-4">
            <Skeleton className="h-6 w-32 rounded-full bg-border" />
            <Skeleton className="h-5 w-24 rounded-full bg-border" />
            <Skeleton className="h-4 w-3/4 bg-border" />
            <Skeleton className="h-5 w-2/3 bg-border" />
            <Skeleton className="h-3 w-5/6 bg-border" />
          </div>
          <div className="flex items-center justify-between px-3 pt-3 pb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-9 w-20 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ icon, title, children, action }: { icon: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-input bg-card px-6 py-16 text-center">
      <div className="mb-4 flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-6">
        {icon}
      </div>
      <h2 className="font-heading text-lg font-semibold">{title}</h2>
      {children && <p className="mt-1 max-w-sm text-sm leading-relaxed text-muted-foreground">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
