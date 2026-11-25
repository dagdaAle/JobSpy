// Generic page of a non-Lavoro area: views as tabs, card list, channels and profile.
// Each area passes its own fields and card details; nothing here knows PA or Gare.
import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Archive, Heart, Inbox, Trash2 } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AreaChannel, AreaChannelRequest, AreaItem, AreaKey, AreaView } from "../../api/areas";
import type { Verdict } from "../../api/types";
import { useAreaChannels, useAreaItems, useAreaMeta, useAreaVerdict } from "../../hooks/areas";
import { ChannelDialog } from "./ChannelDialog";
import { ChannelsPanel } from "./ChannelsPanel";
import { ItemCard, ItemList, type MetaEntry } from "./ItemCard";
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
}

type Tab = AreaView | "channels" | "profile";

const TABS: { value: Tab; label: string }[] = [
  { value: "feed", label: "Feed" },
  { value: "saved", label: "Preferiti" },
  { value: "dismissed", label: "Scartati" },
  { value: "archived", label: "Archivio" },
  { value: "channels", label: "Canali" },
  { value: "profile", label: "Profilo" },
];

// Verdict each list shows; the archive shows everything that left the feed.
const VIEW_VERDICT: Record<AreaView, Verdict | null | undefined> = {
  feed: null,
  saved: "like",
  dismissed: "dislike",
  archived: undefined,
};

const ALL = "all";

export function AreaPage({ config }: { config: AreaConfig }) {
  const { area } = config;
  const [tab, setTab] = useState<Tab>("feed");
  const [channelId, setChannelId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const listView = tab !== "channels" && tab !== "profile" ? tab : null;

  const channels = useAreaChannels(area);
  const meta = useAreaMeta(area);
  const items = useAreaItems(area, listView ?? "feed", channelId, listView !== null);
  const verdict = useAreaVerdict(area);

  const want = listView ? VIEW_VERDICT[listView] : undefined;
  const visible = (items.data?.items ?? []).filter((it) => want === undefined || it.verdict === want);
  const channelList = channels.data?.channels ?? [];
  const channelItems = [
    { value: ALL, label: "Tutti i canali" },
    ...channelList.map((ch) => ({ value: String(ch.id), label: ch.name || config.describeChannel(ch) })),
  ];

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

  const heading = listView ? HEADINGS(config.noun)[listView] : null;

  return (
    <div className="space-y-6">
      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
        <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <TabsList>
            {TABS.map((t) => <TabsTrigger key={t.value} value={t.value} className="px-2.5">{t.label}</TabsTrigger>)}
          </TabsList>
        </div>
      </Tabs>

      {heading && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">{heading.title}</h1>
              <p className="text-sm text-muted-foreground">{heading.hint}</p>
            </div>
            {channelList.length > 0 && (
              <Select items={channelItems} value={channelId === null ? ALL : String(channelId)}
                onValueChange={(v) => setChannelId(!v || v === ALL ? null : Number(v))}>
                <SelectTrigger aria-label="Filtra per canale" className="w-full sm:w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {channelItems.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
          </div>

          {items.isError ? (
            <Empty icon={<AlertTriangle />} title="Errore nel caricamento">{(items.error as Error).message}</Empty>
          ) : (
            <ItemList
              items={visible}
              loading={items.isLoading}
              empty={<ListEmpty view={listView!} noun={config.noun} noChannels={!channels.isLoading && channelList.length === 0} />}
              renderItem={(item) => (
                <ItemCard
                  key={item.key}
                  item={item}
                  view={listView!}
                  sourceLabel={config.sourceLabel}
                  meta={config.itemMeta(item)}
                  facts={item.facts ? config.itemFacts(item.facts) : []}
                  onLike={() => setVerdict(item, "like", "Nei preferiti")}
                  onDismiss={() => setVerdict(item, "dislike", "Tra gli scartati")}
                  onRestore={() => setVerdict(item, null, item.verdict === "like" ? "Fuori dai preferiti" : "Di nuovo nel feed")}
                />
              )}
            />
          )}
        </>
      )}

      {tab === "channels" && (
        <>
          <h1 className="text-2xl font-semibold tracking-tight">Canali</h1>
          <ChannelsPanel
            area={area}
            channels={channelList}
            loading={channels.isLoading}
            describe={config.describeChannel}
            onCreate={() => setCreating(true)}
            onDeleted={(id) => id === channelId && setChannelId(null)}
          />
        </>
      )}

      {tab === "profile" && (
        <>
          <h1 className="text-2xl font-semibold tracking-tight">Profilo</h1>
          <ProfileForm area={area} fields={config.profileFields} defaults={config.profileDefaults}
            meta={meta.data} hint={config.profileHint} />
        </>
      )}

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
    </div>
  );
}

const HEADINGS = (noun: string): Record<AreaView, { title: string; hint: string }> => ({
  feed: {
    title: `${noun.charAt(0).toUpperCase()}${noun.slice(1)} da vedere`,
    hint: "Con il cuore passa nei Preferiti, con la X tra gli Scartati. Le scadenze entro 7 giorni sono evidenziate.",
  },
  saved: { title: "Preferiti", hint: "Quello che hai messo da parte." },
  dismissed: { title: "Scartati", hint: "Puoi rimetterli nel feed." },
  archived: { title: "Archivio", hint: "Scaduti o usciti dal feed." },
});

function ListEmpty({ view, noun, noChannels }: { view: AreaView; noun: string; noChannels: boolean }) {
  if (view === "feed" && noChannels)
    return <Empty icon={<Inbox />} title="Nessun canale">Apri la scheda Canali e crea una ricerca.</Empty>;
  if (view === "saved") return <Empty icon={<Heart />} title="Nessun preferito">Metti il cuore per ritrovarli qui.</Empty>;
  if (view === "dismissed") return <Empty icon={<Trash2 />} title="Niente di scartato" />;
  if (view === "archived") return <Empty icon={<Archive />} title="Archivio vuoto" />;
  return <Empty icon={<Inbox />} title="Hai visto tutto">Nessun risultato da valutare: i prossimi {noun} arrivano con l'aggiornamento di domattina.</Empty>;
}

function Empty({ icon, title, children }: { icon: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-20 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-5">
        {icon}
      </div>
      <h2 className="font-medium">{title}</h2>
      {children && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{children}</p>}
    </div>
  );
}
