import { AlertTriangle, Briefcase, Gavel, Landmark, Loader2, Moon, Sparkles, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { StatusResponse } from "../api/types";
import { Logo } from "./shell/Logo";

export type Area = "lavoro" | "pa" | "gare";

export const AREAS: { area: Area; label: string; short: string; icon: ReactNode; accent: string; soft: string }[] = [
  { area: "lavoro", label: "Lavoro", short: "Lavoro", icon: <Briefcase />, accent: "text-area-lavoro", soft: "bg-area-lavoro-soft" },
  { area: "pa", label: "Concorsi PA", short: "PA", icon: <Landmark />, accent: "text-area-pa", soft: "bg-area-pa-soft" },
  { area: "gare", label: "Gare P.IVA", short: "Gare", icon: <Gavel />, accent: "text-area-gare", soft: "bg-area-gare-soft" },
];

export const areaInfo = (area: Area) => AREAS.find((a) => a.area === area)!;

/** Small "area" label above a dialog title: icon and name in the area accent. */
export function AreaLabel({ area }: { area: Area }) {
  const a = areaInfo(area);
  return <span className={cn("flex items-center gap-1.5 text-xs font-semibold [&_svg]:size-3.5", a.accent)}>{a.icon}{a.label}</span>;
}

export type View = "feed" | "new" | "saved" | "dismissed" | "archived" | "applications" | "freehire" | "cvs" | "analytics" | "logs" | "notifiche";

/** Black header: logo, area switch, AI status, theme. The views live in the sidebar. */
export function AppHeader({ area, onArea, status }: { area: Area; onArea: (area: Area) => void; status?: StatusResponse }) {
  return (
    <div className="flex h-16 items-center justify-between gap-3 px-4 sm:px-8">
      <div className="flex min-w-0 items-center gap-4 lg:gap-10">
        <Logo onDark />
        <nav aria-label="Area" className="flex gap-1">
          {AREAS.map((a) => {
            const on = a.area === area;
            return (
              <button
                key={a.area}
                type="button"
                onClick={() => onArea(a.area)}
                aria-current={on ? "page" : undefined}
                className={cn(
                  "flex h-10 items-center gap-2 rounded-full px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 sm:px-3.5 [&_svg]:size-4",
                  on ? "bg-header-field font-semibold text-header-foreground" : "font-medium text-header-muted hover:text-header-foreground",
                )}
              >
                <span className={on ? a.accent : undefined}>{a.icon}</span>
                <span className="sm:hidden">{a.short}</span>
                <span className="hidden sm:inline">{a.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
      <div className="flex items-center gap-2">
        {status && <AiStatus status={status} />}
        <ThemeToggle />
      </div>
    </div>
  );
}

function AiStatus({ status }: { status: StatusResponse }) {
  const ok = status.analyzer_configured && status.cv_loaded;
  const pending = status.analysis_pending;
  const text = ok
    ? `Analisi AI attiva su ogni offerta. CV caricato (${status.cv_chars.toLocaleString("it-IT")} caratteri).` +
      (pending ? ` ${pending} offerte in attesa di analisi.` : " Tutte le offerte sono analizzate.")
    : !status.analyzer_configured
      ? "Analisi AI non attiva: manca la chiave API DeepSeek."
      : "Analisi AI senza CV: monta un CV in PDF per calcolare il match.";
  return (
    <Tooltip>
      <TooltipTrigger
        render={<span className="hidden items-center gap-1.5 rounded-full bg-header-field px-3 py-1.5 text-xs font-medium sm:flex" />}
      >
        {!ok ? (
          <AlertTriangle className="size-3.5 text-deadline" />
        ) : pending > 0 ? (
          <Loader2 className="size-3.5 animate-spin text-header-muted" />
        ) : (
          <Sparkles className="size-3.5 text-header-muted" />
        )}
        <span className={ok ? "text-header-muted" : "text-header-foreground"}>
          {!ok ? (status.analyzer_configured ? "AI senza CV" : "AI non configurata") : pending > 0 ? `AI: ${pending} in coda` : "AI attiva"}
        </span>
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
            className="size-9 bg-header-field text-header-foreground hover:bg-header-field hover:text-header-foreground"
          />
        }
      >
        {dark ? <Sun /> : <Moon />}
      </TooltipTrigger>
      <TooltipContent>{dark ? "Tema chiaro" : "Tema scuro"}</TooltipContent>
    </Tooltip>
  );
}
