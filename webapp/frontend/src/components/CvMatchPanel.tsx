// "CV per questa offerta": score of the chosen CV, keywords to confirm, verified patches to accept.
// Contract: specs/004-cv-match/contract.md.
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, Loader2, RefreshCw, ShieldAlert, Square, SquareCheck, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { api } from "../api/client";
import type { MatchReport, TailorProposal } from "../api/types";

const MAX_ATTESTED = 30;
const touch = "h-11 sm:h-8"; // ≥ 44 px on phones

const COMPONENTS: { key: keyof MatchReport["components"]; label: string; weight: number }[] = [
  { key: "keyword_match", label: "Parole chiave", weight: 40 },
  { key: "skills_coverage", label: "Competenze", weight: 20 },
  { key: "title_match", label: "Titolo del ruolo", weight: 15 },
  { key: "section_completeness", label: "Sezioni", weight: 15 },
  { key: "date_consistency", label: "Date", weight: 10 },
];

const scoreTone = (n: number) => (n >= 75 ? "text-score-high" : n >= 50 ? "text-score-mid" : "text-score-low");
const errText = (e: unknown) => (e instanceof Error ? e.message : "Operazione non riuscita");

export function CvMatchPanel({ cvId, jobUrl, onSaved }: { cvId: number; jobUrl: string; onSaved: (newCvId: number) => void }) {
  const qc = useQueryClient();
  const key = ["cv-match", cvId, jobUrl];
  const match = useQuery({ queryKey: key, queryFn: () => api.cvMatch(cvId, jobUrl), retry: false, staleTime: 5 * 60_000 });
  const [attested, setAttested] = useState<string[]>([]);
  const [proposal, setProposal] = useState<TailorProposal | null>(null);
  const [chosen, setChosen] = useState<number[]>([]);
  const [busy, setBusy] = useState<"refresh" | "propose" | "save" | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<{ before: number; after: number } | null>(null);

  async function run(action: "refresh" | "propose" | "save") {
    setBusy(action); setError("");
    try {
      if (action === "refresh") {
        setProposal(null);
        qc.setQueryData(key, await api.cvMatch(cvId, jobUrl, true));
      } else if (action === "propose") {
        setProposal(null); setSaved(null);
        const p = await api.tailorProposal(cvId, jobUrl, attested);
        setProposal(p); setChosen(p.patches.map((_, i) => i));
      } else if (proposal) {
        const res = await api.tailorCv({
          job_url: jobUrl, base_cv_id: cvId, attested, source_hash: proposal.source_hash,
          patches: proposal.patches.filter((_, i) => chosen.includes(i)).map(({ before, after, reason }) => ({ before, after, reason })),
        });
        setProposal(null); setSaved({ before: res.score_before, after: res.score_after });
        toast.success("CV adattato salvato");
        onSaved(res.cv.id);
      }
    } catch (e) {
      if ((e as { status?: number }).status === 409) {
        setProposal(null);
        toast.error("Il CV è cambiato: rigenera");
      } else setError(errText(e));
    } finally { setBusy(null); }
  }

  function toggle(term: string) {
    setProposal(null);
    setAttested((old) => (old.includes(term) ? old.filter((t) => t !== term) : [...old, term]));
  }

  if (match.isPending)
    return (
      <div className="space-y-3 rounded-lg border bg-card p-4" aria-live="polite" aria-busy="true">
        <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Analizzo l’annuncio… la prima volta servono alcuni secondi.</p>
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  if (match.isError)
    return (
      <div role="alert" className="space-y-2 rounded-lg border border-dashed border-unknown-border bg-card p-4 text-sm">
        <p className="flex items-center gap-2 font-medium text-destructive"><ShieldAlert className="size-4" />{errText(match.error)}</p>
        <Button variant="outline" className={touch} onClick={() => match.refetch()}>Riprova</Button>
      </div>
    );

  const m = match.data;
  const found = m.keywords.filter((k) => k.found);
  const missing = m.keywords.filter((k) => !k.found);

  return (
    <div className="space-y-4">
      {/* a) Analisi */}
      <section aria-label="Punteggio del CV" className="space-y-4 rounded-lg border bg-card p-4">
        <div className="flex items-center gap-3 sm:gap-4">
          <ScoreRing value={m.overall} />
          <div className="min-w-0 flex-1 space-y-1">
            <p className="text-sm font-semibold">{m.job.role}{m.job.company && <span className="font-normal text-muted-foreground"> · {m.job.company}</span>}</p>
            <p className="text-xs text-muted-foreground">Stima di JobSpy, non il punteggio di un ATS reale.</p>
            <Button variant="ghost" size="sm" className={cn(touch, "-ml-2")} disabled={busy !== null} onClick={() => run("refresh")}>
              {busy === "refresh" ? <Loader2 className="animate-spin" /> : <RefreshCw />} Rileggi l’annuncio
            </Button>
          </div>
        </div>
        <dl className="space-y-2.5">
          {COMPONENTS.map(({ key: k, label, weight }) => {
            const v = m.components[k];
            return (
              <div key={k} className="space-y-1">
                <div className="flex items-baseline justify-between gap-2 text-sm">
                  <dt>{label} <span className="text-xs text-muted-foreground">{weight}%</span></dt>
                  <dd className={cn("font-mono text-xs", v === null ? "text-unknown-foreground italic" : "font-semibold")}>{v === null ? "non valutabile" : v}</dd>
                </div>
                {v === null ? (
                  <div className="h-2 rounded-full border border-dashed border-unknown-border" aria-hidden />
                ) : (
                  <div className="h-2 overflow-hidden rounded-full bg-muted" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={v}>
                    <div className="h-full rounded-full bg-foreground" style={{ width: `${v}%` }} />
                  </div>
                )}
              </div>
            );
          })}
        </dl>
      </section>

      {/* b) Parole chiave */}
      <section aria-label="Parole chiave dell’annuncio" className="space-y-3 rounded-lg border bg-card p-4">
        <h4 className="text-sm font-semibold">Parole chiave dell’annuncio</h4>
        {found.length > 0 && <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground">Già nel CV ({found.length})</p>
          <ul className="flex flex-wrap gap-1.5">
            {found.map((k) => <li key={k.term} className="inline-flex items-center gap-1 rounded-full bg-candidati px-2.5 py-1 text-xs font-medium text-candidati-foreground [&_svg]:size-3.5"><Check aria-hidden />{k.term}</li>)}
          </ul>
        </div>}
        {missing.length > 0 && <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground">Mancanti ({missing.length}): spunta «ce l’ho» solo se le hai davvero. Solo queste possono entrare nel CV adattato.</p>
          <ul className="flex flex-wrap gap-1.5">
            {missing.map((k) => {
              const on = attested.includes(k.term);
              return <li key={k.term}>
                <button type="button" aria-pressed={on} disabled={busy !== null || (!on && attested.length >= MAX_ATTESTED)} onClick={() => toggle(k.term)}
                  className={cn("inline-flex min-h-11 items-center gap-1.5 rounded-full border px-3 text-xs font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50 sm:min-h-8 [&_svg]:size-4",
                    on ? "border-primary bg-primary text-primary-foreground" : "border-dashed border-unknown-border bg-card text-foreground hover:border-foreground/40")}>
                  {on ? <SquareCheck aria-hidden /> : <Square aria-hidden />}
                  {k.term}
                  <span className={cn("font-normal", on ? "text-primary-foreground/80" : "text-muted-foreground")}>{on ? "ce l’ho" : k.kind === "required" ? "richiesta" : "ce l’ho?"}</span>
                </button>
              </li>;
            })}
          </ul>
        </div>}
        {m.keywords.length === 0 && <p className="text-sm text-muted-foreground">Nessuna parola chiave estratta dall’annuncio.</p>}
        <Button className={touch} disabled={busy !== null} onClick={() => run("propose")}>
          {busy === "propose" ? <Loader2 className="animate-spin" /> : <Wand2 />} {busy === "propose" ? "Preparo le modifiche…" : "Adatta CV"}
        </Button>
      </section>

      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {saved && <p className="text-sm" aria-live="polite">CV adattato salvato: <Score before={saved.before} after={saved.after} /></p>}

      {/* c) Risultato */}
      {proposal && <section aria-label="Modifiche proposte" aria-live="polite" className="space-y-3 rounded-lg border bg-card p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h4 className="text-sm font-semibold">Modifiche proposte</h4>
          <p className="text-sm">Punteggio <Score before={proposal.score_before} after={proposal.score_after} /> <span className="text-xs text-muted-foreground">con tutte le modifiche</span></p>
        </div>
        {proposal.rejected > 0 && <p className="text-xs text-muted-foreground">{proposal.rejected} {proposal.rejected === 1 ? "modifica scartata" : "modifiche scartate"} dai controlli</p>}
        {proposal.patches.length === 0 && <p className="text-sm text-muted-foreground">Nessuna modifica proposta supera i controlli.</p>}
        {proposal.patches.map((p, i) => (
          <div key={i} className="space-y-2 rounded-md border p-3">
            <label className="flex min-h-11 cursor-pointer items-start gap-3 text-sm font-medium sm:min-h-0">
              <input type="checkbox" className="mt-0.5 size-5 shrink-0 accent-primary sm:size-4" checked={chosen.includes(i)} disabled={busy !== null}
                onChange={(e) => setChosen((old) => (e.target.checked ? [...old, i] : old.filter((n) => n !== i)))} />
              <span className="min-w-0">{p.reason}</span>
            </label>
            {p.keywords.length > 0 && <ul className="flex flex-wrap gap-1" aria-label="Parole chiave portate">
              {p.keywords.map((k) => <li key={k} className="rounded-sm border bg-muted px-1.5 py-0.5 text-[11px]">{k}</li>)}
            </ul>}
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-sm bg-muted/50 p-2"><p className="text-xs font-medium text-muted-foreground">Prima</p><p className="text-sm break-words whitespace-pre-wrap">{p.before}</p></div>
              <div className="rounded-sm bg-candidati/60 p-2"><p className="text-xs font-medium text-muted-foreground">Dopo</p><p className="text-sm break-words whitespace-pre-wrap">{p.after}</p></div>
            </div>
          </div>
        ))}
        {proposal.patches.length > 0 && <>
          <Button className={touch} disabled={busy !== null || chosen.length === 0} onClick={() => run("save")}>
            {busy === "save" && <Loader2 className="animate-spin" />} Salva CV adattato ({chosen.length})
          </Button>
          <p className="text-xs text-muted-foreground">Viene creata una copia: il CV di partenza resta com’è.</p>
        </>}
      </section>}
    </div>
  );
}

function ScoreRing({ value }: { value: number }) {
  const r = 30, c = 2 * Math.PI * r;
  return (
    <div className={cn("relative size-16 shrink-0 sm:size-20", scoreTone(value))} role="img" aria-label={`Punteggio ${value} su 100`}>
      <svg viewBox="0 0 72 72" className="size-full -rotate-90" aria-hidden>
        <circle cx="36" cy="36" r={r} fill="none" strokeWidth="7" className="stroke-muted" />
        <circle cx="36" cy="36" r={r} fill="none" strokeWidth="7" strokeLinecap="round" stroke="currentColor" strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} />
      </svg>
      <span className="absolute inset-0 grid place-items-center font-mono text-xl font-semibold text-foreground sm:text-2xl">{value}</span>
    </div>
  );
}

function Score({ before, after }: { before: number; after: number }) {
  return <span className="font-mono font-semibold"><span className={scoreTone(before)}>{before}</span> → <span className={scoreTone(after)}>{after}</span></span>;
}
