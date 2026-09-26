import { useState } from "react";
import { Heart, MapPin, Undo2, Wallet, Wifi, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { Analysis, Job } from "../api/types";
import { daysLeftInFeed, initial, salaryLabel, scoreColor, siteDot, siteLabel, timeAgo } from "../lib/format";

export type CardMode = "feed" | "saved" | "dismissed";

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

export function JobCard({ job, analysis, mode, feedDays, onOpen, onLike, onDismiss, onRestore }: Props) {
  const score = analysis?.relevance_score ?? null;
  const salary = salaryLabel(job);
  const tags = analysis?.tags ?? [];
  const locations = job.location?.split(" · ") ?? [];
  const daysLeft = mode === "feed" ? daysLeftInFeed(job.first_seen_at, feedDays) : null;

  return (
    <article
      onClick={onOpen}
      className="group flex h-full cursor-pointer flex-col rounded-xl border bg-card text-card-foreground shadow-xs transition-[border-color,box-shadow] hover:border-foreground/15 hover:shadow-md"
    >
      <div className="flex flex-1 flex-col gap-4 p-5">
        <header className="flex items-start gap-3">
          <CompanyAvatar name={job.company} logo={job.company_logo} />
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 font-medium leading-snug text-foreground group-hover:text-primary">
              {job.title}
            </h3>
            <p className="mt-0.5 truncate text-sm text-muted-foreground">{job.company}</p>
          </div>
          {job.is_new && (
            <Badge className="bg-primary/12 text-primary dark:bg-primary/15">Nuovo</Badge>
          )}
        </header>

        <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-muted-foreground">
          {job.is_remote ? (
            <Meta icon={<Wifi />}>Remoto</Meta>
          ) : (
            locations[0] && (
              <Meta icon={<MapPin />}>
                {locations[0]}
                {locations.length > 1 && ` +${locations.length - 1}`}
              </Meta>
            )
          )}
          {salary && <Meta icon={<Wallet />}>{salary}</Meta>}
        </div>

        <div className="mt-auto space-y-3">
          {score != null && <ScoreBar score={score} />}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.slice(0, 4).map((t) => (
                <Badge key={t} variant="secondary" className="font-normal">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>

      <footer className="flex items-center gap-2 border-t px-5 py-2.5 text-xs text-muted-foreground">
        <span className={cn("size-1.5 rounded-full", siteDot(job.site))} />
        <span>{siteLabel(job.site)}</span>
        <span aria-hidden>·</span>
        <span>{timeAgo(job.date_posted)}</span>
        {daysLeft !== null && daysLeft <= 2 && (
          <Tooltip>
            <TooltipTrigger render={<span className="text-score-mid" />}>
              · {daysLeft <= 0 ? "esce oggi" : daysLeft === 1 ? "esce domani" : `esce tra ${daysLeft} g`}
            </TooltipTrigger>
            <TooltipContent>
              Senza like né scarto esce dal feed {feedDays} giorni dopo essere comparsa. Resta nel database.
            </TooltipContent>
          </Tooltip>
        )}
        <div className="ml-auto flex gap-1" onClick={(e) => e.stopPropagation()}>
          {mode === "feed" && (
            <>
              <CardAction label="Scarta" onClick={onDismiss} className="hover:text-destructive">
                <X />
              </CardAction>
              <CardAction label="Aggiungi ai preferiti" onClick={onLike} className="hover:text-rose-500">
                <Heart />
              </CardAction>
            </>
          )}
          {mode === "saved" && (
            <CardAction label="Togli dai preferiti" onClick={onRestore} className="text-rose-500">
              <Heart className="fill-current" />
            </CardAction>
          )}
          {mode === "dismissed" && (
            <CardAction label="Rimetti tra le offerte" onClick={onRestore}>
              <Undo2 />
            </CardAction>
          )}
        </div>
      </footer>
    </article>
  );
}

function Meta({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 [&_svg]:size-3.5 [&_svg]:shrink-0">
      {icon}
      <span className="truncate">{children}</span>
    </span>
  );
}

export function ScoreBar({ score }: { score: number }) {
  const c = scoreColor(score);
  return (
    <div className="flex items-center gap-3">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", c.bar)} style={{ width: `${score}%` }} />
      </div>
      <span className={cn("text-xs font-medium tabular-nums", c.text)}>{score}% match</span>
    </div>
  );
}

function CardAction({
  label,
  onClick,
  className,
  children,
}: {
  label: string;
  onClick: () => void;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={label}
            onClick={onClick}
            className={cn("text-muted-foreground", className)}
          />
        }
      >
        {children}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export function CompanyAvatar({
  name,
  logo,
  className,
}: {
  name: string | null;
  logo?: string | null;
  className?: string;
}) {
  const [broken, setBroken] = useState(false);
  const base = cn(
    "flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-lg border bg-muted text-sm font-semibold text-muted-foreground",
    className,
  );
  if (logo && !broken) {
    return (
      <div className={cn(base, "bg-white")}>
        <img src={logo} alt="" className="size-full object-contain" onError={() => setBroken(true)} />
      </div>
    );
  }
  return <div className={base}>{initial(name)}</div>;
}
