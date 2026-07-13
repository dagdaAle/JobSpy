import { Icon } from "./Icon";
import { JobCard } from "./JobCard";
import type { Analysis, Feedback, Job } from "../api/types";

interface Props {
  jobs: Job[];
  analysis: Record<string, Analysis>;
  feedback: Record<string, Feedback>;
  loading?: boolean;
  onOpen: (job: Job) => void;
  onLike: (job: Job) => void;
  onDismiss: (job: Job) => void;
}

export function JobGrid({
  jobs,
  analysis,
  feedback,
  loading,
  onOpen,
  onLike,
  onDismiss,
}: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-72 bg-surface-container border-thick border-black neo-shadow animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center border-thick border-dashed border-outline-variant">
        <Icon
          name="search_off"
          className="text-outline-variant mb-4"
        />
        <h2 className="text-headline-lg uppercase text-outline-variant">
          Nessun risultato trovato
        </h2>
        <p className="text-body-md text-on-surface-variant mt-2">
          Avvia una ricerca o aggiungi un nuovo canale per popolare la griglia.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      {jobs.map((job) => (
        <JobCard
          key={job.job_url}
          job={job}
          analysis={analysis[job.job_url]}
          feedback={feedback[job.job_url]}
          onOpen={() => onOpen(job)}
          onLike={() => onLike(job)}
          onDismiss={() => onDismiss(job)}
        />
      ))}
    </div>
  );
}
