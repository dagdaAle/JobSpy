import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import type { Analysis, Job } from "../api/types";
import { JobCard, type CardMode } from "./JobCard";

interface Props {
  jobs: Job[];
  analysis: Record<string, Analysis>;
  mode: CardMode;
  loading?: boolean;
  empty: ReactNode;
  onOpen: (job: Job) => void;
  onLike: (job: Job) => void;
  onDismiss: (job: Job) => void;
  onRestore: (job: Job) => void;
}

const GRID = "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3";

export function JobGrid({ jobs, analysis, mode, loading, empty, onOpen, onLike, onDismiss, onRestore }: Props) {
  if (loading) {
    return (
      <div className={GRID}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-60 rounded-xl" />
        ))}
      </div>
    );
  }

  if (jobs.length === 0) return <>{empty}</>;

  return (
    <div className={GRID}>
      {jobs.map((job) => (
        <JobCard
          key={job.job_url}
          job={job}
          analysis={analysis[job.job_url]}
          mode={mode}
          onOpen={() => onOpen(job)}
          onLike={() => onLike(job)}
          onDismiss={() => onDismiss(job)}
          onRestore={() => onRestore(job)}
        />
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-20 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-5">
        {icon}
      </div>
      <h2 className="font-medium">{title}</h2>
      {children && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{children}</p>}
    </div>
  );
}
