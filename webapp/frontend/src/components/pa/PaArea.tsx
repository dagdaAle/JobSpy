import { FileText } from "lucide-react";
import { AreaPage, type AreaConfig } from "../area/AreaPage";
import type { Area } from "../AppHeader";
import { daysUntil } from "../decision";

const SOURCES: Record<string, string> = { inpa: "inPA", gazzetta: "Gazzetta Ufficiale · Concorsi" };
const sourceLabel = (s: string) => SOURCES[s] ?? s;

const LEVELS = [
  { value: "diploma", label: "Diploma" },
  { value: "triennale", label: "Laurea triennale" },
  { value: "magistrale", label: "Laurea magistrale" },
  { value: "dottorato", label: "Dottorato" },
];
const levelLabel = (v: string) => LEVELS.find((l) => l.value === v)?.label ?? v;

const CHANNEL_DEFAULTS = { name: "", source: "inpa", query: "", location: "Verona", results_wanted: 50 };
const PROFILE_DEFAULTS = { titoli: [], livello_max: null, aree: [], sedi: [], eta: null };

const config: AreaConfig = {
  area: "pa",
  noun: "bandi",
  sourceLabel,
  channelDefaults: CHANNEL_DEFAULTS,
  channelFields: [
    { name: "query", label: "Cosa cerchi", kind: "text", required: true, wide: true, placeholder: "es. istruttore informatico" },
    {
      name: "source", label: "Fonte", kind: "select",
      options: (meta) => (meta?.sources ?? Object.keys(SOURCES)).map((s) => ({ value: s, label: sourceLabel(s) })),
    },
    { name: "location", label: "Sede", kind: "text", placeholder: "es. Verona" },
    { name: "name", label: "Nome del canale (facoltativo)", kind: "text", wide: true },
    { name: "results_wanted", label: "Risultati massimi", kind: "number", min: 1, max: 500 },
  ],
  canCreateChannel: (v) => Boolean(String(v.query ?? "").trim()),
  channelHint: "inPA ha ente, sede e scadenza strutturati; la Gazzetta 4ª serie copre anche i bandi non pubblicati su inPA.",
  describeChannel: (ch) => [sourceLabel(ch.source ?? ""), ch.query, ch.location].filter(Boolean).join(" · "),
  profileDefaults: PROFILE_DEFAULTS,
  profileFields: [
    { name: "titoli", label: "Titoli di studio (classi di laurea)", kind: "tags", wide: true, placeholder: "es. L-8, LM-32, diploma" },
    { name: "livello_max", label: "Titolo più alto", kind: "select", options: LEVELS },
    { name: "eta", label: "Età", kind: "number", min: 16, max: 99 },
    {
      name: "aree", label: "Aree di interesse", kind: "multi", wide: true,
      options: (meta) => (meta?.vocabulary ?? []).map((v) => ({ value: v, label: v })),
    },
    { name: "sedi", label: "Sedi", kind: "tags", wide: true, placeholder: "es. Verona, Vicenza" },
  ],
  profileHint: "Il profilo decide l'esito di ogni bando (titolo, classe di laurea, età, area). Cambiarlo non richiede una nuova analisi.",
  itemMeta: (item) => (item.kind ? [{ icon: <FileText />, text: item.kind }] : []),
  itemNumber: (item) => {
    const d = daysUntil(item.deadline);
    if (d === null) return { value: null, unknown: "Scadenza non nota" };
    if (d < 0) return { value: null, unknown: "Scaduto" };
    return { value: d === 0 ? "oggi" : `${d} ${d === 1 ? "g" : "gg"}`, unit: "alla scadenza", unknown: "" };
  },
  range: {
    label: "Scade entro",
    max: 90,
    step: 5,
    format: (v) => (v ? `${v} gg` : "qualsiasi"),
    // Unknown deadlines stay: unknown is not late.
    keep: (item, v) => { const d = daysUntil(item.deadline); return d === null || d <= v; },
  },
  itemFacts: (f) => {
    const out: string[] = [];
    if (typeof f.livello_richiesto === "string") out.push(`Titolo: ${levelLabel(f.livello_richiesto)}`);
    if (Array.isArray(f.classi_laurea) && f.classi_laurea.length) out.push(`Classi: ${f.classi_laurea.join(", ")}`);
    if (typeof f.posti === "number") out.push(`${f.posti} ${f.posti === 1 ? "posto" : "posti"}`);
    if (typeof f.contratto === "string") out.push(f.contratto === "indeterminato" ? "Tempo indeterminato" : f.contratto === "determinato" ? "Tempo determinato" : "Altro contratto");
    return out;
  },
};

export function PaArea({ onArea }: { onArea: (area: Area) => void }) {
  return <AreaPage config={config} onArea={onArea} />;
}
