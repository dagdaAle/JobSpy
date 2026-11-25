# Implementation Plan: aree Concorsi PA e Gare P.IVA

**Branch**: `feat/pa-gare-areas` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Summary

Due aree nuove accanto a Lavoro, ognuna un pacchetto autonomo in `webapp/` con connettori, tabelle,
estrazione AI, valutazione in codice, router FastAPI e pagine React proprie. `app.py` le aggancia in tre
punti: `include_router`, `init_tables()` all'avvio, `refresh_all()` + `analyze_pending()` nel giro dello
scheduler. I connettori stanno in `webapp/` e non in `jobspy/`: non producono `JobPost` e la zona upstream
resta intatta (ADR 001).

## Technical Context

- Python 3.11, FastAPI, requests, BeautifulSoup (già in `requirements.txt`) per la GU; nessuna dipendenza
  nuova. TypeScript + React 18 + TanStack Query + shadcn/ui.
- Storage: SQLite `/data/feedback.db` via `storage._connect()` e `storage._lock` (ADR 003); tabelle nuove
  `CREATE TABLE IF NOT EXISTS`, nessuna migrazione di tabelle esistenti.
- LLM: `analyzer._client()` / `analyzer.MODEL` (DeepSeek), JSON a schema, `null` se non noto.
- Test: `unittest` offline, sessioni HTTP e client LLM finti (`MagicMock`), HTML/JSON registrati inventati.

## Struttura

```text
webapp/
├── area_common.py        # infrastruttura neutra: AreaStore (tabelle per prefisso), Area, area_router,
│                         # refresh e estrazione con log, http session, llm_json
├── pa/
│   ├── __init__.py       # AREA + router /pa
│   ├── sources.py        # inPA (campi strutturati) + Gazzetta 4ª serie
│   └── evaluate.py       # prompt pa-v1, normalizzazione fatti, decisione in codice
├── gare/
│   ├── __init__.py       # AREA + router /gare
│   ├── sources.py        # TED v3 (solo bandi aperti cn-*)
│   └── evaluate.py       # prompt gare-v1, normalizzazione fatti, decisione in codice
└── frontend/src/
    ├── components/pa/    # PaArea (configurazione)
    ├── components/gare/  # GareArea (configurazione)
    └── components/area/  # pezzi generici: AreaPage, ItemCard/ItemList, ChannelDialog, ChannelsPanel, ProfileForm
tests/test_areas.py
```

`area_common.py` e `components/area/` sono infrastruttura neutra: non conoscono né PA né Gare. Nessun
import da `pa` a `gare` o viceversa, nessun import delle due aree da Lavoro.

## Data model (stesso schema per le due aree, prefisso `pa_` / `gare_`)

- `<area>_channels(id, name, source, query, location, cpv, country, days, max_amount, results_wanted,
  created_at, last_refresh_at, last_refresh_status)` — i campi non usati da un'area restano NULL
  (PA: `source`, `query`, `location`; Gare: `query`, `cpv` CSV, `country`, `days`, `max_amount`).
- `<area>_items(key PK, source, title, body, buyer, kind, place, deadline, published_at, url, amount,
  currency, cpv, raw_json, first_seen_at, last_seen_at, archived_at)`.
- `<area>_channel_items(channel_id, key, first_seen_at)`.
- `<area>_verdicts(key PK, verdict 'like'|'dislike', updated_at)`.
- `<area>_extractions(key PK, prompt_version, facts_json, created_at)` + `<area>_extraction_errors(key,
  error, created_at)` (max 3 tentativi).
- profilo in `meta` con chiave `<area>_profile` (JSON).

Scadenza: `deadline` ISO (data). Feed = `archived_at IS NULL AND (deadline IS NULL OR deadline >= today)`.

## API (contratti)

Uguali per le due aree, con prefisso `/pa` o `/gare`:

| Metodo | Path | Corpo / risposta |
|---|---|---|
| GET | `/{area}/channels` | `{channels: Channel[]}` |
| POST | `/{area}/channels` | Channel senza id → `{channel, new_count}` (primo refresh subito) |
| DELETE | `/{area}/channels/{id}` | `{ok: true}` |
| POST | `/{area}/channels/{id}/refresh` | `{new_count}` |
| GET | `/{area}/items?view=feed\|saved\|dismissed\|archived&channel_id=` | `{items: Item[]}` |
| POST | `/{area}/verdict` | `{key, verdict: 'like'\|'dislike'\|null}` → `{ok}` |
| GET | `/{area}/profile` · PUT `/{area}/profile` | profilo JSON dell'area |
| GET | `/{area}/meta` | `{sources: string[], vocabulary?: string[]}` |

`Item` = colonne di `<area>_items` (senza `raw_json`) + `verdict`, `facts` (oggetto o null),
`decision: 'adatto'|'da_valutare'|'non_adatto'|null`, `reasons: string[]`, `channel_ids: number[]`.

Profilo PA: `{titoli: string[] /* es. "L-8","LM-32","diploma" */, livello_max:
'diploma'|'triennale'|'magistrale'|'dottorato', aree: string[], sedi: string[], eta: number|null}`.
Profilo Gare: `{servizi: string[] /* tag vocabolario */, fatturato_annuo: number|null,
certificazioni: string[], solo_subappalto_ok: boolean}`.

## Fatti estratti

- PA (`PA_PROMPT_VERSION = "pa-v1"`): `livello_richiesto`, `classi_laurea[]`, `eta_max`, `contratto`
  (`indeterminato|determinato|altro|null`), `posti`, `area_profilo` (vocabolario), `evidenza{campo: frase}`.
- Gare (`GARE_PROMPT_VERSION = "gare-v1"`): `servizi[]` (vocabolario), `fatturato_minimo`,
  `certificazioni_richieste[]`, `subappalto_ammesso`, `raggruppamento_ammesso`, `durata_mesi`, `evidenza`.

## Valutazione (codice)

- PA: livello richiesto > livello del profilo → non adatto «titolo di studio»; classi di laurea note e
  nessuna in comune → non adatto «classe di laurea»; `eta_max` < età → non adatto «età»; area nel profilo
  → adatto; fatto chiave null → da valutare.
- Gare: fatturato minimo > fatturato del profilo → non adatto «fatturato» (o da valutare se subappalto
  ammesso e `solo_subappalto_ok`); certificazione richiesta assente → da valutare «certificazione»;
  servizi in comune → adatto; nessun servizio in comune → non adatto «servizi».

## Scheduler

Dopo il giro dei canali Lavoro e prima del backup: `pa.refresh_all()`, `gare.refresh_all()`, poi
`pa.analyze_pending()`, `gare.analyze_pending()`, ognuno in `try/except` con log (FR-008). Il refresh usa
`refresh_log` con `site = "pa:inpa"` / `"pa:gazzetta"` / `"gare:ted"` e `channel_id` NULL, così la pagina
Log mostra tutto senza confondere gli id dei canali Lavoro.

## Frontend

`App.tsx`: stato `area` (`lavoro` | `pa` | `gare`) in `?area=`; il contenuto attuale di `App` diventa
`LavoroArea` senza cambi di comportamento. `AppHeader` riceve uno switch d'area. `PaArea` e `GareArea`
hanno viste Feed / Preferiti / Scartati / Archivio / Canali / Profilo, card con scadenza, ente, esito e
motivi, dialog nuovo canale con i campi dell'area. Proxy di Vite: aggiungere `/pa` e `/gare`.

## Rischi

- La GU cambia HTML: il parser fallisce in modo esplicito (errore nel log), non restituisce zero.
- TED ha limiti di frequenza non documentati: un canale al giorno, pausa tra le pagine.
