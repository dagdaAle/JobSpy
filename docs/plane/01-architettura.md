> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 01 · Architettura

## C4 livello 1 — contesto

```
                 ┌──────────────┐
   Ale ─browser─▶│   Authentik  │──▶ ┌─────────────────────────┐ ──scraping──▶ LinkedIn, Indeed, Glassdoor,
  (Mac/telefono) └──────────────┘    │        JobSpy           │               Subito, inPA, Remotive, RemoteOK,
                                     │ jobspy.intecha.dev      │               WeWorkRemotely, WorkingNomads
   Hermes / Claude ─MCP─▶ gateway ──▶│ feed, verdetti, CV,     │ ──HTTPS────▶  DeepSeek API
   (mcp.intecha.dev)                 │ candidature             │
                                     └─────────────────────────┘ ◀──pull notturno── NAS (backup)
```

## C4 livello 2 — container

```
  mcp.intecha.dev ──▶ MCPJungle ──▶ mcp-backend (intecha-mcp, server jobspy / jobspy_write)
                                          │ HTTP su rete Docker interna (JOBSPY_URL)
                                          ▼
  Browser ──Authentik forward-auth──▶ jobspy-api  (un container, un processo uvicorn)
                                          ├── FastAPI: API + build statica React (webapp/static)
                                          ├── thread scheduler: refresh canali 09:00 Europe/Rome
                                          │     → analisi → archiviazione → backup giornaliero
                                          ├── pool di thread analisi → DeepSeek (ANALYSIS_WORKERS)
                                          ├── jobspy/  libreria di scraping
                                          └── SQLite /data/feedback.db  (volume jobspy-data)
                                                 └── /data/backups (14 giornalieri, stesso volume)
```

## Componenti

| Componente | File | Ruolo |
|---|---|---|
| API + scheduler | `webapp/app.py` | rotte, refresh canali, pool di analisi, archiviazione |
| Persistenza | `webapp/storage.py` | schema, migrazioni a mano, dedup, storico, verdetti, backup |
| Analisi | `webapp/analyzer.py` | prompt DeepSeek, output JSON a schema, `PROMPT_VERSION = v3-decision` |
| Filtri canale | `webapp/channel_filters.py` | parole incluse/escluse, aziende escluse, modalità di lavoro |
| CV | `webapp/cv_*.py` | import PDF, revisione, template (Europass), rendering PDF |
| Fonti nostre | `jobspy/inpa`, `subito`, `remotive`, `remoteok`, `weworkremotely`, `workingnomads` | cartelle proprie, non toccano upstream |
| Helper fork | `jobspy/presets.py`, `recency.py`, `common.py` | elenchi siti per modalità, finestra di recenza, retry |
| Frontend | `webapp/frontend/` | React; la build è anche committata in `webapp/static/` |

Il codice è diviso in **due zone**: `jobspy/` è upstream e si tocca il minimo; `webapp/` è nostro (ADR-001).

## Flussi principali

**Refresh giornaliero** (thread scheduler, 09:00 ora italiana)

1. Per ogni canale, uno alla volta sotto `_scrape_lock`: scraping del sito con la query del canale.
2. Salvataggio: `jobs` (upsert su `job_url`), `channel_jobs`, `job_sightings`, `job_versions` se il testo cambia.
3. Analisi in background di tutte le offerte senza analisi valida (pool di thread verso DeepSeek).
4. Archiviazione delle offerte senza verdetto più vecchie di `FEED_DAYS` (default 7). Archiviate, mai cancellate.
5. Backup coerente `daily-*` in `/data/backups`.

**Dedup**: titolo + azienda normalizzati formano la chiave; le copie diventano una card con le sedi unite. Il verdetto si propaga a tutte le copie; uno scarto non sovrascrive mai un preferito. Senza titolo o azienda non si raggruppa.

**Analisi**: una chiamata per offerta legge annuncio + CV e restituisce tag, riassunto, punteggio, motivi e decisione. Valida finché non cambiano modello, versione del prompt o testo del CV (`context_key`). Le analisi pre-migrazione restano valide come `legacy`.

**Candidatura**: Ale (o Hermes via MCP) salva stato, date, CV usato e note; ogni passo è un evento in `application_events`. L'invio resta sempre di Ale.

## Architettura di arrivo

`docs/ARCHITECTURE.md` descrive il punto di arrivo: backend a strati (routers → services → repositories), SQLAlchemy + Alembic, `/api/v1`, estrazione LLM separata dalla valutazione deterministica a componenti, tag a vocabolario controllato. **Non ancora implementato.**
