import type { ReactNode } from "react";

export const CARD_GRID = "grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3";

/** «Da candidare oggi (3)»: a titled group of cards, like «Recommended jobs 387» in the reference. */
export function FeedSection({ title, count, children, action }: { title: string; count: number; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-3 font-heading text-2xl font-semibold">
          {title}
          <span className="rounded-full border bg-card px-3 py-0.5 font-mono text-[13px] font-medium">{count}</span>
        </h2>
        {action}
      </div>
      <div className={CARD_GRID}>{children}</div>
    </section>
  );
}

/** Notice above the list: warn (ambra), error (rosso), info (grigio). */
export function StatusBanner({ kind, icon, title, children, action }: { kind: "warn" | "error" | "info"; icon: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  const cls = { warn: "bg-valuta text-valuta-foreground", error: "bg-destructive-soft text-destructive", info: "bg-muted text-foreground" }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`flex items-start gap-3 rounded-lg px-4 py-3.5 ${cls}`}>
      <span className="mt-0.5 shrink-0 [&_svg]:size-4.5">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{title}</p>
        {children && <p className="text-[13px] leading-relaxed text-foreground">{children}</p>}
      </div>
      {action}
    </div>
  );
}
