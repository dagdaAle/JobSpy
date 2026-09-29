import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, ClipboardList, Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { EmptyState } from "./JobGrid";
import { ApplicationFields } from "./ApplicationFields";
import type { Job, ManualApplication } from "../api/types";
import { api } from "../api/client";
import { dateLabel, emptyApplication, isClosed, isDue, STATUS_ITEMS, STATUS_LABELS, today } from "../lib/applications";

const STATUS_FILTER = [{ value: "all", label: "Tutti gli stati" }, ...STATUS_ITEMS];
const DEADLINE_FILTER = [{ value: "all", label: "Tutte le scadenze" }, { value: "due", label: "Da seguire oggi" }, { value: "scheduled", label: "Con prossimo passo" }];

export function ApplicationsPage({ onOpen }: { onOpen: (job: Job) => void }) {
  const query = useQuery({ queryKey: ["applications"], queryFn: api.applications, refetchInterval: 60_000 });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [deadline, setDeadline] = useState("all");
  const [manual, setManual] = useState(false);
  const applications = query.data?.applications ?? {};
  const all = Object.values(applications);
  const jobs = (query.data?.jobs ?? []).filter((job) => {
    const app = applications[job.job_url];
    if (!app) return false;
    if (status !== "all" && app.status !== status) return false;
    if (deadline === "due" && !isDue(app)) return false;
    if (deadline === "scheduled" && (!app.follow_up_on || isClosed(app))) return false;
    return `${job.title} ${job.company} ${app.contact} ${app.next_step}`.toLowerCase().includes(search.trim().toLowerCase());
  }).sort((a, b) => {
    const aa = applications[a.job_url], bb = applications[b.job_url];
    const dueOrder = Number(isDue(bb)) - Number(isDue(aa));
    if (dueOrder) return dueOrder;
    const dateOrder = (isClosed(aa) ? "9999" : aa.follow_up_on ?? "9999").localeCompare(isClosed(bb) ? "9999" : bb.follow_up_on ?? "9999");
    return dateOrder || (bb.updated_at ?? "").localeCompare(aa.updated_at ?? "");
  });
  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="space-y-1"><h1 className="text-2xl font-semibold tracking-tight">Candidature</h1>
        <p className="text-sm text-muted-foreground">Tutti i portali, un solo registro. Parti dai prossimi passi da seguire oggi.</p></div>
      <Button onClick={() => setManual(true)}><Plus /> Inserisci candidatura</Button>
    </div>
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {[["In corso", all.filter((a) => !isClosed(a)).length], ["Da seguire oggi", all.filter(isDue).length], ["Concluse", all.filter(isClosed).length]].map(([label, count]) => (
        <Card key={label}><CardContent className="space-y-1 p-4"><p className="text-sm text-muted-foreground">{label}</p><p className="text-2xl font-semibold tabular-nums">{query.isLoading ? "—" : count}</p></CardContent></Card>
      ))}
    </div>
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative w-full sm:w-80"><Search className="absolute top-2 left-2.5 size-4 text-muted-foreground" />
        <Input className="pl-8" aria-label="Cerca candidature" placeholder="Ruolo, azienda, contatto…" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
      <Select items={STATUS_FILTER} value={status} onValueChange={(v) => v && setStatus(v)}>
        <SelectTrigger aria-label="Filtra per stato"><SelectValue /></SelectTrigger>
        <SelectContent>{STATUS_FILTER.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectContent>
      </Select>
      <Select items={DEADLINE_FILTER} value={deadline} onValueChange={(v) => v && setDeadline(v)}>
        <SelectTrigger aria-label="Filtra per scadenza"><SelectValue /></SelectTrigger>
        <SelectContent>{DEADLINE_FILTER.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectContent>
      </Select>
      <span className="text-sm text-muted-foreground">{jobs.length} candidature</span>
    </div>
    <p className="flex items-start gap-2 text-xs text-muted-foreground"><CalendarClock className="size-4 shrink-0" />
      Le date sono promemoria in questa pagina. Nessuna email o notifica esterna viene inviata.</p>
    {query.isLoading ? <Skeleton className="h-56" /> : query.isError ? (
      <EmptyState icon={<ClipboardList />} title="Impossibile caricare le candidature">
        <Button variant="outline" onClick={() => query.refetch()}>Riprova</Button>
      </EmptyState>
    ) : !jobs.length ? <EmptyState icon={<ClipboardList />} title={all.length ? "Nessuna candidatura con questi filtri" : "Il tuo registro candidature"}>
      {all.length ? "Modifica i filtri per vedere le altre candidature." : "Inserisci una candidatura esterna oppure registra l’invio dal dettaglio di un’offerta."}
    </EmptyState> : <div className="rounded-xl border bg-card">
      <Table>
        <TableHeader><TableRow><TableHead className="pl-4">Ruolo e azienda</TableHead><TableHead>Stato</TableHead><TableHead>Inviata</TableHead><TableHead>Prossimo passo</TableHead><TableHead className="pr-4">Quando</TableHead></TableRow></TableHeader>
        <TableBody>{jobs.map((job) => {
          const app = applications[job.job_url];
          return <TableRow key={job.job_url}>
            <TableCell className="pl-4"><Button variant="link" className="h-auto max-w-72 whitespace-normal p-0 text-left" onClick={() => onOpen(job)}>{job.title}</Button>
              <p className="text-xs text-muted-foreground">{job.company}</p></TableCell>
            <TableCell><Badge variant="secondary">{STATUS_LABELS[app.status]}</Badge></TableCell>
            <TableCell>{dateLabel(app.applied_on)}</TableCell>
            <TableCell className="max-w-64 whitespace-normal">{app.next_step || "Da definire"}</TableCell>
            <TableCell className="pr-4">{isDue(app) ? <Badge variant="outline" className="text-score-mid"><CalendarClock className="size-3" />{dateLabel(app.follow_up_on)}</Badge> : dateLabel(app.follow_up_on)}</TableCell>
          </TableRow>;
        })}</TableBody>
      </Table>
    </div>}
    {manual && <ManualApplicationDialog onClose={() => setManual(false)} />}
  </div>;
}

function ManualApplicationDialog({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<ManualApplication>({ ...emptyApplication(""), status: "applied", applied_on: today(), title: "", company: "", url: null, location: "" });
  const qc = useQueryClient();
  const save = useMutation({ mutationFn: api.createManualApplication,
    onSuccess: () => {
      for (const key of ["applications", "jobs", "analytics"]) qc.invalidateQueries({ queryKey: [key] });
      toast.success("Candidatura inserita"); onClose();
    }, onError: (err: Error) => toast.error(err.message),
  });
  return <Dialog open onOpenChange={(open) => !open && !save.isPending && onClose()}>
    <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-xl">
      <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); save.mutate(form); }}>
        <DialogHeader><DialogTitle>Inserisci candidatura</DialogTitle><DialogDescription>Per offerte trovate fuori da JobSpy, su qualsiasi portale o tramite contatto diretto.</DialogDescription></DialogHeader>
        <fieldset disabled={save.isPending} className="space-y-4">
          {([['title', 'Ruolo'], ['company', 'Azienda'], ['location', 'Sede (facoltativa)']] as const).map(([key, label]) => <div key={key} className="grid gap-2">
            <Label htmlFor={`manual-${key}`}>{label}</Label><Input id={`manual-${key}`} maxLength={300} required={key !== 'location'} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
          </div>)}
          <div className="grid gap-2"><Label htmlFor="manual-url">Link annuncio (facoltativo)</Label><Input id="manual-url" type="url" placeholder="https://…" value={form.url ?? ""} onChange={(e) => setForm({ ...form, url: e.target.value || null })} /></div>
          <ApplicationFields value={form} onChange={(value) => setForm({ ...form, ...value })} />
          <DialogFooter><Button variant="outline" type="button" onClick={onClose}>Annulla</Button><Button type="submit" disabled={save.isPending || !form.title.trim() || !form.company.trim()}>{save.isPending ? "Salvataggio…" : "Inserisci candidatura"}</Button></DialogFooter>
        </fieldset>
      </form>
    </DialogContent>
  </Dialog>;
}
