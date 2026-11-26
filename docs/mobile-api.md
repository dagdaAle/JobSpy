# API mobile (app iOS)

Ogni rotta dell'API è raggiungibile anche come `/mobile/<rotta>`, con lo stesso comportamento e le
stesse risposte JSON. Esempio: `GET /mobile/pa/items` = `GET /pa/items`. Stesso schema di HNWatch.

## Autenticazione

- Header `X-Api-Key: <MOBILE_API_KEY>` su ogni richiesta. Chiave: `openssl rand -hex 32`, solo nelle
  variabili d'ambiente dell'app su Coolify (vedi `.env.example`). Confronto a tempo costante (`hmac.compare_digest`).
- In Authentik il provider di jobspy deve escludere `^/mobile/`: lì il controllo lo fa il backend,
  non il login web. Il resto del dominio resta dietro Authentik.
- Errori del gate: `503 {"detail": "accesso mobile non configurato"}` se `MOBILE_API_KEY` non è impostata;
  `401 {"detail": "chiave API non valida"}` se la chiave manca o è sbagliata; `404` JSON per un path
  che non è una rotta (la SPA e i file statici non sono mai serviti sotto `/mobile/`).
- Errori applicativi: sempre `{"detail": "<messaggio in italiano>"}` (`422` di validazione: `detail` è una lista
  di `{msg, loc}`). 404 non trovato, 409 conflitto (CV cambiato), 502 fonte o modello non raggiungibile,
  503 DeepSeek non configurato.
- Date: `YYYY-MM-DD HH:MM:SS` sono UTC (SQLite); `YYYY-MM-DD` sono giorni di calendario.

## Rotte usate dall'app iOS (v1, area Lavoro)

Elenco, tipi e timeout in [specs/005-ios-app/contract.md](../specs/005-ios-app/contract.md). In breve:

| Metodo | Rotta | Note |
|---|---|---|
| GET | `/mobile/status` | AI configurata, analisi in coda, `feed_days` |
| GET | `/mobile/channels` | `{channels, sites}` |
| POST | `/mobile/channels/{id}/refresh` | scraping: può durare minuti; 502 se la fonte fallisce |
| GET | `/mobile/jobs?archived=false\|true` | `{jobs, analysis, feedback, applications}` per `job_url` |
| GET | `/mobile/channels/{id}/jobs` | stessa forma, solo il canale |
| GET | `/mobile/job?url=<job_url>` | `{job, analysis, feedback}` con la descrizione |
| POST | `/mobile/feedback` | `{job_url, verdict: "like"\|"dislike"\|null, title, company, site}` |
| POST | `/mobile/jobs/restore?url=<job_url>` | dall'archivio al feed |
| GET / POST | `/mobile/applications` | elenco (stessa forma di `/jobs`) / crea o aggiorna una candidatura |
| GET | `/mobile/cvs`, `/mobile/cvs/{id}` | libreria CV, testo |
| GET | `/mobile/cvs/{id}/match?job_url=` | punteggio CV per l'offerta (DeepSeek la prima volta) |
| POST | `/mobile/cvs/{id}/tailor-proposal` | modifiche proposte (DeepSeek) |
| POST | `/mobile/cvs/tailor` | salva il CV adattato; 409 se il CV base è cambiato |

`job_url` va in query string con percent-encoding completo.

## Contratto completo

`GET /mobile/openapi.json` restituisce lo schema OpenAPI di tutte le rotte.

## Da fare sul server (Ale)

1. `MOBILE_API_KEY` nelle variabili d'ambiente di `jobspy-api` su Coolify, poi redeploy.
2. Authentik: nel provider di jobspy aggiungere `^/mobile/` ai percorsi esclusi dall'autenticazione.
3. Prova: `curl -H "X-Api-Key: $KEY" https://jobspy.intecha.dev/mobile/status` → 200;
   senza header → 401.
