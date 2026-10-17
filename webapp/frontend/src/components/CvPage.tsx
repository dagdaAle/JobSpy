import { useEffect, useId, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileDown, FileText, Loader2, Plus, Star, Trash2, Upload, Wand2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { api } from "../api/client";
import type { CvSummary } from "../api/types";
import { useCv, useCvs } from "../hooks";
import { CvReviewPanel } from "./CvReviewPanel";

// Invalidate everything a CV change can touch: the library, the analyses
// (default CV drives the scoring) and the AI status in the header.
function useRefreshCvs() {
  const qc = useQueryClient();
  return () => Promise.all([
    qc.invalidateQueries({ queryKey: ["cvs"] }),
    qc.invalidateQueries({ queryKey: ["cv"] }),
    qc.invalidateQueries({ queryKey: ["status"] }),
  ]);
}

export function CvPage() {
  const cvs = useCvs();
  const refresh = useRefreshCvs();
  const [selected, setSelected] = useState<number | null>(null);
  const list = cvs.data?.cvs ?? [];
  const base = list.filter((c) => c.kind === "base");
  const tailored = list.filter((c) => c.kind === "tailored");

  useEffect(() => {
    if (selected === null && list.length) setSelected(list[0].id);
    if (selected !== null && cvs.data && !list.some((c) => c.id === selected)) setSelected(list[0]?.id ?? null);
  }, [list, selected, cvs.data]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">CV</h1>
        <p className="text-sm text-muted-foreground">
          Il CV predefinito (stella) è quello usato per calcolare il match. I CV adattati si generano dal dettaglio di un'offerta.
        </p>
      </div>
      <NewCv onCreated={(id) => { void refresh().then(() => setSelected(id)); }} />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <div className="space-y-4">
          <CvList title="CV base" items={base} selected={selected} onSelect={setSelected} />
          <CvList title="Adattati alle offerte" items={tailored} selected={selected} onSelect={setSelected} />
          {cvs.isSuccess && !list.length && <p className="text-sm text-muted-foreground">Nessun CV: caricane uno in PDF.</p>}
        </div>
        {selected !== null && <CvEditor key={selected} id={selected} onRevisionCreated={setSelected} />}
      </div>
    </div>
  );
}

function CvList({ title, items, selected, onSelect }: { title: string; items: CvSummary[]; selected: number | null; onSelect: (id: number) => void }) {
  if (!items.length) return null;
  return (
    <div className="space-y-1">
      <h2 className="px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h2>
      {items.map((c) => (
        <button key={c.id} type="button" onClick={() => onSelect(c.id)}
          className={cn("flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-muted",
            selected === c.id && "bg-muted font-medium")}>
          {c.is_default ? <Star className="size-3.5 shrink-0 fill-current text-amber-500" /> : <FileText className="size-3.5 shrink-0 text-muted-foreground" />}
          <span className="truncate">{c.name}</span>
        </button>
      ))}
    </div>
  );
}

function NewCv({ onCreated }: { onCreated: (id: number) => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const run = (p: Promise<{ id: number }>, ok: string) => {
    setBusy(true);
    p.then(({ id }) => { toast.success(ok); onCreated(id); })
      .catch((e: Error) => toast.error(e.message))
      .finally(() => setBusy(false));
  };
  return (
    <div className="flex flex-wrap gap-2">
      <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => {
        const file = e.target.files?.[0];
        e.target.value = "";
        if (file) run(api.uploadCv(file.name.replace(/\.pdf$/i, ""), file), "CV importato dal PDF");
      }} />
      <Button disabled={busy} onClick={() => fileRef.current?.click()}>
        {busy ? <Loader2 className="animate-spin" /> : <Upload />} Carica PDF
      </Button>
      <Button variant="outline" disabled={busy} onClick={() => run(api.createCv({ name: "Nuovo CV", markdown: "# Nome Cognome\n\n## Esperienze\n\n- \n" }), "CV creato")}>
        <Plus /> Nuovo da Markdown
      </Button>
      <p className="w-full text-xs text-muted-foreground">L’importazione conserva il testo del PDF. L’esportazione usa l’impaginazione di JobSpy.</p>
    </div>
  );
}

export function CvEditor({ id, compact = false, jobUrl, onRevisionCreated }: { id: number; compact?: boolean; jobUrl?: string; onRevisionCreated?: (id: number) => void }) {
  const cv = useCv(id);
  const refresh = useRefreshCvs();
  const fid = useId();
  const [name, setName] = useState("");
  const [markdown, setMarkdown] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (cv.data) { setName(cv.data.cv.name); setMarkdown(cv.data.cv.markdown); }
  }, [cv.data]);

  if (!cv.data) return <div className="text-sm text-muted-foreground">Caricamento…</div>;
  const data = cv.data.cv;
  const dirty = name !== data.name || markdown !== data.markdown;

  const save = () => {
    setSaving(true);
    api.updateCv(id, { name, markdown })
      .then(() => { toast.success(data.is_default ? "Salvato: le offerte verranno rianalizzate" : "CV salvato"); refresh(); })
      .catch((e: Error) => toast.error(e.message))
      .finally(() => setSaving(false));
  };
  const act = (p: Promise<unknown>, ok: string) => p.then(() => { toast.success(ok); refresh(); }).catch((e: Error) => toast.error(e.message));

  return (
    <div className="space-y-3">
      {!compact && (
        <div className="grid gap-2">
          <Label htmlFor={`${fid}-name`}>Nome</Label>
          <Input id={`${fid}-name`} value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {data.is_default && <Badge variant="secondary"><Star className="fill-current text-amber-500" /> Usato per l'analisi</Badge>}
        {data.kind === "tailored" && <Badge variant="outline">Adattato</Badge>}
      </div>
      {data.changes.length > 0 && (
        <div className="rounded-lg border bg-muted/40 p-3 text-sm">
          <p className="mb-1 font-medium">Modifiche dell'AI</p>
          <ul className="list-disc space-y-0.5 pl-5 text-muted-foreground">
            {data.changes.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}
      <Textarea aria-label="Testo del CV in Markdown" value={markdown} maxLength={50000}
        onChange={(e) => setMarkdown(e.target.value)}
        className={cn("font-mono text-xs", compact ? "min-h-72" : "min-h-[60vh]")} />
      <div className="flex flex-wrap gap-2">
        <Button disabled={!dirty || saving || !markdown.trim() || !name.trim()} onClick={save}>
          {saving && <Loader2 className="animate-spin" />} Salva
        </Button>
        <Button variant="outline" render={<a href={api.cvPdfUrl(id)} target="_blank" rel="noreferrer" />}>
          <FileDown /> PDF
        </Button>
        {!compact && data.kind === "base" && !data.is_default && (
          <Button variant="outline" onClick={() => act(api.setDefaultCv(id), "CV predefinito cambiato: le offerte verranno rianalizzate")}>
            <Star /> Usa per l'analisi
          </Button>
        )}
        {!data.is_default && (
          <Button variant="ghost" onClick={() => confirm(`Eliminare "${data.name}"?`) && act(api.deleteCv(id), "CV eliminato")}>
            <Trash2 /> Elimina
          </Button>
        )}
      </div>
      {dirty && <p className="text-xs text-muted-foreground">Modifiche non salvate: il PDF usa l'ultima versione salvata.</p>}
      <CvReviewPanel key={id} id={id} source={data.markdown} dirty={dirty} jobUrl={jobUrl} onCreated={(newId) => {
        toast.success("Copia revisionata salvata"); void refresh().then(() => onRevisionCreated?.(newId));
      }} />
    </div>
  );
}

// Detail sheet: tailored CVs for this job + generation from a base CV.
export function JobCvSection({ jobUrl }: { jobUrl: string }) {
  const cvs = useCvs();
  const refresh = useRefreshCvs();
  const list = cvs.data?.cvs ?? [];
  const base = list.filter((c) => c.kind === "base");
  const mine = list.filter((c) => c.kind === "tailored" && c.job_url === jobUrl);
  const [baseId, setBaseId] = useState<string>("");
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const chosen = baseId || String(base.find((c) => c.is_default)?.id ?? base[0]?.id ?? "");

  const generate = () => {
    setBusy(true);
    api.tailorCv(jobUrl, chosen ? Number(chosen) : undefined)
      .then(({ cv }) => { toast.success("CV adattato generato"); refresh(); setOpen(cv.id); })
      .catch((e: Error) => toast.error(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium">CV per questa offerta</h3>
      {base.length > 0 && <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-medium">Revisiona il CV base con poche correzioni</summary>
        <div className="mt-3"><CvEditor key={chosen} id={Number(chosen)} compact jobUrl={jobUrl}
          onRevisionCreated={(id) => setBaseId(String(id))} /></div>
      </details>}
      {base.length === 0 ? (
        <p className="text-sm text-muted-foreground">Carica prima un CV dalla pagina CV.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {base.length > 1 && (
            <Select items={base.map((c) => ({ value: String(c.id), label: c.name }))} value={chosen} onValueChange={(v) => v && setBaseId(v)}>
              <SelectTrigger className="w-56" aria-label="CV di partenza"><SelectValue /></SelectTrigger>
              <SelectContent>{base.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
            </Select>
          )}
          <Button variant="outline" disabled={busy} onClick={generate}>
            {busy ? <Loader2 className="animate-spin" /> : <Wand2 />} {busy ? "Generazione…" : "Genera CV adattato"}
          </Button>
        </div>
      )}
      {mine.map((c) => (
        <div key={c.id} className="rounded-lg border p-3">
          <button type="button" className="flex w-full items-center gap-2 text-left text-sm" onClick={() => setOpen(open === c.id ? null : c.id)}>
            <FileText className="size-4 text-muted-foreground" />
            <span className="flex-1 truncate">{c.name}</span>
            <span className="text-xs text-muted-foreground">{open === c.id ? "Chiudi" : "Apri"}</span>
          </button>
          {open === c.id && <div className="mt-3"><CvEditor id={c.id} compact jobUrl={jobUrl} onRevisionCreated={setOpen} /></div>}
        </div>
      ))}
    </section>
  );
}

// Application form: which CV was sent.
export function CvSelect({ value, onChange }: { value: number | null; onChange: (id: number | null) => void }) {
  const cvs = useCvs();
  const id = useId();
  const items = [{ value: "none", label: "Nessuno" }, ...(cvs.data?.cvs ?? []).map((c) => ({ value: String(c.id), label: c.name }))];
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>CV inviato</Label>
      <Select items={items} value={value === null ? "none" : String(value)} onValueChange={(v) => v && onChange(v === "none" ? null : Number(v))}>
        <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
        <SelectContent>{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}</SelectContent>
      </Select>
    </div>
  );
}
