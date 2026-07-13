import { useMemo, useState } from "react";
import { TopNav } from "./components/TopNav";
import { AiBanner } from "./components/AiBanner";
import { ChannelBar } from "./components/ChannelBar";
import { FiltersToolbar, type Filters } from "./components/FiltersToolbar";
import { JobGrid } from "./components/JobGrid";
import { JobDetailDrawer } from "./components/JobDetailDrawer";
import { AnalyticsPage } from "./components/AnalyticsPage";
import { Footer } from "./components/Footer";
import {
  useChannels,
  useFeedback,
  useJobs,
  useRefreshChannel,
  useStatus,
} from "./hooks";
import type { Job } from "./api/types";

export default function App() {
  const [page, setPage] = useState<"jobs" | "analytics">("jobs");
  const [activeChannelId, setActiveChannelId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Job | null>(null);
  const [filters, setFilters] = useState<Filters>({
    search: "",
    remoteOnly: false,
    minScore: 0,
    saved: "all",
  });

  const status = useStatus();
  const channels = useChannels();
  const jobs = useJobs(activeChannelId);
  const feedback = useFeedback();
  const refresh = useRefreshChannel();

  const analysisMap = jobs.data?.analysis ?? {};
  const feedbackMap = jobs.data?.feedback ?? {};

  const filtered = useMemo(() => {
    const all = jobs.data?.jobs ?? [];
    const q = filters.search.trim().toLowerCase();
    return all.filter((job) => {
      if (filters.remoteOnly && !job.is_remote) return false;
      const score = analysisMap[job.job_url]?.relevance_score ?? 0;
      if (score < filters.minScore) return false;
      const verdict = feedbackMap[job.job_url]?.verdict;
      if (filters.saved === "liked" && verdict !== "like") return false;
      if (filters.saved === "hidden" && verdict !== "dislike") return false;
      if (filters.saved === "all" && verdict === "dislike") return false;
      if (q) {
        const hay = `${job.title} ${job.company} ${job.location}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [jobs.data, filters, analysisMap, feedbackMap]);

  const totalCount = jobs.data?.jobs?.length ?? 0;

  const onLike = (job: Job) => {
    const current = feedbackMap[job.job_url]?.verdict;
    feedback.mutate({
      jobUrl: job.job_url,
      verdict: current === "like" ? null : "like",
      meta: { title: job.title, company: job.company ?? "", site: job.site },
    });
  };

  const onDismiss = (job: Job) => {
    feedback.mutate({
      jobUrl: job.job_url,
      verdict: "dislike",
      meta: { title: job.title, company: job.company ?? "", site: job.site },
    });
  };

  const onRefresh = () => {
    if (activeChannelId !== null) refresh.mutate(activeChannelId);
    else jobs.refetch();
  };

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav
        view={
          page === "analytics"
            ? "analytics"
            : filters.saved === "liked"
              ? "saved"
              : "all"
        }
        onNav={(v) => {
          if (v === "analytics") {
            setPage("analytics");
          } else {
            setPage("jobs");
            // Saved must show ALL favourites, not just the active channel's.
            if (v === "saved") setActiveChannelId(null);
            setFilters((f) => ({ ...f, saved: v === "saved" ? "liked" : "all" }));
          }
        }}
      />
      <main className="flex-1 max-w-[1280px] w-full mx-auto px-margin-page py-gutter space-y-gutter">
        {page === "analytics" ? (
          <AnalyticsPage />
        ) : (
          <>
        <AiBanner status={status.data} />

        <ChannelBar
          channels={channels.data?.channels ?? []}
          sites={channels.data?.sites ?? []}
          totalCount={totalCount}
          activeChannelId={activeChannelId}
          onSelect={setActiveChannelId}
        />

        <FiltersToolbar
          filters={filters}
          onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
          onRefresh={onRefresh}
          refreshing={refresh.isPending || jobs.isFetching}
        />

        {jobs.isError ? (
          <div className="bg-error-container border-thick border-black p-6 neo-shadow text-on-error-container uppercase text-meta-sm">
            Errore nel caricamento: {(jobs.error as Error).message}
          </div>
        ) : (
          <JobGrid
            jobs={filtered}
            analysis={analysisMap}
            feedback={feedbackMap}
            loading={jobs.isLoading}
            onOpen={setSelected}
            onLike={onLike}
            onDismiss={onDismiss}
          />
        )}
          </>
        )}
      </main>
      <Footer />

      {selected && (
        <JobDetailDrawer
          job={selected}
          analysis={analysisMap[selected.job_url]}
          feedback={feedbackMap[selected.job_url]}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
