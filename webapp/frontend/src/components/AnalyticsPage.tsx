import { Icon } from "./Icon";
import { useAnalytics } from "../hooks";
import type { Count } from "../api/types";

export function AnalyticsPage() {
  const { data, isLoading, isError, error } = useAnalytics();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-28 bg-surface-container border-thick border-black neo-shadow animate-pulse" />
        ))}
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className="bg-error-container border-thick border-black p-6 neo-shadow text-on-error-container uppercase text-meta-sm">
        Errore analytics: {(error as Error)?.message ?? "dati non disponibili"}
      </div>
    );
  }

  const k = data.kpis;
  const sal = data.salary;
  const cur = sal.currency && sal.currency !== "?" ? sal.currency : "€";
  const fmtK = (n?: number) => (n == null ? "—" : `${cur} ${Math.round(n / 1000)}K`);

  return (
    <div className="space-y-gutter">
      {/* KPI header */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <Stat label="Job totali" value={k.total} icon="database" accent="text-primary-fixed" />
        <Stat label="Nuovi 7gg" value={k.new_7d} icon="fiber_new" accent="text-secondary-fixed" />
        <Stat label="% Remote" value={`${k.remote_pct}%`} icon="public" accent="text-primary-fixed" />
        <Stat
          label="AI score medio"
          value={k.avg_score == null ? "—" : `${k.avg_score}%`}
          icon="neurology"
          accent="text-secondary-fixed"
        />
        <Stat label="Analizzati" value={k.analyzed} icon="check_circle" accent="text-on-surface" />
        <Stat label="Preferiti" value={k.favorites} icon="favorite" accent="text-secondary-fixed" />
        <Stat label="Scartati" value={k.dismissed} icon="block" accent="text-error" />
        <Stat label="Canali" value={k.channels} icon="rss_feed" accent="text-primary-fixed" />
      </section>

      {/* Salary */}
      <Panel title="Stipendi" subtitle={`${sal.count} annunci con RAL`}>
        {sal.count === 0 ? (
          <Empty text="Nessun dato salariale negli annunci raccolti." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 grid grid-cols-3 gap-3">
              <MiniStat label="Min" value={fmtK(sal.min)} />
              <MiniStat label="Mediana" value={fmtK(sal.median)} highlight />
              <MiniStat label="Max" value={fmtK(sal.max)} />
            </div>
            <div className="lg:col-span-2">
              <BarList
                items={(sal.buckets ?? []).map((b) => ({ name: b.range, count: b.count }))}
                barClass="bg-primary-fixed"
              />
            </div>
          </div>
        )}
      </Panel>

      {/* Market intelligence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-gutter">
        <Panel title="Skill più richieste" subtitle="da annunci + tag AI">
          <BarList items={data.top_skills} barClass="bg-secondary-fixed" />
        </Panel>
        <Panel title="Aziende più attive" subtitle="per numero di annunci">
          <BarList items={data.top_companies} barClass="bg-primary-fixed" />
        </Panel>
        <Panel title="Settori" subtitle="industry degli annunci">
          <BarList items={data.top_industries} barClass="bg-tertiary-container" textOnBar="text-on-tertiary-container" />
        </Panel>
        <Panel title="Remote vs On-site" subtitle="per sorgente">
          <div className="space-y-3">
            {data.remote_by_site.map((s) => {
              const tot = s.remote + s.onsite || 1;
              return (
                <div key={s.site}>
                  <div className="flex justify-between text-meta-xs uppercase mb-1">
                    <span className="text-on-surface">{s.site}</span>
                    <span className="text-outline">
                      {Math.round((s.remote / tot) * 100)}% remote
                    </span>
                  </div>
                  <div className="flex h-6 border-thin border-black">
                    <div
                      className="bg-primary-fixed h-full"
                      style={{ width: `${(s.remote / tot) * 100}%` }}
                    />
                    <div
                      className="bg-surface-container-highest h-full"
                      style={{ width: `${(s.onsite / tot) * 100}%` }}
                    />
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

function Stat({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number | string;
  icon: string;
  accent: string;
}) {
  return (
    <div className="bg-surface-container border-thick border-black p-4 neo-shadow flex flex-col justify-between h-full">
      <div className="flex items-center justify-between">
        <span className="text-meta-xs uppercase text-outline">{label}</span>
        <Icon name={icon} className={`${accent} text-base`} />
      </div>
      <span className={`text-headline-lg font-black mt-2 ${accent}`}>{value}</span>
    </div>
  );
}

function MiniStat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`border-thin border-black p-3 flex flex-col ${
        highlight ? "bg-secondary-fixed text-on-secondary-fixed" : "bg-black/40"
      }`}
    >
      <span className={`text-meta-xs uppercase ${highlight ? "" : "text-outline"}`}>{label}</span>
      <span className="text-headline-md font-black">{value}</span>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-surface border-thick border-black p-6 neo-shadow">
      <div className="flex items-baseline justify-between mb-4 border-b-thin border-black pb-2">
        <h3 className="text-headline-md uppercase">{title}</h3>
        {subtitle && <span className="text-meta-xs uppercase text-outline">{subtitle}</span>}
      </div>
      {children}
    </section>
  );
}

function BarList({
  items,
  barClass,
  textOnBar = "text-on-primary-fixed",
}: {
  items: Count[];
  barClass: string;
  textOnBar?: string;
}) {
  if (!items.length) return <Empty text="Nessun dato disponibile." />;
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <div className="space-y-2">
      {items.map((it) => (
        <div key={it.name} className="flex items-center gap-3">
          <span className="w-28 shrink-0 text-meta-xs uppercase text-on-surface-variant truncate" title={it.name}>
            {it.name}
          </span>
          <div className="flex-1 h-6 bg-surface-container-lowest border-thin border-black">
            <div
              className={`${barClass} h-full flex items-center justify-end pr-2`}
              style={{ width: `${Math.max((it.count / max) * 100, 6)}%` }}
            >
              <span className={`text-[10px] font-black ${textOnBar}`}>{it.count}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-body-md text-on-surface-variant py-4">{text}</p>;
}
