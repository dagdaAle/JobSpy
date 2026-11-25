// Card and detail of a bando (PA) or gara (Gare): the same card as the Lavoro offers, with the deadline on top.
import { Bookmark, CircleCheck, CircleHelp, ExternalLink, Undo2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { AreaItem, AreaView } from "../../api/areas";
import { timeAgo } from "../../lib/format";
import { CardNumber, DecisionCard, type CardState } from "../DecisionCard";
import { areaDecision, DECISION, DecisionBadge, Deadline, Tag } from "../decision";

export interface MetaEntry {
  icon: React.ReactNode;
  text: string;
}

export interface CardNumberSpec {
  value: string | null;
  unit?: string;
  unknown: string;
}

const isUrl = (u: string | null) => /^https?:\/\//i.test(u ?? "");

function stateOf(item: AreaItem, view: AreaView): CardState {
  if (item.verdict === "like") return "saved";
  if (item.verdict === "dislike") return "dismissed";
  return view === "archived" ? "archived" : "open";
}

interface Props {
  item: AreaItem;
  view: AreaView;
  sourceLabel: (source: string) => string;
  meta: MetaEntry[];
  facts: string[];
  number: CardNumberSpec;
  onOpen: () => void;
  onLike: () => void;
  onDismiss: () => void;
  onRestore: () => void;
}

export function ItemCard({ item, view, sourceLabel, meta, facts, number, onOpen, onLike, onDismiss, onRestore }: Props) {
  const decision = areaDecision(item.decision);
  const tags = [...meta.map((m) => m.text), ...facts].slice(0, 4);
  return (
    <DecisionCard
      decision={decision}
      badgeLabel={decision === "nonnoto" ? "Non noto · analisi in attesa" : undefined}
      top={<Deadline iso={item.deadline} />}
      org={item.buyer}
      title={item.title}
      reason={item.reasons[0] ?? (item.decision ? null : "Analisi AI in attesa: leggi l’atto e decidi tu.")}
      tags={tags.map((t) => <Tag key={t}>{t}</Tag>)}
      number={<CardNumber {...number} />}
      place={[item.place, sourceLabel(item.source)].filter(Boolean).join(" · ")}
      state={stateOf(item, view)}
      onOpen={onOpen}
      onSave={onLike}
      onDismiss={onDismiss}
      onRestore={onRestore}
    />
  );
}

export function ItemDetailSheet({ item, view, sourceLabel, facts, number, onClose, onLike, onDismiss, onRestore }: {
  item: AreaItem | null;
  view: AreaView;
  sourceLabel: (source: string) => string;
  facts: string[];
  number: CardNumberSpec | null;
  onClose: () => void;
  onLike: (item: AreaItem) => void;
  onDismiss: (item: AreaItem) => void;
  onRestore: (item: AreaItem) => void;
}) {
  const act = (fn: (item: AreaItem) => void) => { if (item) { fn(item); onClose(); } };
  const decision = areaDecision(item?.decision ?? null);
  const state = item ? stateOf(item, view) : "open";
  return (
    <Sheet open={item !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 bg-background p-0 sm:max-w-[560px]">
        {item && (
          <>
            <div className={cn("space-y-3 px-6 pt-5 pb-6", DECISION[decision].tint)}>
              <div className="flex flex-wrap items-center gap-2 pr-10">
                <DecisionBadge decision={decision} onTint />
                <Deadline iso={item.deadline} />
              </div>
              <p className="text-[13px] text-muted-foreground">{[item.buyer, item.place].filter(Boolean).join(" · ")}</p>
              <SheetTitle className="font-heading text-2xl leading-tight font-semibold">{item.title}</SheetTitle>
              <SheetDescription className="text-sm text-muted-foreground">
                {sourceLabel(item.source)}{item.published_at ? ` · pubblicato ${timeAgo(item.published_at)}` : ""}{item.kind ? ` · ${item.kind}` : ""}
              </SheetDescription>
              {number && (
                <div>
                  {number.value ? <p className="font-mono text-lg font-semibold">{number.value}</p> : <p className="text-base text-unknown-foreground italic">{number.unknown}</p>}
                  {number.unit && <p className="text-xs text-muted-foreground">{number.unit}</p>}
                </div>
              )}
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-6 p-6">
                <section className="space-y-2">
                  <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Perché · i motivi</h3>
                  {item.reasons.length ? item.reasons.map((r) => (
                    <div key={r} className="flex items-start gap-3 rounded-lg border bg-card px-4 py-3 text-sm">
                      <span className={cn("mt-0.5 [&_svg]:size-4", DECISION[decision].text)}>{decision === "adatto" ? <CircleCheck /> : <CircleHelp />}</span>
                      {r}
                    </div>
                  )) : (
                    <div className="flex items-start gap-3 rounded-lg border border-dashed border-unknown-border bg-card px-4 py-3 text-sm text-unknown-foreground">
                      <CircleHelp className="mt-0.5 size-4" /> Dati insufficienti: l’analisi AI non c’è ancora.
                    </div>
                  )}
                </section>

                {facts.length > 0 && (
                  <section className="space-y-2">
                    <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Fatti estratti</h3>
                    <ul className="divide-y rounded-lg border bg-card px-4 text-[13px]">
                      {facts.map((f) => <li key={f} className="py-2.5">{f}</li>)}
                      {item.cpv && <li className="py-2.5 font-mono">CPV {item.cpv}</li>}
                    </ul>
                  </section>
                )}

                {item.body && (
                  <section className="space-y-2">
                    <h3 className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">Testo</h3>
                    <p className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground">{item.body}</p>
                  </section>
                )}
              </div>
            </ScrollArea>

            <div className="flex justify-end gap-3 border-t bg-card px-6 py-4">
              {state === "open" && <>
                <Button variant="ghost" className="h-10 px-4" onClick={() => act(onDismiss)}><X /> Scarta</Button>
                <Button variant="outline" className="h-10 px-4" onClick={() => act(onLike)}><Bookmark /> Preferito</Button>
              </>}
              {state !== "open" && <Button variant="outline" className="h-10 px-4" onClick={() => act(onRestore)}><Undo2 /> {state === "saved" ? "Togli dai preferiti" : "Rimetti nel feed"}</Button>}
              {isUrl(item.url) && <Button className="h-10 px-5" render={<a href={item.url!} target="_blank" rel="noreferrer" />} nativeButton={false}>Apri alla fonte <ExternalLink /></Button>}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
