import { Icon } from "./Icon";
import type { Analysis, Feedback, Job } from "../api/types";
import {
  initial,
  salaryLabel,
  scoreColor,
  siteBadge,
  timeAgo,
} from "../lib/format";

interface Props {
  job: Job;
  analysis?: Analysis;
  feedback?: Feedback;
  onOpen: () => void;
  onLike: () => void;
  onDismiss: () => void;
}

export function JobCard({ job, analysis, feedback, onOpen, onLike, onDismiss }: Props) {
  const score = analysis?.relevance_score ?? null;
  const salary = salaryLabel(job);
  const liked = feedback?.verdict === "like";
  const tags = analysis?.tags ?? [];

  return (
    <div
      onClick={onOpen}
      className="bg-surface-container border-thick border-black neo-shadow hover:neo-shadow-lg hover:-translate-y-1 transition-all group flex flex-col h-full cursor-pointer"
    >
      <div className="p-6 flex flex-col h-full">
        <div className="flex justify-between items-start mb-4">
          <div className="w-12 h-12 bg-primary-fixed-dim border-thin border-black flex items-center justify-center text-headline-md text-black font-black shrink-0">
            {initial(job.company)}
          </div>
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-1">
              {job.is_new && (
                <span className="px-2 py-0.5 text-[10px] font-black uppercase border-thin border-black bg-secondary-fixed text-on-secondary-fixed">
                  NEW
                </span>
              )}
              <span
                className={`px-2 py-0.5 text-[10px] font-black uppercase border-thin border-black ${siteBadge(
                  job.site,
                )}`}
              >
                {job.site}
              </span>
            </div>
            <span className="text-outline text-meta-xs">{timeAgo(job.date_posted)}</span>
          </div>
        </div>

        <h3 className="text-headline-md uppercase leading-tight group-hover:text-primary-fixed transition-colors mb-1 line-clamp-2">
          {job.title}
        </h3>
        <p className="text-meta-sm text-on-surface-variant uppercase mb-4 line-clamp-1">
          {job.company}
        </p>

        <div className="flex flex-wrap gap-2 mb-6">
          {job.location && (
            <span className="bg-surface-container-highest border-thin border-black px-2 py-1 text-[10px] font-black uppercase text-outline">
              {job.location}
            </span>
          )}
          {job.is_remote && (
            <span className="bg-primary-container/20 text-primary-fixed border-thin border-primary-fixed px-2 py-1 text-[10px] font-black uppercase">
              Remote
            </span>
          )}
          {salary && (
            <span className="bg-surface-container-highest border-thin border-black px-2 py-1 text-[10px] font-black uppercase text-outline">
              {salary}
            </span>
          )}
        </div>

        <div className="mt-auto space-y-4">
          {score != null && (
            <div className="bg-black/40 p-3 border-thin border-black">
              <div className="flex justify-between items-center mb-1">
                <span className="text-meta-xs uppercase text-outline">AI Relevance Score</span>
                <span className={`text-meta-sm font-black ${scoreColor(score).text}`}>
                  {score}%
                </span>
              </div>
              <div className="w-full h-2 bg-surface-container-lowest border-thin border-black">
                <div
                  className={`h-full ${scoreColor(score).bar}`}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          )}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {tags.slice(0, 4).map((t) => (
                <span
                  key={t}
                  className="text-[9px] font-black px-1.5 py-0.5 bg-tertiary-container text-on-tertiary-container uppercase"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex border-t-thick border-black">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onLike();
          }}
          className={`flex-1 py-3 flex items-center justify-center transition-colors border-r-thick border-black hover:bg-primary-container hover:text-on-primary-fixed ${
            liked ? "bg-primary-container text-on-primary-fixed" : ""
          }`}
        >
          <Icon name="favorite" filled={liked} />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          className="flex-1 py-3 flex items-center justify-center hover:bg-error-container hover:text-on-error transition-colors"
        >
          <Icon name="close" />
        </button>
      </div>
    </div>
  );
}
