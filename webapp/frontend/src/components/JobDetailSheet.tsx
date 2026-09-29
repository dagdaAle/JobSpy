import { ApplicationEditor } from "./ApplicationEditor";
import { ExternalLink, Heart, Sparkles, Undo2, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { Analysis, Job } from "../api/types";
import { useJobDetail } from "../hooks";
import { parseSkills, salaryLabel, scoreColor, siteDot, siteLabel, timeAgo } from "../lib/format";
import { CompanyAvatar, type CardMode } from "./JobCard";

interface Props {
  job: Job | null;
  analysis?: Analysis;
  mode: CardMode;
  onClose: () => void;
  onLike: (job: Job) => void;
  onDismiss: (job: Job) => void;
  onRestore: (job: Job) => void;
}

export function JobDetailSheet({ job, analysis, mode, onClose, onLike, onDismiss, onRestore }: Props) {
  const detail = useJobDetail(job?.job_url ?? null);

  return (
    <Sheet open={job !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 p-0 sm:max-w-xl">
        {job && (
          <Body
            job={{ ...job, ...(detail.data?.job ?? {}), location: job.location }}
            analysis={detail.data?.analysis ?? analysis}
            loading={detail.isLoading}
            mode={mode}
            act={(fn) => {
              fn(job);
              onClose();
            }}
            onLike={onLike}
            onDismiss={onDismiss}
            onRestore={onRestore}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

function Body({
  job,
  analysis,
  loading,
  mode,
  act,
  onLike,
  onDismiss,
  onRestore,
}: {
  job: Job;
  analysis?: Analysis | null;
  loading: boolean;
  mode: CardMode;
  act: (fn: (job: Job) => void) => void;
  onLike: (job: Job) => void;
  onDismiss: (job: Job) => void;
  onRestore: (job: Job) => void;
}) {
  const score = analysis?.relevance_score ?? null;
  const skills = parseSkills(job.skills);
  const salary = salaryLabel(job);
  const applyUrl = job.job_url_direct || job.job_url;
  const details = [
    ["Sede / area ammessa", job.location || "Da verificare"],
    ["Modalità", job.is_remote ? "Remoto" : analysis?.assessment?.work_mode === "hybrid" ? "Ibrido" : "Vedi annuncio"],
    ["Retribuzione", salary],
    ["Contratto", job.job_type],
    ["Livello", job.job_level],
    ["Settore", job.company_industry],
    ["Funzione", job.job_function],
    ["Contatto", job.emails],
  ].filter(([, v]) => v) as [string, string][];

  return (
    <>
      <SheetHeader className="gap-3 border-b p-6 pr-12">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className={cn("size-1.5 rounded-full", siteDot(job.site))} />
          {siteLabel(job.site)} · {timeAgo(job.date_posted)}
          {(job.duplicates ?? 1) > 1 && ` · pubblicata ${job.duplicates} volte`}
        </div>
        <div className="flex items-start gap-3">
          <CompanyAvatar name={job.company} logo={job.company_logo} className="size-12" />
          <div className="min-w-0">
            <SheetTitle className="text-lg leading-snug">{job.title}</SheetTitle>
            <SheetDescription>{job.company}</SheetDescription>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {/^(https?):\/\//i.test(applyUrl) && <Button render={<a href={applyUrl} target="_blank" rel="noreferrer" />} className="flex-1 sm:flex-none">
            Apri annuncio <ExternalLink />
          </Button>}
          {mode === "feed" && (
            <>
              <Button variant="outline" onClick={() => act(onLike)}>
                <Heart /> Preferita
              </Button>
              <Button variant="ghost" onClick={() => act(onDismiss)}>
                <X /> Scarta
              </Button>
            </>
          )}
          {mode === "saved" && (
            <Button variant="outline" onClick={() => act(onRestore)}>
              <Heart className="fill-current text-rose-500" /> Togli dai preferiti
            </Button>
          )}
          {(mode === "dismissed" || mode === "archived") && (
            <Button variant="outline" onClick={() => act(onRestore)}>
              <Undo2 /> Rimetti tra le offerte
            </Button>
          )}
        </div>
      </SheetHeader>

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-6 p-6">
          {analysis && (score != null || analysis.summary) && (
            <section className="space-y-3 rounded-xl border bg-muted/40 p-4">
              <div className="flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-sm font-medium">
                  <Sparkles className="size-4 text-primary" /> Analisi AI
                </h3>
                {score != null && (
                  <span className={cn("text-sm font-semibold tabular-nums", scoreColor(score).text)}>
                    {score}% match
                  </span>
                )}
              </div>
              {score == null && <p className="text-sm">Match non calcolabile con le informazioni disponibili.</p>}
              {analysis.assessment && <div className="space-y-1 text-sm">
                <p><strong>Verona o remoto dall’Italia:</strong> {analysis.assessment.location_reason}</p>
                <p className="text-muted-foreground">Attendibilità della valutazione: {({ high: "alta", medium: "media", low: "bassa" })[analysis.assessment.confidence]}</p>
                {analysis.assessment.missing_requirements?.length > 0 && <p>Requisiti da verificare: {analysis.assessment.missing_requirements.join("; ")}</p>}
              </div>}
              {analysis.summary && <p className="text-sm leading-relaxed">{analysis.summary}</p>}
              {analysis.reasons && analysis.reasons.length > 0 && (
                <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {analysis.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
              {analysis.tags && analysis.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {analysis.tags.map((t) => (
                    <Badge key={t} variant="secondary" className="font-normal">
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
            </section>
          )}

          {details.length > 0 && (
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              {details.map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="break-words">{value}</dd>
                </div>
              ))}
            </dl>
          )}

          {skills.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs text-muted-foreground">Competenze richieste</h3>
              <div className="flex flex-wrap gap-1.5">
                {skills.map((s) => (
                  <Badge key={s} variant="outline" className="font-normal">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <ApplicationEditor key={job.job_url} jobUrl={job.job_url} />
          <Separator />

          <section className="space-y-2">
            <h3 className="text-sm font-medium">Descrizione</h3>
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-11/12" />
                <Skeleton className="h-4 w-4/5" />
              </div>
            ) : (
              <div className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
                {job.description || "Nessuna descrizione disponibile per questo annuncio."}
              </div>
            )}
          </section>
        </div>
      </ScrollArea>
    </>
  );
}
