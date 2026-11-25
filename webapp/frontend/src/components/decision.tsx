// Decisions (Lavoro) and outcomes (PA, Gare) share one look: the card tint, the badge, the section.
// Always text + icon, never colour alone (DESIGN.md).
import { CalendarClock, CircleCheck, CircleHelp, CircleX, Clock } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { Analysis } from "../api/types";
import type { AreaDecision } from "../api/areas";

export type DecisionKey = "candidati" | "valuta" | "lascia" | "nonnoto" | "adatto" | "da_valutare" | "non_adatto";

export const DECISION: Record<DecisionKey, { label: string; icon: ReactNode; tint: string; text: string; dashed?: boolean }> = {
  candidati: { label: "Candidati", icon: <CircleCheck />, tint: "bg-candidati", text: "text-candidati-foreground" },
  valuta: { label: "Valuta", icon: <CircleHelp />, tint: "bg-valuta", text: "text-valuta-foreground" },
  lascia: { label: "Lascia", icon: <CircleX />, tint: "bg-lascia", text: "text-lascia-foreground" },
  nonnoto: { label: "Non noto", icon: <CircleHelp />, tint: "bg-unknown", text: "text-unknown-foreground", dashed: true },
  adatto: { label: "Adatto", icon: <CircleCheck />, tint: "bg-candidati", text: "text-candidati-foreground" },
  da_valutare: { label: "Da valutare", icon: <CircleHelp />, tint: "bg-valuta", text: "text-valuta-foreground" },
  non_adatto: { label: "Non adatto", icon: <CircleX />, tint: "bg-lascia", text: "text-lascia-foreground" },
};

/** Lavoro: the v3 analysis decision, "non noto" when there is no analysis or no decision. */
export function jobDecision(analysis?: Analysis | null): DecisionKey {
  const d = analysis?.assessment?.decision;
  return d === "apply" ? "candidati" : d === "maybe" ? "valuta" : d === "skip" ? "lascia" : "nonnoto";
}

/** PA and Gare: no analysis yet = non noto. */
export function areaDecision(d: AreaDecision | null): DecisionKey {
  return d ?? "nonnoto";
}

export function DecisionBadge({ decision, onTint, label, className }: { decision: DecisionKey; onTint?: boolean; label?: string; className?: string }) {
  const d = DECISION[decision];
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-full py-1 pr-2.5 pl-2 text-xs font-semibold [&_svg]:size-3.5",
        onTint ? "bg-card" : d.tint,
        d.text,
        d.dashed && "border border-dashed border-unknown-border",
        className,
      )}
    >
      {d.icon}
      {label ?? d.label}
    </span>
  );
}

const DAY = 86_400_000;

/** Calendar days from today to an ISO date (negative = past). */
export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((new Date(y, m - 1, d).getTime() - today.getTime()) / DAY);
}

const chip = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium [&_svg]:size-3.5";

/** Deadline chip: filled within 7 days, dashed when unknown, grey when past. */
export function Deadline({ iso }: { iso: string | null }) {
  const days = daysUntil(iso);
  if (days === null)
    return <span className={cn(chip, "border border-dashed border-unknown-border bg-card text-unknown-foreground")}><CalendarClock />Scadenza non indicata</span>;
  const [y, m, d] = iso!.slice(0, 10).split("-").map(Number);
  const date = new Date(y, m - 1, d).toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });
  if (days < 0) return <span className={cn(chip, "bg-muted text-muted-foreground")}><CalendarClock />Scaduto il {date}</span>;
  if (days <= 7)
    return (
      <span className={cn(chip, "bg-deadline font-semibold text-deadline-foreground")}>
        <Clock />
        {days === 0 ? "Scade oggi" : days === 1 ? "Scade domani" : `Scade tra ${days} gg`}
      </span>
    );
  return <span className={cn(chip, "bg-card text-muted-foreground")}><CalendarClock />Scade il {date}</span>;
}

/** Small white chip on the card tint (age, sources). */
export function InfoChip({ icon, children }: { icon?: ReactNode; children: ReactNode }) {
  return <span className={cn(chip, "max-w-full bg-card text-muted-foreground")}>{icon}<span className="truncate">{children}</span></span>;
}

export function Tag({ children, active, unknown, onClick }: { children: ReactNode; active?: boolean; unknown?: boolean; onClick?: () => void }) {
  const cls = cn(
    "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium",
    active ? "border-primary bg-primary text-primary-foreground" : unknown ? "border-dashed border-unknown-border bg-card text-unknown-foreground" : "border-border bg-card text-foreground",
    onClick && "hover:border-foreground/40",
  );
  return onClick ? <button type="button" className={cls} onClick={onClick}>{children}</button> : <span className={cls}>{children}</span>;
}
