# ARCHITECTURE — come è fatta

> Stato: bozza del 02/11/2026. Il perché sta in [PRODUCT.md](PRODUCT.md).
> Descrive l'architettura **di arrivo**; dove il codice di oggi è diverso c'è la sezione "Da oggi ad arrivo".
> Le voci marcate **(scelta di Claude)** vanno confermate.

## Vista d'insieme

```
  Ale (voce/Telegram) ──▶ Hermes / Claude
                              │  tool MCP: jobspy / jobspy_write
                              ▼
                       MCPJungle  mcp.intecha.dev ──▶ mcp-backend (intecha-mcp)
                                                          │  HTTP rete Docker interna
                                                          ▼
  Browser / telefono ──Authentik──▶  jobspy-api  (FastAPI + React buildato, 1 processo)
                                        │
                                        ├── SQLite  /data/feedback.db   (offerte, canali, analisi, verdetti, candidature, CV)
                                        ├── scheduler  thread: refresh canali alle 09:00 Europe/Rome, poi analisi
                                        ├── analisi    pool di 5 thread verso DeepSeek (compatibile OpenAI)
                                        └── jobspy/    libreria di scraping (fork upstream + fonti italiane e remote)
```

Un solo container, come le app sorelle. FastAPI serve l'API, la build statica del frontend e possiede scheduler e analisi.

## Due zone, due regole

| Zona | Cosa è | Regola |
|---|---|---|
| `jobspy/` | Libreria del fork `speedyapply/JobSpy` | Toccare il minimo: ogni modifica è un conflitto al prossimo merge da upstream. |
| `webapp/` | Nostro, non esiste upstream | Zona libera. |

Oggi la regola è già piegata: le fonti nostre (`inpa/`, `subito/`, `remotive/`, `remoteok/`, `weworkremotely/`, `workingnomads/`)
e `presets.py`, `recency.py` stanno dentro `jobspy/`. Il fork è **40 commit dietro e 25 avanti** rispetto a upstream (27/10/2026).
**(scelta di Claude)**: le fonti nuove restano dove sono (sono cartelle nuove, non creano conflitti); le modifiche ai file
upstream (`model.py`, `__init__.py`, scraper esistenti) vanno ridotte al minimo e annotate in `docs/upstream.md` prima del prossimo allineamento.

## Da oggi ad arrivo

| Aspetto | Oggi (`d7d05b2`) | Arrivo |
|---|---|---|
| Struttura backend | `app.py` (998 righe) fa router, servizio, scheduler; `storage.py` (1661 righe) fa tutto il DB | package `webapp/app/` a strati `routers → services → repositories` |
| Accesso ai dati | `sqlite3` grezzo con un lock globale | SQLAlchemy 2 tipizzato, un repository per entità |
| Schema | `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` a mano in `_migrate` | Alembic; prima revisione = schema attuale |
| Chiavi | `job_url` come chiave di tutto | `id` intero + `job_url` unico (resta l'identità logica) **(scelta di Claude)** |
| API | rotte piatte (`/jobs`, `/job?url=`, `/cvs/...`), errori `HTTPException` stringa, nessun contratto | `/api/v1`, Problem Details, `openapi.json` committato |
| Stato in memoria | `_last_result` per `/export` e `/search` ad hoc | `/search` diventa "prova un canale" senza stato; export dai dati salvati |
| Analisi | prompt in `analyzer.py`, cache per `context_key` = hash(modello, prompt, CV) | invariato, più report di misura (piano 05) |
| MCP | tutto tranne modulo CV e modifica canali | anche CV e `update_channel` con filtri |
| Auth | solo forward-auth Authentik; l'MCP entra dalla rete interna senza token | come BuyWatcher: OIDC Authentik per web/mobile, token di servizio per l'MCP |
| Frontend | React + shadcn/Tailwind 4, `App.tsx` 291 righe con stato di vista in `useState` | pagine con router, client generato, design system condiviso |
| Build | `webapp/static/` **committata** e anche ricostruita nel Dockerfile | `static/` fuori da git, costruita solo nel Dockerfile |
| Tooling | pip, Python 3.11, `unittest` | `uv`, Python 3.13, `pytest` (la libreria resta su Poetry come upstream) |
| Backup | giornalieri in `/data/backups`, stesso volume | in più copia notturna fuori dal server, retention 14 giorni + mensili |

**Cosa non cambia**: dedup con verdetto condiviso tra copie, storico (avvistamenti e versioni), archiviazione senza cancellazione,
cache delle analisi con invalidazione su modello/prompt/CV, revisione e rendering CV. Si spostano senza cambiare comportamento.

## Stack

| Parte | Scelta |
|---|---|
| Backend | Python, FastAPI, Pydantic v2; arrivo SQLAlchemy 2, Alembic, `pydantic-settings` |
| Scraping | `jobspy/` (requests, tls-client, BeautifulSoup) |
| LLM | `openai` client verso DeepSeek (`deepseek-chat`); qualunque endpoint compatibile OpenAI |
| CV | pdfplumber (estrazione), reportlab (rendering), pypdf/pypdfium2 (verifica e anteprime) |
| Database | SQLite sul volume `jobspy-data` (`/data/feedback.db`) — vedi [adr/003](adr/003-sqlite-un-processo.md) |
| Frontend | React 18 + TypeScript + Vite, TanStack Query, shadcn/Base UI, Tailwind 4, Geist |
| Deploy | Docker multi-stage, Coolify, Authentik, `jobspy.intecha.dev` |

## Modello dati (oggi)

| Tabella | Cosa | Note |
|---|---|---|
| `jobs` | offerte, chiave `job_url` | colonne ricche (RAL, livello, azienda), `first_seen_at`, `archived_at`, `feed_since` |
| `job_sightings`, `job_versions` | ogni avvistamento e ogni cambio di contenuto | storico, cresce più di tutto (22.963 avvistamenti) |
| `channels`, `channel_jobs` | ricerche salvate e appartenenza | filtri dei canali arrivano con la PR #10 |
| `refresh_log` | esecuzioni (refresh e analisi) | |
| `analysis`, `analysis_runs` | ultima analisi valida per offerta + ogni tentativo | `context_key` decide quale analisi è valida; `assessment` JSON |
| `feedback`, `feedback_events` | verdetto corrente + storico | **dato non rigenerabile** |
| `applications`, `application_events` | candidature e note | |
| `cvs`, `cv`, `cv_versions` | libreria CV, testo del CV per l'analisi, versioni | `cv` (riga unica) è il legacy da cui si calcola il contesto |
| `meta` | configurazione analisi, contesto, versioni di migrazione | |

## Flussi

- **Refresh giornaliero** (scheduler, 09:00): per ogni canale, sotto `_scrape_lock`, scraping → normalizzazione → upsert offerte
  → avvistamenti/versioni → appartenenza al canale → log. Poi archiviazione delle offerte senza verdetto più vecchie di `FEED_DAYS` (7).
- **Analisi**: tutte le offerte senza analisi valida per il contesto corrente, fino a 3 tentativi falliti per contesto, 5 in parallelo.
  Un cambio di CV, prompt o modello invalida le analisi (la PR #10 limita la rianalisi alle offerte attive).
- **Dedup**: le copie della stessa offerta (stesso titolo/azienda normalizzati) ereditano il verdetto. È voluto.

## API (oggi)

37 rotte in `app.py`: ricerca ad hoc ed export, feed e offerta, canali (CRUD + refresh), stato, analytics, manutenzione
(recency, archivio, analisi), log, candidature (manuali, storico, note), ripristino, CV (CRUD, upload, default, PDF, anteprima,
revisione, controllo, adattamento). Nessuna versione, nessun contratto.

## MCP

Server `jobspy` (lettura) e `jobspy_write` in `intecha-mcp`. Mancano: tool CV, `update_channel`, i filtri dei canali.
Regola **(scelta di Claude)**, come BuyWatcher: ogni nuova operazione dell'API ha il suo tool, o un'esclusione motivata.

## Sicurezza e privacy

- Repo **pubblica**: niente chiavi, CV, candidature, dati delle offerte, screenshot. `.env` e `webapp/cv/*.pdf` sono ignorati.
- Il CV e il testo degli annunci vanno a DeepSeek: è un trasferimento a un provider esterno, scelto consapevolmente (domanda aperta in PRODUCT).
- Il prompt tratta CV e annunci come dati non attendibili (prompt injection): da tenere.
- `.github/workflows/publish-to-pypi.yml` è di upstream: non attivarlo.
- Fonti: nessun login automatizzato, nessuna rotazione di proxy dall'IP di casa, una ricerca per canale al giorno.
  Vedi [adr/004](adr/004-politica-fonti.md).
