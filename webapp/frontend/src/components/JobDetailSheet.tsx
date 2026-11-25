import { ApplicationEditor } from "./ApplicationEditor";
import { JobCvSection } from "./CvPage";
import type { ReactNode } from "react";
import { Bookmark, ChartColumn, CircleCheck, CircleHelp, CircleX, ExternalLink, List, Sparkles, Undo2, Wallet, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { Analysis, Job } from "../api/types";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../api/client";
import { useJobDetail } from "../hooks";
import { parseSkills, salaryLabel, siteLabel, timeAgo, REMOTE_SCOPE_LABEL, SENIORITY_LABEL } from "../lib/format";
import { type CardMode, jobReason, workModeLabel } from "./JobCard";
import { DECISION, DecisionBadge, jobDecision, Tag } from "./decision";

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
      <SheetContent className="w-full gap-0 bg-background p-0 sm:max-w-[560px]">
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
  const a = analysis?.assessment;
  const decision = jobDecision(analysis ?? undefined);
  const skills = parseSkills(job.skills);
  const salary = salaryLabel(job) ?? a?.salary ?? null;
  const applyUrl = job.job_url_direct || job.job_url;
  const canOpen = /^(https?):\/\//i.test(applyUrl);
  const mode_ = workModeLabel(job, analysis);
  const extra = [
    ["Area remota", REMOTE_SCOPE_LABEL[a?.remote_scope ?? ""]],
    ["Stack", a?.stack?.join(", ")],
    ["Lingue", a?.languages?.join(", ")],
    ["Livello", job.job_level],
    ["Settore", job.company_industry],
    ["Funzione", job.job_function],
    ["Contatto", job.emails],
  ].filter(([, v]) => v) as [string, string][];

  return (
    <>
      <div className={cn("space-y-3 px-6 pt-5 pb-6", DECISION[decision].tint)}>
        <div className="flex items-center justify-between gap-3 pr-10">
          <DecisionBadge decision={decision} onTint />
          <div className="flex gap-2">
            {canOpen && (
              <Button variant="ghost" size="icon" aria-label="Apri annuncio" render={<a href={applyUrl} target="_blank" rel="noreferrer" />} nativeButton={false} className="size-9 bg-card hover:bg-card">
                <ExternalLink />
              </Button>
            )}
            {mode === "feed" && (
              <Button variant="ghost" size="icon" aria-label="Aggiungi ai preferiti" onClick={() => act(onLike)} className="size-9 bg-card hover:bg-card"><Bookmark /></Button>
            )}
          </div>
        </div>
        <p className="text-[13px] text-muted-foreground">
          {[job.company, job.location, mode_].filter(Boolean).join(" · ")}
        </p>
        <SheetTitle className="font-heading text-2xl leading-tight font-semibold">{job.title}</SheetTitle>
        <SheetDescription className="text-sm leading-relaxed text-foreground">{jobReason(analysis ?? undefined)}</SheetDescription>
        <div className="flex flex-wrap gap-6 pt-1">
          <Num value={salary} label="RAL" unknown="non indicata" />
          <Num value={analysis?.relevance_score != null ? `${analysis.relevance_score}%` : null} label="punteggio AI" unknown="non calcolato" />
          <Num value={timeAgo(job.date_posted) || null} label={`su ${siteLabel(job.site)}${(job.duplicates ?? 1) > 1 ? ` e altri ${(job.duplicates ?? 1) - 1}` : ""}`} unknown="data non nota" />
        </div>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-6 p-6">
          <section className="space-y-3">
            <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Perché · le componenti</h3>
            <Feasibility analysis={analysis} />
            <Match analysis={analysis} />
            <Interest analysis={analysis} />
            <Component icon={<ChartColumn />} title="Carriera" verdict="dati insufficienti" unknown>
              L’analisi di oggi non valuta team, crescita o formazione.
            </Component>
            <Component icon={<Wallet />} title="Condizioni">
              <dl className="space-y-1.5">
                <Row k="RAL" v={salary} mono />
                <Row k="Contratto" v={job.job_type} />
                <Row k="Modalità" v={mode_} />
                <Row k="Seniority" v={SENIORITY_LABEL[a?.seniority ?? ""]} />
                <Row k="Sede" v={a?.location_reason || job.location} />
              </dl>
            </Component>
          </section>

          {skills.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Competenze richieste</h3>
              <div className="flex flex-wrap gap-1.5">{skills.map((s) => <Tag key={s}>{s}</Tag>)}</div>
            </section>
          )}

          {extra.length > 0 && (
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 rounded-lg border bg-card p-4 text-sm">
              {extra.map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="break-words">{value}</dd>
                </div>
              ))}
            </dl>
          )}

          {job.source && <SourceSection job={job} />}

          <ApplicationEditor key={job.job_url} jobUrl={job.job_url} />
          <JobCvSection key={`cv-${job.job_url}`} jobUrl={job.job_url} />

          <section className="space-y-2">
            <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Descrizione</h3>
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-11/12" />
                <Skeleton className="h-4 w-4/5" />
              </div>
            ) : (
              <div className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground">
                {job.description || "Nessuna descrizione disponibile per questo annuncio."}
              </div>
            )}
          </section>
        </div>
      </ScrollArea>

      <div className="flex justify-end gap-3 border-t bg-card px-6 py-4">
        {mode === "feed" && <Button variant="ghost" className="h-10 px-4" onClick={() => act(onDismiss)}><X /> Scarta</Button>}
        {mode === "saved" && <Button variant="outline" className="h-10 px-4" onClick={() => act(onRestore)}><Bookmark className="fill-current" /> Togli dai preferiti</Button>}
        {(mode === "dismissed" || mode === "archived") && <Button variant="outline" className="h-10 px-4" onClick={() => act(onRestore)}><Undo2 /> Rimetti tra le offerte</Button>}
        {canOpen && <Button className="h-10 px-5" render={<a href={applyUrl} target="_blank" rel="noreferrer" />} nativeButton={false}>Apri annuncio <ExternalLink /></Button>}
      </div>
    </>
  );
}

function Num({ value, label, unknown }: { value: string | null; label: string; unknown: string }) {
  return (
    <div>
      {value ? <p className="font-mono text-lg font-semibold">{value}</p> : <p className="text-base text-unknown-foreground italic">{unknown}</p>}
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v?: string | null; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 text-[13px]">
      <dt className="text-muted-foreground">{k}</dt>
      {v ? <dd className={cn("text-right font-medium", mono && "font-mono")}>{v}</dd> : <dd className="text-unknown-foreground italic">non indicato</dd>}
    </div>
  );
}

/** One component of the judgement; an unknown one is dashed with "dati insufficienti", never shown as low. */
function Component({ icon, title, verdict, tone, bar, unknown, children }: {
  icon: ReactNode; title: string; verdict?: string; tone?: "ok" | "warn" | "block"; bar?: number; unknown?: boolean; children?: ReactNode;
}) {
  const color = tone === "ok" ? "text-candidati-foreground" : tone === "warn" ? "text-valuta-foreground" : tone === "block" ? "text-destructive" : unknown ? "text-unknown-foreground" : "text-muted-foreground";
  return (
    <div className={cn("space-y-2 rounded-lg border bg-card px-4 py-3.5", unknown && "border-dashed border-unknown-border")}>
      <div className="flex items-center justify-between gap-3">
        <h4 className={cn("flex items-center gap-2 text-sm font-semibold [&_svg]:size-4", tone && color)}>{icon}<span className="text-foreground">{title}</span></h4>
        {verdict && <span className={cn("text-xs font-semibold", color)}>{verdict}</span>}
      </div>
      {unknown ? (
        <div className="h-2 rounded-full border border-dashed border-unknown-border" />
      ) : bar != null && (
        <div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-foreground" style={{ width: `${Math.round(bar * 100)}%` }} /></div>
      )}
      {children && <div className={cn("text-[13px] leading-relaxed", unknown ? "text-unknown-foreground" : "text-muted-foreground")}>{children}</div>}
    </div>
  );
}

function Feasibility({ analysis }: { analysis?: Analysis | null }) {
  const a = analysis?.assessment;
  if (!a) return <Component icon={<CircleHelp />} title="Fattibilità" verdict="dati insufficienti" unknown>Analisi non ancora fatta.</Component>;
  if (a.blockers?.length)
    return <Component icon={<CircleX />} title="Fattibilità" verdict="✕ bloccante" tone="block">{a.blockers.join("; ")}</Component>;
  if (a.location_fit === "incompatible")
    return <Component icon={<CircleX />} title="Fattibilità" verdict="✕ sede non compatibile" tone="block">{a.location_reason}</Component>;
  if (a.location_fit === "unknown")
    return <Component icon={<CircleHelp />} title="Fattibilità" verdict="⚠ da verificare" tone="warn">{a.location_reason || "Sede o vincoli da verificare."}</Component>;
  return <Component icon={<CircleCheck />} title="Fattibilità" verdict="✓ nessun bloccante" tone="ok">{a.location_reason}</Component>;
}

function Match({ analysis }: { analysis?: Analysis | null }) {
  const a = analysis?.assessment;
  const have = a?.cv_match?.length ?? 0;
  const miss = a?.missing_requirements?.length ?? 0;
  if (!a || have + miss === 0)
    return <Component icon={<List />} title="Corrispondenza" verdict="dati insufficienti" unknown>Requisiti non estratti dall’annuncio.</Component>;
  return (
    <Component icon={<List />} title="Corrispondenza" verdict={`${have} di ${have + miss} dal tuo CV`} bar={have / (have + miss)}>
      {miss > 0 && (
        <span className="flex flex-wrap items-center gap-1.5">
          <span>Manca o da verificare:</span>
          {a.missing_requirements.map((m) => <Tag key={m}>{m}</Tag>)}
        </span>
      )}
    </Component>
  );
}

function Interest({ analysis }: { analysis?: Analysis | null }) {
  const score = analysis?.relevance_score;
  const tags = analysis?.tags ?? [];
  if (score == null && !tags.length)
    return <Component icon={<Sparkles />} title="Interesse" verdict="dati insufficienti" unknown>Punteggio non calcolabile con le informazioni dell’annuncio.</Component>;
  return (
    <Component icon={<Sparkles />} title="Interesse" verdict={score != null ? `${score}%` : undefined} bar={score != null ? score / 100 : undefined}>
      {tags.length > 0 && <span className="flex flex-wrap gap-1.5">{tags.map((t) => <Tag key={t}>{t}</Tag>)}</span>}
    </Component>
  );
}

/** What freehire knows about the job: closed/suspect state, requirements, manual analysis. */
function SourceSection({ job }: { job: Job }) {
  const qc = useQueryClient();
  const src = job.source!;
  const analyze = () =>
    api.analyzeJob(job.job_url)
      .then(() => { toast.success("Analisi fatta"); qc.invalidateQueries(); })
      .catch((e: Error) => toast.error(e.message));
  const reqs = src.requirements ?? [];
  return (
    <div className="space-y-2">
      <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Dalla fonte (freehire{src.origin ? ` · ${src.origin}` : ""})</h3>
      <div className="flex flex-wrap items-center gap-1.5">
        {src.closed_at && <span className="rounded-full bg-destructive-soft px-2.5 py-1 text-xs font-semibold text-destructive">Chiusa alla fonte</span>}
        {src.suspect && (
          <span className="rounded-full bg-valuta px-2.5 py-1 text-xs font-semibold text-valuta-foreground">
            Sospetta: {src.reality?.fake_freshness ? "falsa nuova" : `ripubblicata ${src.reality?.mass_posting_count ?? "più"} volte`}
          </span>
        )}
        {src.suspect && (
          <Button size="sm" variant="outline" onClick={analyze}>
            <Sparkles /> Analizza ora
          </Button>
        )}
      </div>
      {reqs.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {reqs.map((r, i) => (
            <li key={i}>
              {r.text}
              {r.priority === "preferred" && <span className="text-muted-foreground"> (preferito)</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
