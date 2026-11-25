// Generic page of a non-Lavoro area: same shell, sidebar views, cards by outcome, channels and profile.
// Each area passes its own fields and card details; nothing here knows PA or Gare.
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Archive, Bookmark, CalendarClock, Inbox, Plus, Radio, Search, User, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AreaChannel, AreaChannelRequest, AreaItem, AreaKey, AreaView } from "../../api/areas";
import type { Verdict } from "../../api/types";
import { useAreaChannels, useAreaItems, useAreaMeta, useAreaVerdict } from "../../hooks/areas";
import type { Area } from "../AppHeader";
import { areaDecision, daysUntil, type DecisionKey } from "../decision";
import { CARD_GRID, FeedSection } from "../FeedSection";
import { CardSkeletons, EmptyState } from "../JobGrid";
import { AppShell, type NavGroup } from "../shell/AppShell";
import { FacetGroup, Facets, toggle } from "../shell/Facets";
import { FilterBar, RangeField, SelectField, TextField } from "../shell/FilterBar";
import { ChannelDialog } from "./ChannelDialog";
import { ChannelsPanel } from "./ChannelsPanel";
import { ItemCard, ItemDetailSheet, type CardNumberSpec, type MetaEntry } from "./ItemCard";
import { ProfileForm } from "./ProfileForm";
import type { FieldConfig, FormValues } from "./fields";

export interface AreaConfig {
  area: AreaKey;
  noun: string; // plural, lower case: "bandi", "gare"
  sourceLabel: (source: string) => string;
  channelFields: FieldConfig[];
  channelDefaults: FormValues; // module constant: the dialog resets to it on open
  channelHint?: string;
  canCreateChannel?: (values: FormValues) => boolean;
  toChannelRequest?: (values: FormValues) => AreaChannelRequest;
  describeChannel: (ch: AreaChannel) => string;
  profileFields: FieldConfig[];
  profileDefaults: FormValues;
  profileHint?: string;
  itemMeta: (item: AreaItem) => MetaEntry[];
  itemFacts: (facts: Record<string, unknown>) => string[];
  // Big mono number at the bottom of the card.
  itemNumber: (item: AreaItem) => CardNumberSpec;
  // The range in the filter bar; 0 = no limit. Items with an unknown value always stay.
  range: { label: string; max: number; step: number; format: (v: number) => string; keep: (item: AreaItem, v: number) => boolean };
}

type Tab = AreaView | "channels" | "profile";
type SortKey = "deadline" | "recent";

// Verdict each list shows; the archive shows everything that left the feed.
const VIEW_VERDICT: Record<AreaView, Verdict | null | undefined> = {
  feed: null,
  saved: "like",
  dismissed: "dislike",
  archived: undefined,
};

const OUTCOMES: { key: DecisionKey; label: string; section: string }[] = [
  { key: "adatto", label: "Adatto", section: "Adatti a te" },
  { key: "da_valutare", label: "Da valutare", section: "Da valutare" },
  { key: "nonnoto", label: "Non noto", section: "Non noto" },
  { key: "non_adatto", label: "Non adatto", section: "Non adatti" },
];
const DEFAULT_OUTCOMES = new Set<DecisionKey>(["adatto", "da_valutare", "nonnoto"]);

const ACCENT: Record<AreaKey, string> = { pa: "accent-area-pa", gare: "accent-area-gare" };

export function AreaPage({ config, onArea }: { config: AreaConfig; onArea: (area: Area) => void }) {
  const { area } = config;
  const [tab, setTab] = useState<Tab>("feed");
  const [channelId, setChannelId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<AreaItem | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("deadline");
  const [range, setRange] = useState(0);
  const [outcomes, setOutcomes] = useState(DEFAULT_OUTCOMES);
  const listView = tab !== "channels" && tab !== "profile" ? tab : null;

  const channels = useAreaChannels(area);
  const meta = useAreaMeta(area);
  const items = useAreaItems(area, listView ?? "feed", channelId, listView !== null);
  const verdict = useAreaVerdict(area);
  const channelList = channels.data?.channels ?? [];

  const base = useMemo(() => {
    const want = listView ? VIEW_VERDICT[listView] : undefined;
    const q = search.trim().toLowerCase();
    const out = (items.data?.items ?? []).filter((it) => {
      if (want !== undefined && it.verdict !== want) return false;
      if (range && !config.range.keep(it, range)) return false;
      if (q && !`${it.title} ${it.buyer} ${it.place}`.toLowerCase().includes(q)) return false;
      return true;
    });
    if (sort === "deadline") {
      // Nearest open deadline first; no deadline and past ones last.
      const d = (it: AreaItem) => { const n = daysUntil(it.deadline); return n === null || n < 0 ? Infinity : n; };
      out.sort((a, b) => d(a) - d(b));
    } else out.sort((a, b) => (b.published_at ?? b.first_seen_at).localeCompare(a.published_at ?? a.first_seen_at));
    return out;
  }, [items.data, listView, search, range, sort, config.range]);

  const isFeed = listView === "feed";
  const counts = useMemo(() => {
    const c: Partial<Record<DecisionKey, number>> = {};
    for (const it of base) { const d = areaDecision(it.decision); c[d] = (c[d] ?? 0) + 1; }
    return c;
  }, [base]);
  const visible = isFeed ? base.filter((it) => outcomes.has(areaDecision(it.decision))) : base;

  // Set a verdict and offer an undo that restores the previous one.
  const setVerdict = (item: AreaItem, next: Verdict | null, message: string) => {
    const previous = item.verdict;
    verdict.mutate({ key: item.key, verdict: next });
    toast(message, {
      description: item.title,
      duration: 8000,
      action: { label: "Annulla", onClick: () => verdict.mutate({ key: item.key, verdict: previous }) },
    });
  };
  const like = (it: AreaItem) => setVerdict(it, "like", "Nei preferiti");
  const dismiss = (it: AreaItem) => setVerdict(it, "dislike", "Tra gli scartati");
  const restore = (it: AreaItem) => setVerdict(it, null, it.verdict === "like" ? "Fuori dai preferiti" : "Di nuovo nel feed");

  const hasFilters = !!search || range > 0 || (isFeed && outcomes.size < OUTCOMES.length);
  const reset = () => { setSearch(""); setRange(0); setOutcomes(DEFAULT_OUTCOMES); };

  const nav: NavGroup<Tab>[] = [{
    items: [
      { key: "feed", label: "Feed", icon: <Inbox /> },
      { key: "saved", label: "Preferiti", icon: <Bookmark /> },
      { key: "dismissed", label: "Scartati", icon: <X /> },
      { key: "archived", label: "Archivio", icon: <Archive /> },
      { key: "channels", label: "Canali", icon: <Radio />, count: channelList.length || undefined },
      { key: "profile", label: area === "pa" ? "Profilo PA" : "Profilo Gare", icon: <User /> },
    ],
  }];

  const filterBar = listView ? (
    <FilterBar>
      <SelectField
        icon={<Radio />}
        label="Canale"
        value={channelId === null ? "all" : String(channelId)}
        options={[{ value: "all", label: `Tutti i canali (${channelList.length})` }, ...channelList.map((c) => ({ value: String(c.id), label: c.name || config.describeChannel(c) }))]}
        onChange={(v) => setChannelId(v === "all" ? null : Number(v))}
      />
      <TextField icon={<Search />} label="Cerca" value={search} placeholder="Titolo, ente, luogo…" onChange={setSearch} />
      <SelectField<SortKey>
        icon={<CalendarClock />}
        label="Ordina"
        value={sort}
        options={[{ value: "deadline", label: "Scadenza più vicina" }, { value: "recent", label: "Più recenti" }]}
        onChange={setSort}
      />
      <RangeField label={config.range.label} value={range} min={0} max={config.range.max} step={config.range.step} format={config.range.format} onChange={setRange} accent={ACCENT[area]} />
    </FilterBar>
  ) : undefined;

  const facets = isFeed ? (
    <Facets onReset={hasFilters ? reset : undefined}>
      <FacetGroup
        title="Esito"
        options={OUTCOMES.map((o) => ({ key: o.key, label: o.label, count: counts[o.key] ?? 0 }))}
        selected={outcomes}
        onToggle={(k) => setOutcomes((s) => toggle(s, k))}
      />
    </Facets>
  ) : undefined;

  const card = (item: AreaItem) => (
    <ItemCard
      key={item.key}
      item={item}
      view={listView!}
      sourceLabel={config.sourceLabel}
      meta={config.itemMeta(item)}
      facts={item.facts ? config.itemFacts(item.facts) : []}
      number={config.itemNumber(item)}
      onOpen={() => setSelected(item)}
      onLike={() => like(item)}
      onDismiss={() => dismiss(item)}
      onRestore={() => restore(item)}
    />
  );

  const title = { feed: `${config.noun.charAt(0).toUpperCase()}${config.noun.slice(1)}`, saved: "Preferiti", dismissed: "Scartati", archived: "Archivio", channels: "Canali", profile: area === "pa" ? "Profilo PA" : "Profilo Gare" }[tab];
  const hint = {
    feed: "Prima quelli adatti a te, poi quelli da valutare. Le scadenze entro 7 giorni sono evidenziate.",
    saved: "Quello che hai messo da parte.",
    dismissed: "Puoi rimetterli nel feed.",
    archived: "Scaduti o usciti dal feed.",
    channels: "Ricerche salvate: girano ogni mattina, un errore non ferma gli altri canali.",
    profile: config.profileHint ?? "",
  }[tab];

  return (
    <AppShell area={area} onArea={onArea} nav={nav} active={tab} onNav={(t) => { setTab(t); setSelected(null); }} filterBar={filterBar} facets={facets}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="font-heading text-3xl font-semibold">{title}</h1>
          {hint && <p className="max-w-3xl text-sm text-muted-foreground">{hint}</p>}
        </div>
        {tab === "channels" && <Button className="h-10 px-4" onClick={() => setCreating(true)}><Plus /> Nuovo canale</Button>}
        {listView && <span className="font-mono text-sm text-muted-foreground">{visible.length} {config.noun}</span>}
      </div>

      {listView && (items.isError ? (
        <EmptyState icon={<AlertTriangle />} title="Errore nel caricamento">{(items.error as Error).message}</EmptyState>
      ) : items.isLoading ? (
        <CardSkeletons />
      ) : visible.length === 0 ? (
        <ListEmpty view={listView} noun={config.noun} filtered={hasFilters} onReset={reset}
          noChannels={!channels.isLoading && channelList.length === 0} onCreate={() => setCreating(true)} />
      ) : isFeed ? (
        <div className="space-y-10">
          {OUTCOMES.map((o) => {
            const list = visible.filter((it) => areaDecision(it.decision) === o.key);
            return list.length > 0 && <FeedSection key={o.key} title={o.section} count={list.length}>{list.map(card)}</FeedSection>;
          })}
        </div>
      ) : (
        <div className={CARD_GRID}>{visible.map(card)}</div>
      ))}

      {tab === "channels" && (
        <ChannelsPanel
          area={area}
          channels={channelList}
          loading={channels.isLoading}
          describe={config.describeChannel}
          onCreate={() => setCreating(true)}
          onDeleted={(id) => id === channelId && setChannelId(null)}
        />
      )}

      {tab === "profile" && (
        <ProfileForm area={area} fields={config.profileFields} defaults={config.profileDefaults} meta={meta.data} />
      )}

      <ItemDetailSheet
        item={selected}
        view={listView ?? "feed"}
        sourceLabel={config.sourceLabel}
        facts={selected?.facts ? config.itemFacts(selected.facts) : []}
        number={selected ? config.itemNumber(selected) : null}
        onClose={() => setSelected(null)}
        onLike={like}
        onDismiss={dismiss}
        onRestore={restore}
      />

      <ChannelDialog
        area={area}
        open={creating}
        onOpenChange={setCreating}
        fields={config.channelFields}
        defaults={config.channelDefaults}
        meta={meta.data}
        hint={config.channelHint}
        canSubmit={config.canCreateChannel}
        toRequest={config.toChannelRequest}
      />
    </AppShell>
  );
}

function ListEmpty({ view, noun, filtered, noChannels, onReset, onCreate }: { view: AreaView; noun: string; filtered: boolean; noChannels: boolean; onReset: () => void; onCreate: () => void }) {
  if (view === "feed" && noChannels)
    return (
      <EmptyState icon={<Radio />} title="Nessun canale" action={<Button className="h-10 px-4" onClick={onCreate}><Plus /> Nuovo canale</Button>}>
        Un canale è una ricerca salvata che gira ogni mattina. Crea il primo e i {noun} arrivano qui con scadenza ed esito.
      </EmptyState>
    );
  if (filtered)
    return <EmptyState icon={<Search />} title="Nessun risultato con questi filtri" action={<Button onClick={onReset}><X /> Azzera filtri</Button>}>Togli un filtro o azzera tutto.</EmptyState>;
  if (view === "saved") return <EmptyState icon={<Bookmark />} title="Nessun preferito">Usa il segnalibro per ritrovarli qui.</EmptyState>;
  if (view === "dismissed") return <EmptyState icon={<X />} title="Niente di scartato" />;
  if (view === "archived") return <EmptyState icon={<Archive />} title="Archivio vuoto" />;
  return <EmptyState icon={<Inbox />} title="Niente da decidere oggi">I prossimi {noun} arrivano con l'aggiornamento di domattina.</EmptyState>;
}
