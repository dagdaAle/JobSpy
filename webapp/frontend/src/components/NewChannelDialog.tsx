import { useState } from "react";
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
import { useCreateChannel } from "../hooks";
import { siteLabel } from "../lib/format";

const INITIAL = {
  name: "",
  site: "linkedin",
  search_term: "",
  location: "",
  distance_km: 50,
  results_wanted: 50,
  hours_old: 336,
  is_remote: false,
};

export function NewChannelDialog({
  open,
  onOpenChange,
  sites,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sites: string[];
}) {
  const create = useCreateChannel();
  const [form, setForm] = useState(INITIAL);
  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.search_term.trim()) return;
    create.mutate(
      { ...form, name: form.name.trim(), hours_old: form.hours_old || null },
      {
        onSuccess: (r) => {
          toast.success(`Canale creato: ${r.new_count} offerte trovate`);
          setForm(INITIAL);
          onOpenChange(false);
        },
      },
    );
  };

  const siteItems = sites.map((s) => ({ value: s, label: siteLabel(s) }));

  return (
    <Dialog open={open} onOpenChange={(o) => !create.isPending && onOpenChange(o)}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={submit} className="grid gap-5">
          <DialogHeader>
            <DialogTitle>Nuovo canale</DialogTitle>
            <DialogDescription>
              Un canale è una ricerca su un sito, aggiornata ogni mattina. La prima ricerca parte subito.
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
            <Field label="Dove">
              <Input
                placeholder="es. Verona, Veneto"
                value={form.location}
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
            <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 sm:col-span-2">
              <span className="text-sm">Solo offerte da remoto</span>
              <Switch checked={form.is_remote} onCheckedChange={(v) => set("is_remote", v)} />
            </label>
          </div>

          {create.isError && (
            <p className="text-sm text-destructive">{(create.error as Error).message}</p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={create.isPending}>
              Annulla
            </Button>
            <Button type="submit" disabled={create.isPending || !form.search_term.trim()}>
              {create.isPending && <Loader2 className="animate-spin" />}
              {create.isPending ? "Cerco le prime offerte…" : "Crea canale"}
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
