> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 03 · API e tool MCP

## Auth

- **Web**: forward-auth di Authentik davanti a `jobspy.intecha.dev` (gruppo `utenti-app`). L'app non ha login proprio.
- **MCP**: `intecha-mcp` chiama l'API sulla rete Docker interna (`JOBSPY_URL`, default `http://jobspy-api:8000`) **senza token**. Gli accessi per persona e livello stanno nel gateway MCPJungle (badge), gestiti dalla console IntechaMCP.
- Niente OpenAPI committato. FastAPI espone comunque `/docs` e `/openapi.json` di default: DA VERIFICARE che siano raggiungibili dietro Authentik.

Le rotte sono piatte (niente `/api/v1` per ora) ed errori come stringa (`detail`).

## Endpoint

| Metodo e rotta | Cosa fa |
|---|---|
| `GET /status` | analizzatore configurato, CV caricato, analisi in attesa / in corso, `feed_days` |
| `POST /search` | ricerca una tantum (`mode` italy/remote, termini, luogo, raggio, siti) |
| `GET /export` | export CSV o XLSX dell'ultima ricerca, altrimenti di tutte le offerte salvate |
| `GET /jobs` | feed; `archived=true` per l'archivio |
| `GET /job?url=` | dettaglio offerta con analisi, storico e doppioni |
| `POST /jobs/restore` | rimette in feed un'offerta archiviata |
| `POST /feedback` | verdetto `like` / `dislike` / `null`; si propaga alle copie |
| `GET/POST /channels`, `PUT/DELETE /channels/{id}` | canali e loro filtri |
| `POST /channels/{id}/refresh` | refresh manuale di un canale |
| `GET /channels/{id}/jobs` | offerte di un canale |
| `GET /analytics` | KPI e ripartizioni sui dati salvati (dettaglio in `storage.analytics_summary`) |
| `GET /logs` | `refresh_log` |
| `POST /maintenance/analyze` | analizza le offerte senza analisi valida |
| `POST /maintenance/archive?days=` | archivia le offerte senza verdetto più vecchie di N giorni |
| `POST /maintenance/recency?hours=` | imposta la finestra di recenza dei canali |
| `GET/POST /applications`, `POST /applications/manual`, `POST /applications/notes`, `GET /applications/history` | candidature e loro storico |
| `GET/POST /cvs`, `POST /cvs/upload`, `PATCH/DELETE /cvs/{id}`, `POST /cvs/{id}/default` | libreria CV |
| `GET /cvs/{id}/pdf`, `/preview`, `/preview/{page}` | PDF e anteprime |
| `POST /cvs/{id}/review`, `/revision`, `/check` | revisione LLM con modifiche selezionabili, nuova revisione, controllo del testo del PDF |
| `POST /cvs/tailor` | CV adattato a un'offerta (LLM) |

## Tool MCP

Definiti in `intecha-mcp/servers/jobspy.py`. Ognuno è un wrapper sottile su un endpoint.

**Server `jobspy` (lettura)**

| Tool | Endpoint |
|---|---|
| `get_status` | `GET /status` |
| `list_channels` | `GET /channels` |
| `list_channel_jobs` | `GET /channels/{id}/jobs` |
| `list_jobs` | `GET /jobs` |
| `get_job` | `GET /job` |
| `get_analytics` | `GET /analytics` |
| `get_logs` | `GET /logs` |
| `export_jobs` | `GET /export?format=csv` |
| `list_applications` | `GET /applications` |
| `get_application_history` | `GET /applications/history` |

**Server `jobspy_write` (scrittura)**

| Tool | Endpoint |
|---|---|
| `set_favorite`, `discard_job`, `clear_verdict` | `POST /feedback` |
| `restore_job` | `POST /jobs/restore` |
| `save_application` | `POST /applications` |
| `add_manual_application` | `POST /applications/manual` |
| `add_application_note` | `POST /applications/notes` |
| `analyze_backlog` | `POST /maintenance/analyze` |
| `set_recency` | `POST /maintenance/recency` |
| `archive_stale_jobs` | `POST /maintenance/archive` |
| `create_channel` | `POST /channels` |
| `refresh_channel` | `POST /channels/{id}/refresh` |
| `delete_channel` | `DELETE /channels/{id}` |
| `search_jobs` | `POST /search` |

**Senza tool MCP oggi**: tutta la parte CV (`/cvs*`) e la modifica di un canale (`PUT /channels/{id}`). Sono nel piano 05 (MCP completo). Regola: ogni nuova operazione dell'API ha il suo tool, o un'esclusione motivata.

Da non confondere: la cartella `mcp/` della repo è il server `mcp-jobspy` di **upstream** (ricerca diretta sulle bacheche via `uvx`), non quello usato da Hermes.
