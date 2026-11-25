import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { api } from "../api/client";
import type { FreehireResult, Job } from "../api/types";
import { salaryLabel } from "../lib/format";
import { EmptyState } from "./JobGrid";

/** Search freehire without a channel; only the results Ale saves enter the DB. */
export function FreehireSearch() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ q: "", location: "Italia", remote: false, days: 7 });
  const [results, setResults] = useState<FreehireResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);

  const search = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.q.trim()) return;
    setLoading(true);
    api.freehireSearch({ ...form, q: form.q.trim() })
      .then((r) => setResults(r.results))
      .catch((err: Error) => toast.error(err.message))
      .finally(() => setLoading(false));
  };

  const save = (r: FreehireResult) => {
    setSaving(r.slug);
    api.freehireSave(r.slug)
      .then(() => {
        toast.success("Offerta salvata nel feed");
        setResults((rs) => rs?.map((x) => (x.slug === r.slug ? { ...x, in_db: true } : x)) ?? null);
        qc.invalidateQueries({ queryKey: ["jobs"] });
      })
      .catch((err: Error) => toast.error(err.message))
      .finally(() => setSaving(null));
  };

  return (
    <section className="space-y-4">
      <form onSubmit={search} className="grid gap-3 sm:grid-cols-[2fr_1fr_auto_auto_auto] sm:items-end">
        <div className="grid gap-1.5">
          <Label htmlFor="fh-q">Cosa cerchi</Label>
          <Input id="fh-q" autoFocus placeholder="es. AI engineer" value={form.q}
            onChange={(e) => setForm({ ...form, q: e.target.value })} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="fh-loc">Zona</Label>
          <Input id="fh-loc" placeholder="Italia, Europa, una città o vuoto" value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="fh-days">Ultimi giorni</Label>
          <Input id="fh-days" type="number" min={0} max={60} className="w-24" value={form.days}
            onChange={(e) => setForm({ ...form, days: Number(e.target.value) })} />
        </div>
        <label className="flex h-9 items-center gap-2 text-sm">
          <Switch checked={form.remote} onCheckedChange={(v) => setForm({ ...form, remote: v })} /> Solo remoto
        </label>
        <Button type="submit" disabled={loading || !form.q.trim()}>
          {loading ? <Loader2 className="animate-spin" /> : <Search />} Cerca
        </Button>
      </form>

      {results === null ? (
        <EmptyState icon={<Search />} title="Cerca su freehire">
          Offerte dai siti di candidatura delle aziende e da LinkedIn. Niente viene salvato finché non premi «Salva».
        </EmptyState>
      ) : results.length === 0 ? (
        <EmptyState icon={<Search />} title="Nessun risultato">Prova una parola chiave o una zona più ampia.</EmptyState>
      ) : (
        <ul className="grid gap-2">
          {results.map((r) => {
            const salary = salaryLabel(r as unknown as Job);
            return (
              <li key={r.slug}>
                <Card>
                  <CardContent className="flex flex-wrap items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <a href={r.job_url} target="_blank" rel="noreferrer" className="font-medium hover:underline">{r.title}</a>
                      <p className="truncate text-sm text-muted-foreground">
                        {[r.company, r.location, r.is_remote ? "remoto" : null, r.origin, r.posted_at, salary].filter(Boolean).join(" · ")}
                      </p>
                    </div>
                    {r.suspect && <Badge variant="outline" className="border-amber-500 text-amber-700">Sospetta</Badge>}
                    {r.in_db ? (
                      <Badge variant="secondary">Già nel DB</Badge>
                    ) : (
                      <Button size="sm" variant="outline" disabled={saving === r.slug} onClick={() => save(r)}>
                        {saving === r.slug && <Loader2 className="animate-spin" />} Salva
                      </Button>
                    )}
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
