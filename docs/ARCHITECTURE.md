# ARCHITECTURE — come è fatta

> Stato: bozza del 02/11/2026, seconda versione. Il perché sta in [PRODUCT.md](PRODUCT.md).
> Descrive l'architettura **di arrivo**; dove il codice di oggi è diverso c'è la sezione "Da oggi ad arrivo".
> Le voci marcate **(scelta di Claude)** vanno confermate.

## Vista d'insieme

```
  Ale (voce/Telegram) ──▶ Hermes generale            Hermes `jobs` (Mac di Ale)
                              │                         │  browser locale headed, sessioni di Ale
                              │  tool MCP               │  cartella locale: dati candidato, PDF, screenshot
                              ▼                         ▼
                       MCPJungle  mcp.intecha.dev ──▶ mcp-backend (intecha-mcp)
                                                          │  HTTP rete Docker interna
                                                          ▼
  Browser ──Authentik──▶  jobspy-api  (FastAPI + React buildato, 1 processo)
  App iOS ──/mobile/ + X-Api-Key──▶ ┘ (Authentik esclude ^/mobile/)
                                        │
                                        ├── SQLite  /data/feedback.db
                                        ├── scheduler  refresh canali 09:00 Europe/Rome → estrazione → valutazione
                                        ├── estrazione pool di thread verso DeepSeek (compatibile OpenAI)
                                        └── jobspy/    libreria di scraping (fork upstream + fonti italiane e remote)
                                                          │
                                        todo-app ◀── MCP ──┘ promemoria di richiamo e colloqui
```

Un solo container, come le app sorelle. FastAPI serve l'API, la build statica del frontend e possiede scheduler ed estrazione.
Il bot `jobs` resta sul Mac perché usa il browser con le sessioni di Ale **(scelta di Claude)**.

## Due zone, due regole

| Zona | Cosa è | Regola |
|---|---|---|
| `jobspy/` | Libreria del fork `speedyapply/JobSpy` | Toccare il minimo: ogni modifica è un conflitto al prossimo merge da upstream. |
| `webapp/` | Nostro, non esiste upstream | Zona libera. |

Oggi le fonti nostre (`inpa/`, `subito/`, `remotive/`, `remoteok/`, `weworkremotely/`, `workingnomads/`) e `presets.py`,
`recency.py` stanno dentro `jobspy/`. Il fork è **40 commit dietro e 25 avanti** rispetto a upstream (27/10/2026).
Le fonti nuove restano in cartelle proprie; le modifiche ai file upstream si annotano in `docs/upstream.md` e il fork
si allinea a ogni rilascio upstream (decisione di Ale: restare allineati).

## Il flusso, da oggi ad arrivo

Oggi una sola chiamata LLM per offerta fa tutto: legge l'annuncio, lo confronta col CV e dà il voto. Il risultato
dipende da CV, prompt e modello insieme, quindi cambiare uno dei tre rifà tutto.

Arrivo **(scelta di Claude)**: sei passi, ognuno con il suo dato salvato e la sua cache.

```
 1 Raccolta        canale → annunci grezzi per fonte                          (scraping, 1 volta al giorno)
 2 Normalizzazione annuncio → offerta canonica (dedup), sede → comune/provincia/km da Verona   (regole)
 3 Estrazione      offerta → fatti + tag a schema, con evidenza                 (DeepSeek; cache: testo + versione estrazione)
 4 Valutazione     fatti + tag + CV taggato + preferenze → componenti + decisione (deterministica, in locale)
 5 Feed            decisione, motivo, componenti, filtri per faccetta
 6 Candidatura     kit → precompilazione (bot) → invio (Ale) → esito → verdetti e esiti tornano nelle preferenze
```

Conseguenze:

- **L'estrazione non dipende dal CV né dalle preferenze**: si rifà solo se cambia il testo dell'annuncio o la versione del prompt di estrazione.
- **Cambiare CV, pesi o preferenze costa zero token**: si rifà solo il passo 4.
- Il CV si estrae **una volta per versione** con lo stesso vocabolario dei tag.
- Il giudizio LLM resta solo dove serve davvero (rubrica di Carriera, motivo in una riga) e si salva con la sua evidenza.

## Da oggi ad arrivo

| Aspetto | Oggi (`d7d05b2`) | Arrivo |
|---|---|---|
| Struttura backend | `app.py` (998 righe) fa router, servizio, scheduler; `storage.py` (1661 righe) fa tutto il DB | package `webapp/app/` a strati `routers → services → repositories` |
| Accesso ai dati | `sqlite3` grezzo con un lock globale | SQLAlchemy 2 tipizzato, un repository per entità |
| Schema | `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` a mano | Alembic; prima revisione = schema attuale |
| Offerte | `jobs` con chiave `job_url`; i doppioni si raggruppano al volo | `offers` (canonica) + `postings` (uno per fonte e URL) **(scelta di Claude)** |
| Tag | lista libera in `analysis.tags` (JSON) | `tags` (faccetta, slug, etichetta, sinonimi) + `offer_tags` (fonte, evidenza) + coda proposte |
| Analisi | una chiamata: tag + riassunto + punteggio + motivi; cache su hash(modello, prompt, CV) | `extractions` (fatti a schema, cache su testo + versione) + `evaluations` (componenti, ricalcolabili) |
| Punteggio | 0-100 dal modello | componenti + gate + decisione, pesi in `preferences` |
| Preferenze | implicite nel prompt ("Verona o remoto dall'Italia") | `preferences`: zone, raggio, contratti, pesi per componente, affinità per tag |
| Candidature | `applications` in JobSpy + cartelle `stato.md` nel bot | solo JobSpy (stati, eventi, file allegati, cosa è stato dichiarato) |
| inPA | bandi nazionali considerati "in zona" | solo sedi nella provincia scelta; i nazionali esclusi o segnalati |
| API | rotte piatte, errori stringa, nessun contratto | `/api/v1`, Problem Details, `openapi.json` committato |
| MCP | tutto tranne CV e modifica canali | anche CV, tag, preferenze, candidature complete |
| Auth | forward-auth Authentik; app iOS con `X-Api-Key` sotto `/mobile/`; MCP dalla rete interna senza token | OIDC Authentik per web, token di servizio per l'MCP |
| Frontend | `App.tsx` con stato di vista in `useState` | pagine con URL, client generato |
| Build | `webapp/static/` committata e anche ricostruita nel Dockerfile | `static/` fuori da git |
| Tooling | pip, Python 3.11, `unittest` | `uv`, Python 3.13, `pytest` (la libreria resta su Poetry come upstream) |
| Backup | giornalieri sullo stesso volume | in più copia notturna fuori dal server |

**Cosa non cambia**: dedup con verdetto condiviso tra copie, storico (avvistamenti e versioni), archiviazione senza
cancellazione, revisione e rendering CV, verdetti esistenti. La migrazione verso `offers`/`postings` e `extractions`
avviene con le analisi vecchie conservate in sola lettura.

## Modello dati di arrivo **(scelta di Claude)**

| Tabella | Cosa | Note |
|---|---|---|
| `offers` | offerta canonica: titolo, azienda, sede normalizzata, km da Verona, stato feed/archivio | identità = chiave di dedup di oggi |
| `postings` | annuncio per fonte: sito, URL, testo, date | `job_url` di oggi diventa qui |
| `sightings`, `versions` | avvistamenti e cambi di testo (le tabelle di oggi) | |
| `channels`, `channel_postings` | ricerche salvate, filtri per faccetta | archiviabili |
| `tags` | faccetta, slug, etichetta, sinonimi, stato (attivo / proposto / unito) | vocabolario versionato |
| `offer_tags` | offerta, tag, fonte (llm / regola / ale), evidenza | |
| `extractions` | fatti a schema per offerta + versione estrazione + token | cache |
| `cv_profiles` | tag e fatti estratti da una versione del CV | |
| `preferences` | zone, raggio, contratti, pesi, affinità per tag | una riga, versionata |
| `evaluations` | componenti, gate, decisione, motivo, versione preferenze | ricalcolabile |
| `feedback`, `feedback_events` | verdetti | **dato non rigenerabile** |
| `applications`, `application_events`, `application_files` | candidature, passi, file inviati, risposte dichiarate | |
| `cvs`, `cv_versions` | libreria CV | |
| `refresh_log`, `meta` | log ed esecuzioni, configurazione | |
| `job_sources` | dati di un catalogo esterno (oggi freehire) per offerta: slug, sorgente originale, stipendio, competenze, requisiti, segnale sospetto, chiusura alla fonte | **già oggi**; fuori da `jobs` perché l'upsert di `jobs` sovrascrive tutto |

freehire (spec `specs/001-freehire-source/`) è già attivo: canali per parola chiave o per azienda, ricerca al volo
senza salvare (`/freehire/search`, `/freehire/save`), controllo giornaliero delle chiusure alla fonte dopo i refresh
(log `archive` / `source_closed`). Le offerte che freehire prende da LinkedIn usano l'URL dello scraper LinkedIn:
stessa riga, stesso verdetto.

## Valutazione: come si calcola **(scelta di Claude)**

- **Gate di fattibilità**: se un bloccante è certo (sede fuori raggio e non remoto, remoto riservato ad altri paesi, requisito
  obbligatorio impossibile) la decisione è `lascia` con il bloccante come motivo. Se è incerto, `valuta` con "da verificare".
- **Corrispondenza** = requisiti obbligatori coperti / obbligatori totali (peso alto) + preferenziali coperti (peso basso).
  Confronto tra insiemi di tag, nessuna chiamata LLM.
- **Interesse** = media pesata delle affinità dei tag dell'offerta; affinità di un tag = (preferiti − scarti) con smoothing,
  calcolata dai `feedback_events`. Ale può fissare a mano l'affinità di un tag.
- **Carriera** = rubrica a punti (tecnologia nuova ma vicina al CV, ruolo un passo avanti, formazione, tipo di datore, dominio in crescita)
  applicata dall'LLM in estrazione con evidenza, sommata in modo deterministico.
- **Condizioni** = RAL rispetto alla soglia di Ale (se scritta), contratto, modalità, km.
- **Decisione** = soglie su una combinazione pesata delle componenti note; le componenti non note non contano e abbassano la confidenza.
  `candidati` richiede confidenza almeno media.

## Candidature

- Stati: `da valutare → da candidarsi → kit pronto → precompilata → inviata → colloquio → offerta | rifiutata | ritirata | nessuna risposta`.
- Ogni passaggio è un `application_event` con data, autore (Ale / bot / sistema) e nota.
- **Kit**: CV adattato (`/cvs/tailor`), lettera se richiesta, risposte proposte alle domande del form, checklist dei campi.
  Il kit si genera nel server; i dati anagrafici restano nel bot.
- **Bot `jobs`**: legge il kit via MCP, precompila nel browser, carica lo screenshot finale e segna `precompilata`.
  Dopo l'ok di Ale invia e segna `inviata`. Le cartelle `stato.md` diventano solo copia locale dei file.
- **Seguito**: a `inviata` si crea in todo-app un promemoria di richiamo (default 10 giorni) **(scelta di Claude)**.

## Tre aree: Lavoro, Concorsi PA, Gare P.IVA (25/11/2026)

Stessa app, stesso DB e stesso login; codice, tabelle, API e pagine separati
([spec 002](../specs/002-pa-gare-areas/spec.md)).

| Area | Fonti | Codice | Tabelle | API | Frontend |
|---|---|---|---|---|---|
| Lavoro | freehire, LinkedIn, Indeed… | `jobspy/`, `webapp/app.py`, `storage.py` | `jobs`, `channels`, `feedback`… | `/jobs`, `/channels`… | `LavoroArea` |
| Concorsi PA | inPA, Gazzetta Ufficiale 4ª serie | `webapp/pa/` | `pa_*` | `/pa/*` | `components/pa/` |
| Gare P.IVA | TED (solo bandi aperti `cn-*`) | `webapp/gare/` | `gare_*` | `/gare/*` | `components/gare/` |

- `webapp/area_common.py` e `components/area/` sono infrastruttura neutra (store per prefisso, router,
  log, chiamata LLM, componenti di lista e form): non conoscono nessuna area. Le aree non si importano a vicenda.
- `app.py` aggancia le aree in tre punti: `include_router`, `init_tables()` all'avvio, `_refresh_areas()`
  nello scheduler dopo i canali Lavoro. Un errore di un'area finisce nel log e non ferma le altre.
- Valutazione come ADR 005/007: l'LLM estrae i fatti del bando o della gara (`pa-v1`, `gare-v1`), la
  decisione adatto / da valutare / non adatto è codice contro il profilo dell'area (in `meta`).
- TED contiene solo gare sopra soglia UE: per una P.IVA sono soprattutto subappalto o raggruppamento.

## Client iOS (26/11/2026)

App SwiftUI in `ios-native/` ([spec 005](../specs/005-ios-app/spec.md)), stesso schema di HNWatch.
- Non può fare il login web di Authentik: ogni rotta è servita anche come `/mobile/<rotta>`. `_MobileGate` in
  `app.py` controlla `X-Api-Key` contro `MOBILE_API_KEY` (503 se manca sul server, 401 se sbagliata), toglie il
  prefisso e passa solo a rotte API (anche `pa` e `gare`); un path sconosciuto è 404 JSON, mai la SPA.
- Authentik esclude `^/mobile/`. La chiave sta nel Keychain del telefono, mai nel binario.
- Decisione e componenti si calcolano sul client come nella web app (porting di `decision.tsx` e
  `JobDetailSheet.tsx`): il backend non cambia. Contratto in [docs/mobile-api.md](mobile-api.md).

## Stack

| Parte | Scelta |
|---|---|
| Backend | Python, FastAPI, Pydantic v2; arrivo SQLAlchemy 2, Alembic, `pydantic-settings` |
| Scraping | `jobspy/` (requests, tls-client, BeautifulSoup) |
| LLM | DeepSeek (`deepseek-chat`) tramite client `openai`; output a schema JSON |
| CV | pdfplumber, reportlab, pypdf/pypdfium2 |
| Database | SQLite sul volume `jobspy-data` (`/data/feedback.db`) — [adr/003](adr/003-sqlite-un-processo.md) |
| Sede | tabella comuni ISTAT con coordinate, distanza in linea d'aria da Verona **(scelta di Claude)** |
| Frontend | React 18 + TypeScript + Vite, TanStack Query, shadcn/Base UI, Tailwind 4 |
| iOS | Swift 6, SwiftUI, iOS 18+, xcodegen, nessuna dipendenza |
| Deploy | Docker multi-stage, Coolify, Authentik, `jobspy.intecha.dev` |

## MCP

Server `jobspy` (lettura) e `jobspy_write` in `intecha-mcp`. Da aggiungere: CV, `update_channel` con filtri, tag
(elenco, proposte, unione), preferenze, kit di candidatura, eventi e file delle candidature.
Regola, come BuyWatcher: ogni nuova operazione dell'API ha il suo tool, o un'esclusione motivata.

## Sicurezza e privacy

- Repo **pubblica**: niente chiavi, CV, candidature, profilo candidato, dati delle offerte, screenshot. `.env` e `webapp/cv/*.pdf` sono ignorati.
- CV e annunci vanno a DeepSeek: scelta consapevole di Ale. I dati anagrafici del bot (`profilo-candidato`, `domande-ricorrenti`)
  non vanno né a JobSpy né a DeepSeek se non per la singola compilazione.
- Il prompt tratta CV e annunci come dati non attendibili (prompt injection): da tenere anche nell'estrazione.
- `.github/workflows/publish-to-pypi.yml` è di upstream: non attivarlo.
- Fonti e bot: [adr/004](adr/004-politica-fonti.md), [adr/008](adr/008-candidatura-assistita.md).
