import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, ScrollText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import type { LogEntry } from "../api/types";
import { useLogs } from "../hooks";
import { formatDateTime, formatDuration, parseDate, siteDot, siteLabel, timeAgo } from "../lib/format";
import { EmptyState } from "./JobGrid";

const TRIGGER: Record<LogEntry["trigger"], string> = {
  scheduler: "Automatico",
  manual: "Manuale",
  create: "Nuovo canale",
  startup: "Avvio del servizio",
};

const KIND_LABEL: Record<string, string> = {
  analysis: "Analisi AI delle offerte",
  archive: "Uscite dal feed (senza giudizio)",
  purge: "Pulizia offerte vecchie",
};

export function LogsPage() {
  const { data, isLoading, isError, error } = useLogs();
  const [only, setOnly] = useState<"all" | "errors">("all");
  const logs = data?.logs ?? [];

  const stats = useMemo(() => {
    const weekAgo = Date.now() - 7 * 86_400_000;
    const week = logs.filter((l) => (parseDate(l.finished_at)?.getTime() ?? 0) >= weekAgo);
    return {
      last: logs[0],
      errors7d: week.filter((l) => l.status === "error").length,
      new7d: week.reduce((n, l) => n + (l.new_count || 0), 0),
      aiFailed7d: week.reduce((n, l) => n + (l.analysis_failed || 0), 0),
    };
  }, [logs]);

  const rows = only === "errors" ? logs.filter((l) => l.status === "error") : logs;

  if (isLoading) return <Skeleton className="h-96 rounded-xl" />;
  if (isError) {
    return (
      <EmptyState icon={<AlertTriangle />} title="Impossibile caricare il log">
        {(error as Error).message}
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat
          label="Ultimo aggiornamento"
          value={stats.last ? timeAgo(stats.last.finished_at) : "—"}
          hint={stats.last ? formatDateTime(stats.last.finished_at) : "ancora nessuno"}
        />
        <Stat label="Offerte nuove (7 giorni)" value={stats.new7d} />
        <Stat
          label="Errori (7 giorni)"
          value={stats.errors7d}
          tone={stats.errors7d > 0 ? "bad" : "good"}
        />
        <Stat
          label="Analisi AI fallite (7 giorni)"
          value={stats.aiFailed7d}
          tone={stats.aiFailed7d > 0 ? "bad" : "good"}
        />
      </div>

      <Card className="gap-0 py-0">
        <div className="flex items-center justify-between gap-4 border-b px-4 py-3">
          <div>
            <h2 className="font-medium">Registro aggiornamenti</h2>
            <p className="text-sm text-muted-foreground">
              Ogni ricerca dei canali, ogni giro di analisi AI e ogni uscita dal feed. Non viene mai cancellato.
            </p>
          </div>
          <Tabs value={only} onValueChange={(v) => setOnly(v as "all" | "errors")}>
            <TabsList>
              <TabsTrigger value="all">Tutti</TabsTrigger>
              <TabsTrigger value="errors">Solo errori</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {rows.length === 0 ? (
          <div className="p-6">
            <EmptyState icon={<ScrollText />} title={only === "errors" ? "Nessun errore" : "Ancora nessun evento"}>
              {only === "errors"
                ? "Tutti gli aggiornamenti registrati sono andati a buon fine."
                : "Il primo evento comparirà al prossimo aggiornamento dei canali."}
            </EmptyState>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Quando</TableHead>
                <TableHead>Evento</TableHead>
                <TableHead>Avvio</TableHead>
                <TableHead>Esito</TableHead>
                <TableHead className="pr-4 text-right">Durata</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((l) => (
                <TableRow key={l.id} className="align-top">
                  <TableCell className="pl-4 whitespace-nowrap text-muted-foreground tabular-nums">
                    {formatDateTime(l.finished_at)}
                  </TableCell>
                  <TableCell>
                    {l.kind !== "refresh" ? (
                      <span>{KIND_LABEL[l.kind] ?? l.kind}</span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <span className={cn("size-1.5 shrink-0 rounded-full", siteDot(l.site))} />
                        <span className="truncate">{l.channel_name}</span>
                        <span className="text-xs text-muted-foreground">{siteLabel(l.site)}</span>
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{TRIGGER[l.trigger] ?? l.trigger}</TableCell>
                  <TableCell className="whitespace-normal">
                    <Outcome log={l} />
                  </TableCell>
                  <TableCell className="pr-4 text-right text-muted-foreground tabular-nums">
                    {formatDuration(l.duration_ms)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}

function Outcome({ log: l }: { log: LogEntry }) {
  if (l.status === "running") {
    return (
      <Badge variant="secondary">
        <Loader2 className="animate-spin" /> In corso
        {l.kind === "analysis" && l.found ? ` · ${l.found} da analizzare` : ""}
      </Badge>
    );
  }
  if (l.status === "error") {
    return (
      <div className="space-y-1">
        <Badge variant="destructive">
          <AlertTriangle /> Errore
        </Badge>
        {l.kind === "analysis" && (
          <p className="text-xs text-muted-foreground">
            {l.analyzed} analizzate · {l.analysis_failed} fallite
          </p>
        )}
        {l.error && <p className="max-w-md font-mono text-xs break-words text-destructive">{l.error}</p>}
      </div>
    );
  }
  const parts =
    l.kind === "purge"
      ? [`${l.removed} rimosse`]
      : l.kind === "archive"
        ? [`${l.removed} archiviate`]
        : l.kind === "analysis"
          ? [
              `${l.analyzed} analizzate`,
              `${l.found} in coda`,
              l.analysis_failed ? `${l.analysis_failed} fallite` : null,
            ].filter(Boolean)
          : [
          `${l.new_count} nuove`,
          `${l.found} trovate`,
          l.analyzed ? `${l.analyzed} analizzate` : null,
          l.analysis_failed ? `${l.analysis_failed} analisi fallite` : null,
        ].filter(Boolean);
  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <CheckCircle2 className="size-3.5 text-score-high" />
      {parts.map((p, i) => (
        <span
          key={i}
          className={cn(
            i === 0 ? "text-foreground" : "text-muted-foreground",
            String(p).includes("fallite") && "text-destructive",
          )}
        >
          {p}
          {i < parts.length - 1 && <span className="ml-2 text-muted-foreground">·</span>}
        </span>
      ))}
    </span>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "good" | "bad";
}) {
  return (
    <Card className="gap-1 py-4">
      <CardContent className="px-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 text-2xl font-semibold tabular-nums",
            tone === "bad" && "text-destructive",
          )}
        >
          {value}
        </p>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
