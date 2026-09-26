import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Count } from "../api/types";
import { useAnalytics } from "../hooks";
import { siteLabel } from "../lib/format";
import { EmptyState } from "./JobGrid";

export function AnalyticsPage() {
  const { data, isLoading, isError, error } = useAnalytics();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    );
  }
  if (isError || !data) {
    return (
      <EmptyState icon={<AlertTriangle />} title="Analytics non disponibili">
        {(error as Error)?.message ?? "Dati non disponibili."}
      </EmptyState>
    );
  }

  const k = data.kpis;
  const sal = data.salary;
  const cur = sal.currency && sal.currency !== "?" ? sal.currency : "€";
  const fmtK = (n?: number) => (n == null ? "—" : `${cur} ${Math.round(n / 1000)}k`);

  return (
    <div className="space-y-6">
      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Offerte salvate" value={k.total} />
        <Stat label="Nuove negli ultimi 7 giorni" value={k.new_7d} />
        <Stat label="Da remoto" value={`${k.remote_pct}%`} />
        <Stat label="Match medio AI" value={k.avg_score == null ? "—" : `${k.avg_score}%`} />
        <Stat label="Analizzate dall'AI" value={k.analyzed} />
        <Stat label="Preferite" value={k.favorites} />
        <Stat label="Scartate" value={k.dismissed} />
        <Stat label="Canali" value={k.channels} />
      </section>

      <Panel title="Retribuzioni" subtitle={`${sal.count} annunci indicano la RAL`}>
        {sal.count === 0 ? (
          <p className="text-sm text-muted-foreground">Nessun dato sulla retribuzione negli annunci raccolti.</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="grid grid-cols-3 gap-3 self-start">
              <MiniStat label="Minima" value={fmtK(sal.min)} />
              <MiniStat label="Mediana" value={fmtK(sal.median)} highlight />
              <MiniStat label="Massima" value={fmtK(sal.max)} />
            </div>
            <div className="lg:col-span-2">
              <BarList items={(sal.buckets ?? []).map((b) => ({ name: b.range, count: b.count }))} />
            </div>
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Competenze più richieste" subtitle="dagli annunci e dai tag dell'AI">
          <BarList items={data.top_skills} />
        </Panel>
        <Panel title="Aziende più attive" subtitle="per numero di annunci">
          <BarList items={data.top_companies} />
        </Panel>
        <Panel title="Settori" subtitle="settore dichiarato dall'azienda">
          <BarList items={data.top_industries} />
        </Panel>
        <Panel title="Remoto e in sede" subtitle="per sito">
          <div className="space-y-4">
            {data.remote_by_site.map((s) => {
              const tot = s.remote + s.onsite || 1;
              const pct = Math.round((s.remote / tot) * 100);
              return (
                <div key={s.site} className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span>{siteLabel(s.site)}</span>
                    <span className="text-muted-foreground tabular-nums">{pct}% da remoto</span>
                  </div>
                  <div className="flex h-2 overflow-hidden rounded-full bg-muted">
                    <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <Card className="gap-1 py-4">
      <CardContent className="px-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 ${highlight ? "border-primary/30 bg-primary/10" : ""}`}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {subtitle && <CardDescription>{subtitle}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function BarList({ items }: { items: Count[] }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">Nessun dato disponibile.</p>;
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <div className="space-y-2">
      {items.map((it) => (
        <div key={it.name} className="flex items-center gap-3 text-sm">
          <span className="w-32 shrink-0 truncate text-muted-foreground" title={it.name}>
            {it.name}
          </span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary/80"
              style={{ width: `${Math.max((it.count / max) * 100, 3)}%` }}
            />
          </div>
          <span className="w-8 text-right tabular-nums">{it.count}</span>
        </div>
      ))}
    </div>
  );
}
