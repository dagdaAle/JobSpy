import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { Channel, WorkMode } from "../api/types";
import { useCreateChannel, useUpdateChannel } from "../hooks";
import { siteLabel } from "../lib/format";

const INITIAL = {
  name: "",
  site: "linkedin",
  search_term: "",
  location: "Verona, Veneto",
  distance_km: 50,
  results_wanted: 50,
  hours_old: 336,
  is_remote: false,
  include_keywords: "",
  exclude_keywords: "senior, lead, staff, principal, stage, tirocinio",
  exclude_companies: "",
  work_mode: "any" as WorkMode,
};

const WORK_MODES: { value: WorkMode; label: string }[] = [
  { value: "any", label: "Qualsiasi" },
  { value: "remote_or_hybrid", label: "Remoto o ibrido" },
  { value: "remote", label: "Solo remoto" },
];

const toList = (s: string) => s.split(",").map((w) => w.trim()).filter(Boolean);
const fromList = (l?: string[]) => (l ?? []).join(", ");

function fromChannel(ch: Channel): typeof INITIAL {
  return {
    name: ch.name ?? "",
    site: ch.site,
    search_term: ch.search_term,
    location: ch.location ?? "",
    distance_km: ch.distance_km ?? 25,
    results_wanted: ch.results_wanted ?? 25,
    hours_old: ch.hours_old ?? 0,
    is_remote: ch.is_remote,
    include_keywords: fromList(ch.include_keywords),
    exclude_keywords: fromList(ch.exclude_keywords),
    exclude_companies: fromList(ch.exclude_companies),
    work_mode: ch.work_mode ?? "any",
  };
}

export function NewChannelDialog({
  open,
  onOpenChange,
  sites,
  channel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sites: string[];
  // Set = edit this channel instead of creating one.
  channel?: Channel | null;
}) {
  const create = useCreateChannel();
  const update = useUpdateChannel();
  const mutation = channel ? update : create;
  const [form, setForm] = useState(INITIAL);
  useEffect(() => {
    if (open) setForm(channel ? fromChannel(channel) : INITIAL);
  }, [open, channel]);
  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.search_term.trim()) return;
    const body = {
      ...form,
      name: form.name.trim(),
      hours_old: form.hours_old || null,
      include_keywords: toList(form.include_keywords),
      exclude_keywords: toList(form.exclude_keywords),
      exclude_companies: toList(form.exclude_companies),
    };
    if (channel) {
      update.mutate(
        { id: channel.id, body },
        {
          onSuccess: () => {
            toast.success("Canale aggiornato: i filtri valgono dal prossimo aggiornamento");
            onOpenChange(false);
          },
        },
      );
      return;
    }
    create.mutate(
      body,
      {
        onSuccess: (r) => {
          toast.success(`Canale creato: ${r.new_count} offerte trovate`);
          setForm(INITIAL);
          onOpenChange(false);
        },
      },
    );
  };

  const remoteBoard = ["remotive", "remoteok", "weworkremotely", "workingnomads"].includes(form.site);
  const siteItems = sites.map((s) => ({ value: s, label: siteLabel(s) }));

  return (
    <Dialog open={open} onOpenChange={(o) => !mutation.isPending && onOpenChange(o)}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={submit} className="grid gap-5">
          <DialogHeader>
            <DialogTitle>{channel ? "Modifica canale" : "Nuovo canale"}</DialogTitle>
            <DialogDescription>
              {channel
                ? "Le offerte già trovate restano; i nuovi filtri valgono dal prossimo aggiornamento."
                : "Un canale è una ricerca su un sito, aggiornata ogni mattina. La prima ricerca parte subito."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Cosa cerchi" className="sm:col-span-2">
              <Input
                autoFocus
                required
                placeholder="es. sviluppatore python"
                value={form.search_term}
                onChange={(e) => set("search_term", e.target.value)}
              />
            </Field>
            <Field label="Sito">
              <Select items={siteItems} value={form.site} onValueChange={(v) => v && set("site", v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {siteItems.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label={remoteBoard ? "Area candidati (vedi singole offerte)" : "Dove"}>
              <Input
                disabled={remoteBoard}
                placeholder="es. Verona, Veneto"
                value={remoteBoard ? "Remoto: verifica paesi ammessi" : form.location}
                onChange={(e) => set("location", e.target.value)}
              />
            </Field>
            <Field label="Nome del canale (facoltativo)" className="sm:col-span-2">
              <Input
                placeholder={`${siteLabel(form.site)}: ${form.search_term || "…"}`}
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
              />
            </Field>
            <Field label="Raggio (km)">
              <Input
                type="number"
                min={1}
                max={500}
                disabled={remoteBoard}
                value={form.distance_km}
                onChange={(e) => set("distance_km", Number(e.target.value))}
              />
            </Field>
            <Field label="Risultati massimi">
              <Input
                type="number"
                min={1}
                max={500}
                value={form.results_wanted}
                onChange={(e) => set("results_wanted", Number(e.target.value))}
              />
            </Field>
            <Field label="Annunci degli ultimi giorni (0 = tutti)">
              <Input type="number" min={0} max={365} value={form.hours_old / 24}
                onChange={(e) => set("hours_old", Number(e.target.value) * 24)} />
            </Field>
            <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 sm:col-span-2">
              <span className="text-sm">Solo offerte da remoto</span>
              <Switch disabled={remoteBoard} checked={remoteBoard || form.is_remote} onCheckedChange={(v) => set("is_remote", v)} />
            </label>
            <Field label="Parole richieste (titolo o testo, almeno una)" className="sm:col-span-2">
              <Input
                placeholder="es. python, llm, langchain, machine learning"
                value={form.include_keywords}
                onChange={(e) => set("include_keywords", e.target.value)}
              />
            </Field>
            <Field label="Parole escluse (nel titolo)" className="sm:col-span-2">
              <Input
                placeholder="es. senior, lead, stage"
                value={form.exclude_keywords}
                onChange={(e) => set("exclude_keywords", e.target.value)}
              />
            </Field>
            <Field label="Aziende escluse">
              <Input
                placeholder="es. agenzia x, randstad"
                value={form.exclude_companies}
                onChange={(e) => set("exclude_companies", e.target.value)}
              />
            </Field>
            <Field label="Modalità di lavoro">
              <Select
                items={WORK_MODES}
                value={form.work_mode}
                onValueChange={(v) => v && set("work_mode", v as WorkMode)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WORK_MODES.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          <p className="text-xs text-muted-foreground">
            Per Verona lascia “Solo offerte da remoto” disattivato: include presenza e ibrido.
            Sui siti remoti la sede indica i paesi ammessi; gli annunci senza data restano visibili.
            Parole separate da virgola. “Modalità di lavoro” è un filtro sul testo dell’annuncio:
            l’analisi AI verifica poi i paesi ammessi.
          </p>
          {mutation.isError && (
            <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Annulla
            </Button>
            <Button type="submit" disabled={mutation.isPending || !form.search_term.trim()}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              {channel ? "Salva" : create.isPending ? "Cerco le prime offerte…" : "Crea canale"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`grid gap-1.5 ${className ?? ""}`}>
      <Label>{label}</Label>
      {children}
    </div>
  );
}
