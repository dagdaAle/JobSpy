> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 04 · Configurazione

Le variabili arrivano da `.env` (git-ignored; modello in `.env.example`) e dall'ambiente del container. In produzione stanno nelle variabili d'ambiente di Coolify. Solo nomi, nessun valore.

## Variabili d'ambiente

| Variabile | Default | A cosa serve |
|---|---|---|
| `DEEPSEEK_API_KEY` | vuota | chiave DeepSeek. Senza, l'analisi è disattivata. Credenziale: Vaultwarden → DA VERIFICARE nome della voce |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | endpoint compatibile OpenAI |
| `DEEPSEEK_MODEL` | `deepseek-chat` | modello |
| `CV_PATH` | `/data/cv.pdf` | PDF del CV letto all'avvio |
| `FEEDBACK_DB` | `feedback.db` (`/data/feedback.db` nel Dockerfile) | percorso del DB |
| `BACKUP_DIR` | `<cartella del DB>/backups` | dove vanno i backup dell'app |
| `ANALYSIS_WORKERS` | 5 | chiamate DeepSeek in parallelo |
| `FEED_DAYS` | 7 | giorni in feed prima dell'archiviazione per le offerte senza verdetto |
| `REFRESH_HOUR`, `REFRESH_MINUTE` | 9, 0 | ora del refresh giornaliero (ora locale) |
| `TZ` | `Europe/Rome` nel compose | **non togliere**: il refresh delle 09:00 è ora italiana |

`.env.example` cita anche `MAX_ANALYSIS_PER_SEARCH`, che il codice attuale non legge: DA VERIFICARE se va tolta dall'esempio.

Lato `intecha-mcp`: `JOBSPY_URL` (default `http://jobspy-api:8000`).

## Servizi esterni

| Servizio | Uso | Note |
|---|---|---|
| DeepSeek | analisi offerte, revisione e adattamento CV | CV e annunci vanno a DeepSeek: scelta consapevole di Ale |
| LinkedIn, Indeed, Glassdoor | scraping (`ITALY_LOCAL_SITES`) | niente login, niente proxy; dall'IP di casa |
| Subito, inPA | scraping (`ITALY_EXTRA_SITES`), luogo = provincia | fonti del fork |
| Remotive, RemoteOK, WeWorkRemotely, WorkingNomads | scraping (`REMOTE_ONLY_SITES`) | fonti del fork |
| Authentik | forward-auth del dominio | |
| intecha-mcp / MCPJungle | accesso di Hermes e Claude | |

## Dipendenze

- Web: `webapp/requirements.txt` (FastAPI 0.115, uvicorn 0.34, openai 1.59, pdfplumber, reportlab, pypdf, pypdfium2, openpyxl).
- Libreria: `pyproject.toml` (Poetry, come upstream). Il Dockerfile installa `jobspy` con `--no-deps`, quindi `requirements.txt` deve contenere anche le dipendenze della libreria (requests, beautifulsoup4, pandas, pydantic, `curl_cffi>=0.17`, markdownify). A ogni allineamento con upstream vanno riallineate.
- Frontend: `webapp/frontend/package.json` (React 18, Vite 6, TanStack Query 5, Tailwind 4).
