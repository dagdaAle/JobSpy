# Contratti: API JobSpy e tool MCP

Tutti gli endpoint stanno nella webapp FastAPI esistente, dietro Authentik. Risposte JSON.

## Canali (modificati)

- `GET /channels` → `sites` include `freehire`.
- `POST /channels` / `PUT /channels/{id}`: campo opzionale `company_slug: str` (default `""`).
  - `company_slug` non vuoto con `site != "freehire"` → 422.
  - Per un canale per azienda `search_term` = nome dell'azienda (solo etichetta).
- Risposta canale: aggiunge `company_slug`.

## Ricerca aziende (nuovo)

`GET /freehire/companies?q=<nome>&limit=10`

```json
{"companies": [{"slug": "acme", "name": "Acme", "job_count": 12, "tagline": "Example company"}]}
```

## Ricerca al volo (nuovo, non salva)

`GET /freehire/search?q=&location=&remote=false&days=&company_slug=&limit=25`

- `location` con la stessa traduzione dei canali (R11); filtro ignorato da freehire o città che freehire non conosce → 422.

```json
{
  "results": [{
    "slug": "ml-engineer-acme-abc123", "job_url": "https://www.linkedin.com/jobs/view/4000000001",
    "title": "AI engineer", "company": "Acme", "location": "Italy", "is_remote": true,
    "origin": "linkedin", "posted_at": "2026-11-20", "salary_min": 30000, "salary_max": 35000,
    "salary_currency": "EUR", "skills": ["python", "langchain"], "suspect": false, "in_db": false
  }]
}
```

## Salva un risultato (nuovo)

`POST /freehire/save` body `{"slug": "<public_slug>"}`

- Rilegge il dettaglio da freehire, salva in `jobs` (come `upsert_jobs`) e in `job_sources`.
- Offerta chiusa alla fonte → 409; slug inesistente → 404; freehire non raggiungibile → 502.

```json
{"job_url": "https://www.linkedin.com/jobs/view/4000000001", "created": true}
```

## Analisi forzata di un'offerta (nuovo)

`POST /jobs/analyze?url=<job_url>` (stessa forma di `POST /jobs/restore`)

- Analizza subito l'offerta anche se sospetta; 404 se l'offerta non esiste, 409 se manca il CV.

## Campi in più sulle offerte (`/jobs`, `/channels/{id}/jobs`, dettaglio)

- `origin`, `suspect`, `source_closed_at`, `requirements`; `salary_*` e `skills` con fallback su `job_sources`.

## Tool MCP (`intecha-mcp`, `servers/jobspy.py`)

- `jobspy__search_freehire_companies(q, limit)` → `GET /freehire/companies`
- `jobspy__search_freehire(q, location, remote, days, company_slug, limit, offset)` → `GET /freehire/search`
- `jobspy_write__save_freehire_job(slug)` → `POST /freehire/save`
- `jobspy_write__analyze_job(job_url)` → `POST /jobs/analyze`
- `jobspy_write__create_channel`: aggiunge `freehire` ai siti nel docstring e il parametro `company_slug`.
- Nomi nuovi in `tests/tool_names.txt`. PR separata nel repo `intecha-mcp`.

## Chiamate verso freehire (uscenti)

- `GET https://freehire.me/api/v1/jobs/search` (canali, ricerca al volo)
- `GET https://freehire.me/api/v1/jobs/{slug}` (salvataggio, controllo chiusure)
- `GET https://freehire.me/api/v1/companies?q=` e `GET https://freehire.me/api/v1/companies/{slug}`
- Header `User-Agent` di JobSpy, `Accept: application/json`; nessuna chiave.
