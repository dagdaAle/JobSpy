import { Building2, CalendarClock, ExternalLink, Heart, MapPin, Undo2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { AreaDecision, AreaItem, AreaView } from "../../api/areas";
import { timeAgo } from "../../lib/format";

const DAY = 86_400_000;

export const DECISION: Record<AreaDecision, { text: string; className: string }> = {
  adatto: { text: "Adatto", className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" },
  da_valutare: { text: "Da valutare", className: "bg-amber-500/15 text-amber-700 dark:text-amber-300" },
  non_adatto: { text: "Non adatto", className: "bg-muted text-muted-foreground" },
};

export interface MetaEntry {
  icon: React.ReactNode;
  text: string;
}

/** Calendar days from today to an ISO date (negative = past). */
function daysUntil(iso: string): number | null {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((new Date(y, m - 1, d).getTime() - today.getTime()) / DAY);
}

function Deadline({ iso }: { iso: string }) {
  const days = daysUntil(iso);
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const date = days === null ? iso : new Date(y, m - 1, d).toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });
  const soon = days !== null && days >= 0 && days <= 7;
  const left = days === null || days < 0 ? "" : days === 0 ? " · oggi" : days === 1 ? " · domani" : ` · tra ${days} g`;
  return (
    <Meta icon={<CalendarClock />} className={soon ? "font-medium text-amber-700 dark:text-amber-300" : undefined}>
      Scade il {date}{left}
    </Meta>
  );
}

interface Props {
  item: AreaItem;
  view: AreaView;
  sourceLabel: (source: string) => string;
  meta: MetaEntry[];
  facts: string[];
  onLike: () => void;
  onDismiss: () => void;
  onRestore: () => void;
}

export function ItemCard({ item, view, sourceLabel, meta, facts, onLike, onDismiss, onRestore }: Props) {
  const decision = item.decision ? DECISION[item.decision] : null;
  return (
    <article className="flex h-full flex-col rounded-xl border bg-card text-card-foreground shadow-xs transition-[border-color,box-shadow] hover:border-foreground/15 hover:shadow-md">
      <div className="flex flex-1 flex-col gap-4 p-5">
        <header className="min-w-0">
          <h3 className="line-clamp-3 font-medium leading-snug">{item.title}</h3>
          {item.buyer && (
            <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
              <Building2 className="size-3.5 shrink-0" />
              <span className="truncate">{item.buyer}</span>
            </p>
          )}
        </header>

        <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-muted-foreground">
          {item.deadline && <Deadline iso={item.deadline} />}
          {item.place && <Meta icon={<MapPin />}>{item.place}</Meta>}
          {meta.map((m) => (
            <Meta key={m.text} icon={m.icon}>{m.text}</Meta>
          ))}
        </div>

        <div className="mt-auto space-y-2">
          {decision ? (
            <div className="space-y-1 text-xs">
              <span className={cn("inline-block rounded px-1.5 py-0.5 font-medium", decision.className)}>{decision.text}</span>
              {item.reasons.length > 0 && (
                <ul className="list-inside list-disc text-muted-foreground">
                  {item.reasons.slice(0, 3).map((r) => <li key={r}>{r}</li>)}
                </ul>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Analisi AI in attesa</p>
          )}
          {facts.length > 0 && <p className="text-xs text-muted-foreground">{facts.join(" · ")}</p>}
        </div>
      </div>

      <footer className="flex items-center gap-2 border-t px-5 py-2.5 text-xs text-muted-foreground">
        <span className="truncate">{sourceLabel(item.source)}</span>
        {item.published_at && (
          <>
            <span aria-hidden>·</span>
            <span className="shrink-0">{timeAgo(item.published_at)}</span>
          </>
        )}
        <div className="ml-auto flex shrink-0 gap-1">
          {/^https?:\/\//i.test(item.url ?? "") && (
            <CardAction label="Apri alla fonte" render={<a href={item.url!} target="_blank" rel="noreferrer" />}>
              <ExternalLink />
            </CardAction>
          )}
          {item.verdict === null && view !== "archived" ? (
            <>
              <CardAction label="Scarta" onClick={onDismiss} className="hover:text-destructive"><X /></CardAction>
              <CardAction label="Aggiungi ai preferiti" onClick={onLike} className="hover:text-rose-500"><Heart /></CardAction>
            </>
          ) : item.verdict === "like" ? (
            <CardAction label="Togli dai preferiti" onClick={onRestore} className="text-rose-500">
              <Heart className="fill-current" />
            </CardAction>
          ) : item.verdict === "dislike" ? (
            <CardAction label="Rimetti nel feed" onClick={onRestore}><Undo2 /></CardAction>
          ) : null}
        </div>
      </footer>
    </article>
  );
}

function Meta({ icon, className, children }: { icon: React.ReactNode; className?: string; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex min-w-0 items-center gap-1.5 [&_svg]:size-3.5 [&_svg]:shrink-0", className)}>
      {icon}
      <span className="truncate">{children}</span>
    </span>
  );
}

function CardAction({
  label,
  onClick,
  className,
  render,
  children,
}: {
  label: string;
  onClick?: () => void;
  className?: string;
  render?: React.ReactElement;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button variant="ghost" size="icon-sm" aria-label={label} onClick={onClick} render={render} nativeButton={!render}
            className={cn("text-muted-foreground", className)} />
        }
      >
        {children}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

const GRID = "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3";

export function ItemList({
  items,
  loading,
  empty,
  renderItem,
}: {
  items: AreaItem[];
  loading?: boolean;
  empty: React.ReactNode;
  renderItem: (item: AreaItem) => React.ReactNode;
}) {
  if (loading) {
    return (
      <div className={GRID}>
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-56 rounded-xl" />)}
      </div>
    );
  }
  if (items.length === 0) return <>{empty}</>;
  return <div className={GRID}>{items.map(renderItem)}</div>;
}
