// The one card of the app (offerta, bando, gara): white frame, inner panel tinted by the decision.
import { Bookmark, Undo2, X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { DECISION, DecisionBadge, type DecisionKey } from "./decision";

export type CardState = "open" | "saved" | "dismissed" | "archived";

interface Props {
  decision: DecisionKey;
  badgeLabel?: string;
  top: ReactNode; // chip in alto: età e fonti, oppure scadenza
  org: string | null;
  title: string;
  reason?: ReactNode;
  tags?: ReactNode;
  extra?: ReactNode;
  number: ReactNode;
  place?: string | null;
  state: CardState;
  onOpen?: () => void;
  openHref?: string | null; // card without a detail panel: «Dettagli» opens the source
  onSave: () => void;
  onDismiss: () => void;
  onRestore: () => void;
}

export function DecisionCard({ decision, badgeLabel, top, org, title, reason, tags, extra, number, place, state, onOpen, openHref, onSave, onDismiss, onRestore }: Props) {
  const d = DECISION[decision];
  return (
    <article
      className={cn(
        "flex h-full flex-col rounded-xl border bg-card p-1.5 text-card-foreground transition-shadow hover:shadow-md",
        d.dashed && "border-dashed border-unknown-border",
        state === "dismissed" && "opacity-70",
      )}
    >
      <div className={cn("flex flex-1 flex-col gap-3 rounded-[14px] px-4 pt-3.5 pb-4", d.tint)}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">{top}</div>
          <div className="flex shrink-0 gap-1.5">
            {state === "open" && (
              <>
                <CardAction label="Scarta" onClick={onDismiss} outlined={d.dashed}><X /></CardAction>
                <CardAction label="Aggiungi ai preferiti" onClick={onSave} outlined={d.dashed}><Bookmark /></CardAction>
              </>
            )}
            {state === "saved" && (
              <CardAction label="Togli dai preferiti" onClick={onRestore} outlined={d.dashed}><Bookmark className="fill-current" /></CardAction>
            )}
            {(state === "dismissed" || state === "archived") && (
              <CardAction label="Rimetti nel feed" onClick={onRestore} outlined={d.dashed}><Undo2 /></CardAction>
            )}
          </div>
        </div>

        <DecisionBadge decision={decision} label={badgeLabel} onTint />

        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            {org && <p className="truncate text-[13px] font-medium text-muted-foreground">{org}</p>}
            <h3 className="line-clamp-3 text-lg leading-snug font-semibold">
              {onOpen ? (
                <button type="button" onClick={onOpen} className="text-left outline-none hover:underline focus-visible:underline">{title}</button>
              ) : title}
            </h3>
          </div>
          <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-full bg-card font-heading text-sm font-semibold text-muted-foreground", d.dashed && "border")}>
            {monogram(org)}
          </span>
        </div>

        {reason && <p className="line-clamp-2 text-[13px] leading-relaxed">{reason}</p>}
        {tags && <div className="flex flex-wrap gap-1.5">{tags}</div>}
        {extra}
      </div>

      <footer className="flex items-center justify-between gap-3 px-3 pt-3 pb-2">
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5">{number}</div>
          {place && <p className="truncate text-xs text-muted-foreground">{place}</p>}
        </div>
        {onOpen ? (
          <Button onClick={onOpen} className="h-9 shrink-0 px-4">Dettagli</Button>
        ) : openHref ? (
          <Button render={<a href={openHref} target="_blank" rel="noreferrer" />} nativeButton={false} className="h-9 shrink-0 px-4">Apri</Button>
        ) : null}
      </footer>
    </article>
  );
}

/** Two letters from the first two words: "Azienda Esempio Srl" -> "AE". */
function monogram(name: string | null): string {
  const words = (name ?? "").replace(/[^\p{L}\p{N} ]/gu, " ").split(/\s+/).filter(Boolean);
  return (words.slice(0, 2).map((w) => w[0]).join("") || "?").toUpperCase();
}

/** Big mono number, or the unknown value in grey italic (never a zero). */
export function CardNumber({ value, unit, unknown }: { value: string | null; unit?: string; unknown: string }) {
  if (!value) return <span className="text-[15px] font-medium text-unknown-foreground italic">{unknown}</span>;
  return (
    <>
      <span className="font-mono text-base font-semibold">{value}</span>
      {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
    </>
  );
}

function CardAction({ label, onClick, outlined, children }: { label: string; onClick: () => void; outlined?: boolean; children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            aria-label={label}
            onClick={onClick}
            // 32 visible, 44 touch area on phones
            className={cn("relative size-8 bg-card text-foreground hover:bg-card hover:text-foreground before:absolute before:-inset-1.5 before:content-[''] [&_svg]:size-4", outlined && "border-border")}
          />
        }
      >
        {children}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
