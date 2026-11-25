import { Tag, Wallet } from "lucide-react";
import { AreaPage, type AreaConfig } from "../area/AreaPage";

const SOURCES: Record<string, string> = { ted: "TED · Gazzetta UE" };
const sourceLabel = (s: string) => SOURCES[s] ?? s;

function euro(amount: number, currency: string | null) {
  try {
    return amount.toLocaleString("it-IT", { style: "currency", currency: currency || "EUR", maximumFractionDigits: 0 });
  } catch {
    // Unknown currency code from the source: show it as is.
    return `${amount.toLocaleString("it-IT")} ${currency}`;
  }
}

const CHANNEL_DEFAULTS = { name: "", query: "", cpv: "", country: "ITA", days: 14, max_amount: null, results_wanted: 50 };
const PROFILE_DEFAULTS = { servizi: [], fatturato_annuo: null, certificazioni: [], solo_subappalto_ok: false };

const config: AreaConfig = {
  area: "gare",
  noun: "gare",
  sourceLabel,
  channelDefaults: CHANNEL_DEFAULTS,
  channelFields: [
    { name: "query", label: "Cosa cerchi", kind: "text", wide: true, placeholder: "es. sviluppo software" },
    { name: "cpv", label: "Codici CPV (separati da virgola)", kind: "text", wide: true, placeholder: "es. 72000000, 48000000" },
    { name: "country", label: "Paese (codice ISO a 3 lettere)", kind: "text", placeholder: "ITA" },
    { name: "days", label: "Pubblicate negli ultimi giorni", kind: "number", min: 1, max: 365 },
    { name: "max_amount", label: "Importo massimo (EUR, facoltativo)", kind: "number", min: 0 },
    { name: "results_wanted", label: "Risultati massimi", kind: "number", min: 1, max: 500 },
    { name: "name", label: "Nome del canale (facoltativo)", kind: "text", wide: true },
  ],
  // Without text or CPV the search would pull every notice of the country.
  canCreateChannel: (v) => Boolean(String(v.query ?? "").trim() || String(v.cpv ?? "").trim()),
  toChannelRequest: (v) => ({
    ...v,
    cpv: String(v.cpv ?? "").split(",").map((c) => c.trim()).filter(Boolean).join(","),
    country: String(v.country ?? "").trim().toUpperCase(),
  }),
  channelHint: "Serve almeno il testo o un codice CPV. Le gare arrivano da TED (avvisi UE attivi).",
  describeChannel: (ch) => [ch.query, ch.cpv && `CPV ${ch.cpv}`, ch.country].filter(Boolean).join(" · "),
  profileDefaults: PROFILE_DEFAULTS,
  profileFields: [
    {
      name: "servizi", label: "Servizi che offri", kind: "multi", wide: true,
      options: (meta) => (meta?.vocabulary ?? []).map((v) => ({ value: v, label: v })),
    },
    { name: "fatturato_annuo", label: "Fatturato annuo (EUR)", kind: "number", min: 0 },
    { name: "certificazioni", label: "Certificazioni", kind: "tags", placeholder: "es. ISO 9001" },
    { name: "solo_subappalto_ok", label: "Accetto gare solo in subappalto", kind: "switch", wide: true },
  ],
  profileHint: "Il profilo decide l'esito di ogni gara (servizi, fatturato, certificazioni). Cambiarlo non richiede una nuova analisi.",
  itemMeta: (item) => [
    ...(item.amount != null ? [{ icon: <Wallet />, text: euro(item.amount, item.currency) }] : []),
    ...(item.cpv ? [{ icon: <Tag />, text: `CPV ${item.cpv}` }] : []),
  ],
  itemFacts: (f) => {
    const out: string[] = [];
    if (Array.isArray(f.servizi) && f.servizi.length) out.push(`Servizi: ${f.servizi.join(", ")}`);
    if (typeof f.fatturato_minimo === "number") out.push(`Fatturato minimo ${euro(f.fatturato_minimo, "EUR")}`);
    if (typeof f.subappalto_ammesso === "boolean") out.push(f.subappalto_ammesso ? "Subappalto ammesso" : "Subappalto non ammesso");
    return out;
  },
};

export function GareArea() {
  return <AreaPage config={config} />;
}
