import { Moon, Search, Sparkles, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { StatusResponse } from "../api/types";

export type View = "feed" | "new" | "saved" | "dismissed" | "analytics" | "logs";

const NAV: { view: View; label: string }[] = [
  { view: "feed", label: "Offerte" },
  { view: "new", label: "Nuove" },
  { view: "saved", label: "Preferiti" },
  { view: "dismissed", label: "Scartate" },
  { view: "analytics", label: "Analytics" },
  { view: "logs", label: "Log" },
];

interface Props {
  view: View;
  onNav: (view: View) => void;
  counts: Partial<Record<View, number>>;
  status?: StatusResponse;
  logErrors?: boolean;
}

export function AppHeader({ view, onNav, counts, status, logErrors }: Props) {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <div className="flex items-center gap-2 font-semibold">
          <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Search className="size-4" strokeWidth={2.5} />
          </span>
          JobSpy
        </div>

        <nav className="-mb-px flex h-full min-w-0 flex-1 gap-1 overflow-x-auto">
          {NAV.map(({ view: v, label }) => {
            const active = v === view;
            const count = counts[v];
            return (
              <button
                key={v}
                type="button"
                onClick={() => onNav(v)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 border-b-2 px-2.5 text-sm transition-colors outline-none focus-visible:text-foreground",
                  active
                    ? "border-primary font-medium text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                {label}
                {count != null && count > 0 && (
                  <span
                    className={cn(
                      "rounded-full px-1.5 text-[11px] leading-4 tabular-nums",
                      active ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground",
                    )}
                  >
                    {count}
                  </span>
                )}
                {v === "logs" && logErrors && (
                  <span className="size-1.5 rounded-full bg-destructive" aria-label="errori recenti" />
                )}
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-1">
          {status && <AiStatus status={status} />}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function AiStatus({ status }: { status: StatusResponse }) {
  const ok = status.analyzer_configured && status.cv_loaded;
  const text = ok
    ? `Analisi AI attiva: CV caricato (${status.cv_chars.toLocaleString("it-IT")} caratteri), max ${status.max_analysis_per_search} offerte per aggiornamento.`
    : !status.analyzer_configured
      ? "Analisi AI non attiva: manca la chiave API DeepSeek."
      : "Analisi AI senza CV: monta un CV in PDF per calcolare il match.";
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            className={cn(
              "hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-xs sm:flex",
              ok ? "text-muted-foreground" : "bg-destructive/10 text-destructive",
            )}
          />
        }
      >
        <Sparkles className="size-3.5" />
        {ok ? "AI attiva" : "AI non attiva"}
      </TooltipTrigger>
      <TooltipContent className="max-w-64">{text}</TooltipContent>
    </Tooltip>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            aria-label={dark ? "Tema chiaro" : "Tema scuro"}
            onClick={() => setTheme(dark ? "light" : "dark")}
          />
        }
      >
        {dark ? <Sun /> : <Moon />}
      </TooltipTrigger>
      <TooltipContent>{dark ? "Tema chiaro" : "Tema scuro"}</TooltipContent>
    </Tooltip>
  );
}
