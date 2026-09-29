import { api } from "./api/client";
import { ApplicationsPage } from "./components/ApplicationsPage";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, Heart, Inbox, SearchX, Sparkles, Trash2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AppHeader, type View } from "./components/AppHeader";
import { AnalyticsPage } from "./components/AnalyticsPage";
import { ChannelBar } from "./components/ChannelBar";
import { FiltersToolbar, type Filters } from "./components/FiltersToolbar";
import { EmptyState, JobGrid } from "./components/JobGrid";
import { JobDetailSheet } from "./components/JobDetailSheet";
import type { CardMode } from "./components/JobCard";
import { LogsPage } from "./components/LogsPage";
import { useChannels, useFeedback, useJobs, useLogs, useStatus } from "./hooks";
import type { Feedback, Job, Verdict } from "./api/types";
import { parseDate } from "./lib/format";

// Which verdict each job-list view shows. Liked and dismissed jobs leave the
// feed: the feed is only what is still to review.
const VIEW_VERDICT: Record<"feed" | "new" | "saved" | "dismissed" | "archived" | "applications", Verdict | null> = {
  feed: null,
  new: null,
  saved: "like",
  dismissed: "dislike",
  archived: null,
  applications: null,
};

const HEADINGS: Record<"feed" | "new" | "saved" | "dismissed" | "archived" | "applications", { title: string; hint: string }> = {
  archived: { title: "Archivio", hint: "Offerte uscite dal feed. Puoi recuperarle e valutarle di nuovo." },
  applications: { title: "Candidature", hint: "Stato, note e prossimi passi delle offerte che stai seguendo." },
  feed: {
    title: "Offerte da vedere",
    hint: "Con il cuore l'offerta passa nei Preferiti, con la X tra le Scartate. Le offerte senza giudizio né candidatura passano automaticamente in Archivio.",
  },
  new: { title: "Nuove", hint: "Trovate all'ultimo aggiornamento e non ancora valutate." },
  saved: { title: "Preferiti", hint: "Le offerte che hai messo da parte. Restano qui anche dopo l’archiviazione automatica." },
  dismissed: { title: "Scartate", hint: "Le copie riconosciute dello stesso annuncio restano scartate. Puoi rimetterle tra le offerte." },
};

const verdictOf = (fb: Record<string, Feedback>, job: Job) => fb[job.job_url]?.verdict ?? null;

export default function App() {
  const [view, setView] = useState<View>("feed");
  const [activeChannelId, setActiveChannelId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Job | null>(null);
  const [filters, setFilters] = useState<Filters>({
    search: "",
    remoteOnly: false,
    minScore: 0,
    sort: "recent",
  });

  const listView = view !== "analytics" && view !== "logs" && view !== "applications";
  // Channels only scope the "to review" views; saved/dismissed span everything.
  const channelScoped = (view === "feed" || view === "new") && activeChannelId !== null;

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

  const visible = useMemo(() => {
    if (!listView) return [];
    const want = VIEW_VERDICT[view];
    const q = filters.search.trim().toLowerCase();
    const out = (source.data?.jobs ?? []).filter((job) => {
      if (view !== "archived" && verdictOf(feedbackMap, job) !== want) return false;
      if ((view === "feed" || view === "new") && source.data?.applications?.[job.job_url]) return false;
      if (view === "new" && !job.is_new) return false;
      if (filters.remoteOnly && !job.is_remote) return false;
      const score = analysisMap[job.job_url]?.relevance_score ?? 0;
      if (score < filters.minScore) return false;
      if (q && !`${job.title} ${job.company} ${job.location}`.toLowerCase().includes(q)) return false;
      return true;
    });
    if (filters.sort === "score") {
      const s = (j: Job) => analysisMap[j.job_url]?.relevance_score ?? -1;
      out.sort((a, b) => s(b) - s(a));
    }
    return out;
  }, [listView, view, source.data, filters, analysisMap, feedbackMap]);

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
  const heading = listView ? HEADINGS[view] : null;
  const hasFilters = !!filters.search || filters.remoteOnly || filters.minScore > 0;

  return (
    <div className="min-h-screen">
      <AppHeader
        view={view}
        onNav={(v) => {
          setView(v);
          setSelected(null);
        }}
        counts={{ feed: counts.feed, new: counts.new, saved: counts.saved }}
        status={status.data}
        logErrors={recentLogErrors}
      />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
        {status.data && !status.data.analyzer_configured && listView && (
          <Alert>
            <AlertTriangle />
            <AlertTitle>Analisi AI non attiva</AlertTitle>
            <AlertDescription>
              Senza la chiave API DeepSeek le offerte non ricevono il punteggio di match.
            </AlertDescription>
          </Alert>
        )}

        {view === "analytics" && <AnalyticsPage />}
        {view === "logs" && <LogsPage />}
        {view === "applications" && <ApplicationsPage onOpen={setSelected} />}

        {heading && (
          <>
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">{heading.title}</h1>
              <p className="text-sm text-muted-foreground">{heading.hint}</p>
            </div>

            {(view === "feed" || view === "new") && (
              <ChannelBar
                channels={channels.data?.channels ?? []}
                sites={channels.data?.sites ?? []}
                allCount={counts.feed}
                activeChannelId={activeChannelId}
                onSelect={setActiveChannelId}
              />
            )}

            <FiltersToolbar
              filters={filters}
              onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
              onRefresh={() => source.refetch()}
              refreshing={source.isFetching}
              resultCount={visible.length}
            />

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
                onOpen={setSelected}
                onLike={onLike}
                onDismiss={onDismiss}
                onRestore={onRestore}
                empty={<ListEmpty view={view} filtered={hasFilters} />}
              />
            )}
          </>
        )}
      </main>

      <JobDetailSheet
        job={selected}
        analysis={selected ? analysisMap[selected.job_url] : undefined}
        mode={mode}
        onClose={() => setSelected(null)}
        onLike={onLike}
        onDismiss={onDismiss}
        onRestore={onRestore}
      />
    </div>
  );
}

function ListEmpty({ view, filtered }: { view: View; filtered: boolean }) {
  if (filtered) {
    return (
      <EmptyState icon={<SearchX />} title="Nessuna offerta con questi filtri">
        Prova ad abbassare il match minimo o a svuotare la ricerca.
      </EmptyState>
    );
  }
  if (view === "archived" || view === "applications") return (
    <EmptyState icon={<Inbox />} title={view === "archived" ? "Archivio vuoto" : "Nessuna candidatura"}>
      {view === "applications" ? "Apri un’offerta e salva lo stato della candidatura." : "Qui ritroverai le offerte archiviate automaticamente."}
    </EmptyState>
  );
  if (view === "saved")
    return (
      <EmptyState icon={<Heart />} title="Nessun preferito">
        Metti il cuore a un'offerta per ritrovarla qui.
      </EmptyState>
    );
  if (view === "dismissed")
    return (
      <EmptyState icon={<Trash2 />} title="Nessuna offerta scartata">
        Le offerte che scarti finiscono qui.
      </EmptyState>
    );
  if (view === "new")
    return (
      <EmptyState icon={<Sparkles />} title="Niente di nuovo">
        Hai già visto tutte le offerte dell'ultimo aggiornamento.
      </EmptyState>
    );
  return (
    <EmptyState icon={<Inbox />} title="Hai visto tutto">
      Nessuna offerta da valutare. Le prossime arrivano con l'aggiornamento di domattina.
    </EmptyState>
  );
}
