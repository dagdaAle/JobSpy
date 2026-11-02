import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, History, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ApplicationFields } from "./ApplicationFields";
import { api } from "../api/client";
import type { Application, ApplicationEvent } from "../api/types";
import { dateLabel, emptyApplication, FIELD_LABELS, STATUS_LABELS, today } from "../lib/applications";

export function ApplicationEditor({ jobUrl }: { jobUrl: string }) {
  const query = useQuery({ queryKey: ["applications"], queryFn: api.applications });
  if (query.isLoading) return <Skeleton className="h-40" />;
  if (query.isError) return <div className="text-sm text-destructive">
    Impossibile caricare la candidatura. <Button variant="outline" onClick={() => query.refetch()}>Riprova</Button>
  </div>;
  const app = query.data?.applications?.[jobUrl];
  return <ApplicationForm key={jobUrl} initial={app ?? emptyApplication(jobUrl)} tracked={!!app} />;
}

function ApplicationForm({ initial, tracked }: { initial: Application; tracked: boolean }) {
  const [form, setForm] = useState(initial);
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: api.saveApplication,
    onSuccess: () => {
      for (const key of ["jobs", "job", "applications", "application-history", "analytics", "channels"]) qc.invalidateQueries({ queryKey: [key] });
      toast.success("Candidatura salvata");
    },
    onError: (err: Error) => toast.error(err.message),
  });
  return <section className="space-y-6">
    <form className="space-y-4 rounded-xl border p-4" onSubmit={(e) => { e.preventDefault(); save.mutate(form); }}>
      <div className="space-y-1">
        <h3 className="text-sm font-medium">La tua candidatura</h3>
        <p className="text-xs text-muted-foreground">Registra qui l’invio dopo aver completato la candidatura sul portale dell’azienda.</p>
      </div>
      {!form.applied_on && <Button type="button" variant="secondary" disabled={save.isPending} onClick={() => {
        const sent = { ...form, status: "applied" as const, applied_on: today() };
        setForm(sent); save.mutate(sent);
      }}><Check /> Candidatura inviata oggi</Button>}
      <fieldset disabled={save.isPending} className="space-y-4">
        <ApplicationFields value={form} onChange={setForm} />
        <Button type="submit" disabled={save.isPending}>{save.isPending ? "Salvataggio…" : "Salva candidatura"}</Button>
      </fieldset>
    </form>
    {tracked && <ApplicationHistory jobUrl={form.job_url} />}
  </section>;
}

function eventText(event: ApplicationEvent) {
  if (event.kind === "note") return [String(event.content.text ?? "")];
  if (event.kind === "imported") return ["Candidatura già presente: dati conservati all’attivazione della cronologia."];
  return Object.entries(event.content).flatMap(([key, change]) => {
    if (!change || typeof change !== "object" || !("to" in change)) return [];
    if (event.kind === "created" && !change.to) return [];
    const display = (v: unknown) => key === "status" ? STATUS_LABELS[v as Application["status"]] ?? String(v ?? "—") : String(v || "—");
    return [`${FIELD_LABELS[key] ?? key}: ${event.kind === "updated" ? `${display("from" in change ? change.from : null)} → ` : ""}${display(change.to)}`];
  });
}

function ApplicationHistory({ jobUrl }: { jobUrl: string }) {
  const query = useQuery({ queryKey: ["application-history", jobUrl], queryFn: () => api.applicationHistory(jobUrl) });
  const [text, setText] = useState("");
  const [date, setDate] = useState(today());
  const qc = useQueryClient();
  const add = useMutation({
    mutationFn: api.addApplicationNote,
    onSuccess: () => {
      setText(""); qc.invalidateQueries({ queryKey: ["application-history", jobUrl] });
      toast.success("Aggiornamento aggiunto");
    },
    onError: (err: Error) => toast.error(err.message),
  });
  return <div className="space-y-4">
    <h3 className="flex items-center gap-2 text-sm font-medium"><History className="size-4" /> Cronologia</h3>
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); add.mutate({ job_url: jobUrl, text, occurred_on: date }); }}>
      <Textarea aria-label="Aggiornamento della candidatura" placeholder="es. Ricevuto invito al colloquio tecnico" required maxLength={5000}
        disabled={add.isPending} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex flex-wrap gap-2">
        <Input className="w-auto" aria-label="Data aggiornamento" type="date" required disabled={add.isPending} value={date} onChange={(e) => setDate(e.target.value)} />
        <Button variant="outline" type="submit" disabled={add.isPending || !text.trim() || !date}><Plus /> Aggiungi aggiornamento</Button>
      </div>
    </form>
    {query.isLoading && <Skeleton className="h-24" />}
    {query.isError && <Button variant="outline" onClick={() => query.refetch()}>Cronologia non disponibile: riprova</Button>}
    <ol className="space-y-4 border-l pl-4">
      {query.data?.events.map((event) => <li key={event.id} className="space-y-2 text-sm">
        <div className="flex items-center gap-2"><Badge variant="secondary">{dateLabel(event.occurred_on)}</Badge>
          <span className="text-xs text-muted-foreground">{event.kind === "note" ? "Aggiornamento" : event.kind === "updated" ? "Modifica" : "Registrazione"}</span>
        </div>
        {eventText(event).map((line, i) => <p key={i} className="whitespace-pre-wrap break-words text-muted-foreground">{line}</p>)}
      </li>)}
    </ol>
  </div>;
}
