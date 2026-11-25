// Page frame shared by the three areas: black header (+ optional filter bar), sidebar with the views and the
// facet filters, content. Below 768 px the sidebar becomes a bottom bar and the facets go away.
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { StatusResponse } from "../../api/types";
import { AppHeader, areaInfo, type Area } from "../AppHeader";

export interface NavItem<K extends string> {
  key: K;
  label: string;
  icon: ReactNode;
  count?: number | string;
  alert?: boolean;
}

export interface NavGroup<K extends string> {
  label?: string;
  items: NavItem<K>[];
}

interface Props<K extends string> {
  area: Area;
  onArea: (area: Area) => void;
  status?: StatusResponse;
  nav: NavGroup<K>[];
  active: K;
  onNav: (key: K) => void;
  filterBar?: ReactNode;
  facets?: ReactNode;
  children: ReactNode;
}

export function AppShell<K extends string>({ area, onArea, status, nav, active, onNav, filterBar, facets, children }: Props<K>) {
  const a = areaInfo(area);
  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <header className="bg-header">
        <AppHeader area={area} onArea={onArea} status={status} />
        {filterBar}
      </header>

      <div className="flex min-h-[calc(100dvh-4rem)]">
        <aside className="hidden w-66 shrink-0 border-r bg-card md:block">
          <div className="sticky top-0 max-h-screen space-y-6 overflow-y-auto py-6 pr-4 pl-6">
            {nav.map((g, i) => (
              <nav key={i} aria-label={g.label ?? "Viste"} className="space-y-0.5">
                {g.label && <p className="px-0 pb-1 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">{g.label}</p>}
                {g.items.map((it) => {
                  const on = it.key === active;
                  return (
                    <button
                      key={it.key}
                      type="button"
                      onClick={() => onNav(it.key)}
                      aria-current={on ? "page" : undefined}
                      className={cn(
                        "flex h-10 w-full items-center gap-2.5 rounded-md px-3 text-left text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 [&_svg]:size-4",
                        on ? cn(a.soft, a.accent, "font-semibold") : "font-medium text-foreground hover:bg-muted",
                      )}
                    >
                      <span className={on ? undefined : "text-muted-foreground"}>{it.icon}</span>
                      <span className="flex-1 truncate">{it.label}</span>
                      {it.alert && <span className="size-2 rounded-full bg-destructive" aria-label="errori recenti" />}
                      {it.count != null && it.count !== 0 && (
                        <span className={cn("font-mono text-xs font-medium", on ? undefined : "text-muted-foreground")}>
                          {typeof it.count === "number" ? it.count.toLocaleString("it-IT") : it.count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            ))}
            {facets && (
              <>
                <div className="h-px bg-border" />
                {facets}
              </>
            )}
          </div>
        </aside>

        <main className="min-w-0 flex-1 space-y-5 px-4 py-6 sm:px-8">{children}</main>
      </div>

      <MobileNav nav={nav} active={active} onNav={onNav} soft={a.soft} accent={a.accent} />
    </div>
  );
}

function MobileNav<K extends string>({ nav, active, onNav, soft, accent }: { nav: NavGroup<K>[]; active: K; onNav: (k: K) => void; soft: string; accent: string }) {
  const items = nav.flatMap((g) => g.items);
  return (
    <nav aria-label="Viste" className="fixed inset-x-0 bottom-0 z-40 flex gap-1 overflow-x-auto border-t bg-card px-2 pt-1.5 pb-[max(0.75rem,env(safe-area-inset-bottom))] md:hidden">
      {items.map((it) => {
        const on = it.key === active;
        return (
          <button
            key={it.key}
            type="button"
            onClick={() => onNav(it.key)}
            aria-current={on ? "page" : undefined}
            className={cn(
              "relative flex min-h-13 min-w-17 shrink-0 flex-col items-center justify-center gap-1 rounded-md px-1 text-[11px] [&_svg]:size-5",
              on ? cn(soft, accent, "font-semibold") : "font-medium text-muted-foreground",
            )}
          >
            {it.icon}
            <span className="max-w-16 truncate">{it.label}</span>
            {it.alert && <span className="absolute top-1.5 right-4 size-2 rounded-full bg-destructive" />}
          </button>
        );
      })}
    </nav>
  );
}
