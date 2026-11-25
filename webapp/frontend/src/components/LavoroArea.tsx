import { api } from "../api/client";
import { ApplicationsPage } from "./ApplicationsPage";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  AlertTriangle, Archive, Bookmark, ChartColumn, Download, FileUser, Inbox, Loader2, Radio, RefreshCw, ScrollText, Search,
  SearchX, Send, SlidersHorizontal, Sparkles, Wifi, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { type Area, type View } from "./AppHeader";
import { AnalyticsPage } from "./AnalyticsPage";
import { ChannelBar } from "./ChannelBar";
import { EmptyState, JobGrid } from "./JobGrid";
import { JobDetailSheet } from "./JobDetailSheet";
import type { CardMode } from "./JobCard";
import { LogsPage } from "./LogsPage";
import { CvPage } from "./CvPage";
import { FreehireSearch } from "./FreehireSearch";
import { AppShell, type NavGroup } from "./shell/AppShell";
import { FilterBar, RangeField, SelectField, TextField } from "./shell/FilterBar";
import { FacetGroup, Facets, toggle } from "./shell/Facets";
import { StatusBanner } from "./FeedSection";
import { jobDecision, type DecisionKey } from "./decision";
import { useChannels, useFeedback, useJobs, useLogs, useStatus } from "../hooks";
import type { Feedback, Job, Verdict } from "../api/types";
import { parseDate, yearlySalary } from "../lib/format";

type ListView = "feed" | "new" | "saved" | "dismissed" | "archived" | "applications";
type SortKey = "recent" | "score";
type ModeKey = "all" | "remote" | "remote_or_hybrid";

// Which verdict each job-list view shows. Liked and dismissed jobs leave the
// feed: the feed is only what is still to review.
const VIEW_VERDICT: Record<ListView, Verdict | null> = {
  feed: null,
  new: null,
  saved: "like",
  dismissed: "dislike",
  archived: null,
  applications: null,
};

const HEADINGS: Record<ListView, { title: string; hint: string }> = {
  archived: { title: "Archivio", hint: "Offerte uscite dal feed. Puoi recuperarle e valutarle di nuovo." },
  applications: { title: "Candidature", hint: "Stato, note e prossimi passi delle offerte che stai seguendo." },
  feed: {
    title: "Offerte",
    hint: "Prima quelle a cui candidarti, poi quelle da valutare. Segnalibro = preferiti, X = scarta; dopo qualche giorno senza giudizio passano in Archivio.",
  },
  new: { title: "Nuove", hint: "Trovate all'ultimo aggiornamento e non ancora valutate." },
  saved: { title: "Preferiti", hint: "Le offerte che hai messo da parte. Restano qui anche dopo l’archiviazione automatica." },
  dismissed: { title: "Scartate", hint: "Le copie riconosciute dello stesso annuncio restano scartate. Puoi rimetterle tra le offerte." },
};

const SECTIONS: { key: DecisionKey; title: string }[] = [
  { key: "candidati", title: "Da candidare oggi" },
  { key: "valuta", title: "Da valutare" },
  { key: "nonnoto", title: "Non noto" },
  { key: "lascia", title: "Lascia" },
];

const DECISIONS: { key: DecisionKey; label: string }[] = [
  { key: "candidati", label: "Candidati" },
  { key: "valuta", label: "Valuta" },
  { key: "lascia", label: "Lascia" },
  { key: "nonnoto", label: "Non noto" },
];
const DEFAULT_DECISIONS = new Set<DecisionKey>(["candidati", "valuta", "nonnoto"]);

const verdictOf = (fb: Record<string, Feedback>, job: Job) => fb[job.job_url]?.verdict ?? null;
const isList = (v: View): v is ListView => v in VIEW_VERDICT;
const eur = (v: number) => (v ? `${v.toLocaleString("it-IT")} €` : "qualsiasi");

export function LavoroArea({ onArea }: { onArea: (area: Area) => void }) {
  const [view, setView] = useState<View>(() => /^\d+$/.test(new URLSearchParams(window.location.search).get("cv") ?? "") ? "cvs" : "feed");
  const [activeChannelId, setActiveChannelId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Job | null>(null);
  const [search, setSearch] = useState("");
  const [workMode, setWorkMode] = useState<ModeKey>("all");
  const [sort, setSort] = useState<SortKey>("recent");
  const [minSalary, setMinSalary] = useState(0);
  const [decisions, setDecisions] = useState(DEFAULT_DECISIONS);

  const listView = isList(view) && view !== "applications";
  // Channels only scope the "to review" views; saved/dismissed span everything.
  const toReview = view === "feed" || view === "new";
  const channelScoped = toReview && activeChannelId !== null;

  const status = useStatus();
  const channels = useChannels();
  const allJobs = useJobs(null);
  const scopedJobs = useJobs(channelScoped ? activeChannelId : null);
  const extraJobs = useJobs(null, view === "archived" ? "archived" : view === "applications" ? "applications" : "active");
  const source = view === "archived" || view === "applications" ? extraJobs : channelScoped ? scopedJobs : allJobs;
  const logs = useLogs();
  const feedback = useFeedback();
  const qc = useQueryClient();
  const feedDays = status.data?.feed_days ?? 7;

  // New AI analyses land in the background: reload the lists when the backlog shrinks.
  const pending = status.data?.analysis_pending;
  const lastPending = useRef(pending);
  useEffect(() => {
    if (lastPending.current !== undefined && pending !== undefined && pending < lastPending.current) {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    }
    lastPending.current = pending;
  }, [pending, qc]);

  const analysisMap = source.data?.analysis ?? {};
  const feedbackMap = source.data?.feedback ?? {};

  const counts = useMemo(() => {
    const jobs = allJobs.data?.jobs ?? [];
    const fb = allJobs.data?.feedback ?? {};
    const tracked = allJobs.data?.applications ?? {};
    let feed = 0, fresh = 0, saved = 0;
    for (const j of jobs) {
      const v = verdictOf(fb, j);
      if (v === null && !tracked[j.job_url]) {
        feed++;
        if (j.is_new) fresh++;
      } else if (v === "like") saved++;
    }
    return { feed, new: fresh, saved };
  }, [allJobs.data]);

  // Everything but the decision facet: its counts must not depend on itself.
  const base = useMemo(() => {
    if (!listView) return [];
    const want = VIEW_VERDICT[view as ListView];
    const q = search.trim().toLowerCase();
    const out = (source.data?.jobs ?? []).filter((job) => {
      if (view !== "archived" && verdictOf(feedbackMap, job) !== want) return false;
      if (toReview && source.data?.applications?.[job.job_url]) return false;
      if (view === "new" && !job.is_new) return false;
      const mode = analysisMap[job.job_url]?.assessment?.work_mode;
      if (workMode === "remote" && !(job.is_remote || mode === "remote")) return false;
      if (workMode === "remote_or_hybrid" && !(job.is_remote || mode === "remote" || mode === "hybrid")) return false;
      // Unknown pay is not low pay: it stays.
      const pay = yearlySalary(job);
      if (minSalary && pay !== null && pay < minSalary) return false;
      if (q && !`${job.title} ${job.company} ${job.location}`.toLowerCase().includes(q)) return false;
      return true;
    });
    if (sort === "score") {
      const s = (j: Job) => analysisMap[j.job_url]?.relevance_score ?? -1;
      out.sort((a, b) => s(b) - s(a));
    }
    return out;
  }, [listView, view, toReview, source.data, search, workMode, minSalary, sort, analysisMap, feedbackMap]);

  const decisionCounts = useMemo(() => {
    const c: Partial<Record<DecisionKey, number>> = {};
    for (const j of base) { const d = jobDecision(analysisMap[j.job_url]); c[d] = (c[d] ?? 0) + 1; }
    return c;
  }, [base, analysisMap]);

  const visible = toReview ? base.filter((j) => decisions.has(jobDecision(analysisMap[j.job_url]))) : base;

  const recentLogErrors = useMemo(() => {
    const dayAgo = Date.now() - 86_400_000;
    return (logs.data?.logs ?? []).some(
      (l) => l.status === "error" && (parseDate(l.finished_at)?.getTime() ?? 0) >= dayAgo,
    );
  }, [logs.data]);

  // Set a verdict and offer an undo that restores the previous one.
  const setVerdict = (job: Job, verdict: Verdict | null, message: string) => {
    const previous = verdictOf(feedbackMap, job);
    const meta = { title: job.title, company: job.company ?? "", site: job.site };
    feedback.mutate({ jobUrl: job.job_url, verdict, meta });
    toast(message, {
      description: job.title,
      duration: 8000,
      action: {
        label: "Annulla",
        onClick: () => feedback.mutate({ jobUrl: job.job_url, verdict: previous, meta }),
      },
    });
  };
  const onLike = (job: Job) => setVerdict(job, "like", "Aggiunta ai preferiti");
  const onDismiss = (job: Job) => setVerdict(job, "dislike", "Offerta scartata");
  const onRestore = (job: Job) => {
    if (view === "archived") {
      api.restore(job.job_url).then(() => {
        qc.invalidateQueries({ queryKey: ["jobs"] });
        qc.invalidateQueries({ queryKey: ["analytics"] });
        toast.success("Offerta rimessa nel feed");
      }).catch((err: Error) => toast.error(err.message));
      return;
    }
    setVerdict(
      job,
      null,
      verdictOf(feedbackMap, job) === "like" ? "Tolta dai preferiti" : "Rimessa tra le offerte",
    );
  };

  const mode: CardMode = view === "archived" ? "archived" : view === "applications" ? "applications" : view === "saved" ? "saved" : view === "dismissed" ? "dismissed" : "feed";
  const heading = isList(view) && view !== "applications" ? HEADINGS[view] : null;
  const hasFilters = !!search || workMode !== "all" || minSalary > 0 || (toReview && decisions.size < DECISIONS.length);
  const resetFilters = () => { setSearch(""); setWorkMode("all"); setMinSalary(0); setDecisions(DEFAULT_DECISIONS); };
  const channelList = channels.data?.channels ?? [];

  const nav: NavGroup<View>[] = [
    { items: [
      { key: "feed", label: "Offerte", icon: <Inbox />, count: counts.feed },
      { key: "new", label: "Nuove", icon: <Sparkles />, count: counts.new },
      { key: "saved", label: "Preferiti", icon: <Bookmark />, count: counts.saved },
      { key: "dismissed", label: "Scartate", icon: <X /> },
      { key: "archived", label: "Archivio", icon: <Archive /> },
    ] },
    { label: "Candidature", items: [
      { key: "applications", label: "Candidature", icon: <Send /> },
      { key: "cvs", label: "CV", icon: <FileUser /> },
      { key: "freehire", label: "Cerca su freehire", icon: <Search /> },
    ] },
    { label: "Sistema", items: [
      { key: "analytics", label: "Analytics", icon: <ChartColumn /> },
      { key: "logs", label: "Log", icon: <ScrollText />, alert: recentLogErrors },
    ] },
  ];

  const filterBar = listView ? (
    <FilterBar>
      <SelectField
        icon={<Radio />}
        label="Canale"
        value={activeChannelId === null ? "all" : String(activeChannelId)}
        options={[{ value: "all", label: `Tutti i canali (${channelList.length})` }, ...channelList.map((c) => ({ value: String(c.id), label: c.name || c.search_term }))]}
        onChange={(v) => setActiveChannelId(v === "all" ? null : Number(v))}
      />
      <TextField icon={<Search />} label="Cerca" value={search} placeholder="Titolo, azienda, città…" onChange={setSearch} />
      <SelectField<ModeKey>
        icon={<Wifi />}
        label="Modalità"
        value={workMode}
        options={[{ value: "all", label: "Presenza, ibrido, remoto" }, { value: "remote_or_hybrid", label: "Ibrido o remoto" }, { value: "remote", label: "Solo remoto" }]}
        onChange={setWorkMode}
      />
      <SelectField<SortKey>
        icon={<SlidersHorizontal />}
        label="Ordina"
        value={sort}
        options={[{ value: "recent", label: "Più recenti" }, { value: "score", label: "Più adatte a me" }]}
        onChange={setSort}
      />
      <RangeField label="RAL minima" value={minSalary} min={0} max={80000} step={5000} format={eur} onChange={setMinSalary} accent="accent-area-lavoro" />
    </FilterBar>
  ) : undefined;

  const facets = toReview ? (
    <Facets onReset={hasFilters ? resetFilters : undefined}>
      <FacetGroup
        title="Decisione"
        options={DECISIONS.map((d) => ({ ...d, count: decisionCounts[d.key] ?? 0 }))}
        selected={decisions}
        onToggle={(k) => setDecisions((s) => toggle(s, k))}
      />
    </Facets>
  ) : undefined;

  return (
    <AppShell
      area="lavoro"
      onArea={onArea}
      status={status.data}
      nav={nav}
      active={view}
      onNav={(v) => { setView(v); setSelected(null); }}
      filterBar={filterBar}
      facets={facets}
    >
      {listView && status.data && !status.data.analyzer_configured && (
        <StatusBanner kind="warn" icon={<AlertTriangle />} title="LLM non configurato">
          Le offerte arrivano ma senza decisione né motivo: manca la chiave API DeepSeek nelle variabili del server.
        </StatusBanner>
      )}
      {listView && recentLogErrors && (
        <StatusBanner kind="error" icon={<AlertTriangle />} title="Un canale non si è aggiornato"
          action={<Button variant="outline" size="sm" onClick={() => setView("logs")}>Apri il log</Button>}>
          Errori nelle ultime 24 ore. Gli altri canali sono aggiornati.
        </StatusBanner>
      )}
      {toReview && status.data?.analyzer_configured && (pending ?? 0) > 0 && (
        <StatusBanner kind="info" icon={<Loader2 className="animate-spin" />} title={`Analisi in corso · ${pending} in coda`}>
          Le offerte appena arrivate restano «Non noto» finché l’AI non le ha lette.
        </StatusBanner>
      )}

      {view === "analytics" && <AnalyticsPage />}
      {view === "logs" && <LogsPage />}
      {view === "cvs" && <CvPage />}
      {view === "freehire" && <FreehireSearch />}
      {view === "applications" && <ApplicationsPage onOpen={setSelected} />}

      {heading && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="space-y-1">
              <h1 className="font-heading text-3xl font-semibold">{heading.title}</h1>
              <p className="max-w-3xl text-sm text-muted-foreground">{heading.hint}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-muted-foreground">{visible.length} {visible.length === 1 ? "offerta" : "offerte"}</span>
              <Button variant="outline" size="icon" onClick={() => source.refetch()} aria-label="Ricarica" className="size-9">
                <RefreshCw className={source.isFetching ? "animate-spin" : ""} />
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="outline" size="icon" aria-label="Esporta" className="size-9" />}>
                  <Download />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem render={<a href={api.exportUrl("csv")} />}>Esporta CSV</DropdownMenuItem>
                  <DropdownMenuItem render={<a href={api.exportUrl("xlsx")} />}>Esporta Excel</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {toReview && (
            <ChannelBar
              channels={channelList}
              sites={channels.data?.sites ?? []}
              allCount={counts.feed}
              activeChannelId={activeChannelId}
              onSelect={setActiveChannelId}
            />
          )}

          {source.isError ? (
            <EmptyState icon={<AlertTriangle />} title="Errore nel caricamento">
              {(source.error as Error).message}
            </EmptyState>
          ) : (
            <JobGrid
              jobs={visible}
              analysis={analysisMap}
              mode={mode}
              feedDays={feedDays}
              loading={source.isLoading}
              sections={toReview ? SECTIONS : undefined}
              onOpen={setSelected}
              onLike={onLike}
              onDismiss={onDismiss}
              onRestore={onRestore}
              empty={<ListEmpty view={view as ListView} filtered={hasFilters} noChannels={!channels.isLoading && channelList.length === 0} onReset={resetFilters} />}
            />
          )}
        </>
      )}

      <JobDetailSheet
        job={selected}
        analysis={selected ? analysisMap[selected.job_url] : undefined}
        mode={mode}
        onClose={() => setSelected(null)}
        onLike={onLike}
        onDismiss={onDismiss}
        onRestore={onRestore}
      />
    </AppShell>
  );
}

function ListEmpty({ view, filtered, noChannels, onReset }: { view: ListView; filtered: boolean; noChannels: boolean; onReset: () => void }) {
  if (filtered) {
    return (
      <EmptyState icon={<SearchX />} title="Nessuna offerta con questi filtri" action={<Button onClick={onReset}><X /> Azzera filtri</Button>}>
        Togli un filtro o azzera tutto.
      </EmptyState>
    );
  }
  if ((view === "feed" || view === "new") && noChannels)
    return (
      <EmptyState icon={<Radio />} title="Nessun canale">
        Un canale è una ricerca salvata che gira ogni mattina. Crealo dalla barra dei canali qui sopra.
      </EmptyState>
    );
  if (view === "archived")
    return <EmptyState icon={<Archive />} title="Archivio vuoto">Qui ritroverai le offerte archiviate automaticamente.</EmptyState>;
  if (view === "saved")
    return <EmptyState icon={<Bookmark />} title="Nessun preferito">Usa il segnalibro su un’offerta per ritrovarla qui.</EmptyState>;
  if (view === "dismissed")
    return <EmptyState icon={<X />} title="Nessuna offerta scartata">Le offerte che scarti finiscono qui.</EmptyState>;
  if (view === "new")
    return <EmptyState icon={<Sparkles />} title="Niente di nuovo">Hai già visto tutte le offerte dell'ultimo aggiornamento.</EmptyState>;
  return (
    <EmptyState icon={<Inbox />} title="Niente da decidere oggi">
      Le prossime offerte arrivano con l'aggiornamento di domattina. Le «Lascia» sono nei filtri.
    </EmptyState>
  );
}
