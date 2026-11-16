> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 08 · Sviluppo locale

## Setup

```bash
cp .env.example .env            # mettere la propria DEEPSEEK_API_KEY (opzionale: senza, niente analisi)
mkdir -p webapp/cv && cp <tuo-cv>.pdf webapp/cv/cv.pdf   # mai in git
docker compose up -d --build    # app su http://localhost:8080
```

Il compose monta il volume `feedback-data` su `/data` e il CV read-only. **Mai `docker compose down -v`**: cancella il DB.

Frontend in sviluppo:

```bash
cd webapp/frontend && npm ci && npm run dev     # :5173
```

Backend senza Docker: DA VERIFICARE la procedura (il Dockerfile installa `webapp/requirements.txt` e la libreria con `pip install --no-deps .`, poi `uvicorn app:app` da `webapp/`).

## Test

```bash
cd webapp && PYTHONPATH=.. python -m unittest discover -s ../tests
```

`unittest`, senza rete: mai i siti veri nei test. File in `tests/`: workflow (dedup, storico, verdetti), filtri di analisi e canali, area inPA, CV (libreria, revisione, template). La CI di upstream gira sulla libreria (`jobspy/`, mypy).

## Convenzioni

| Regola | Dettaglio |
|---|---|
| Repo pubblica | niente chiavi, CV, candidature, dati di offerte, screenshot con nomi |
| Lingua | codice, commenti e commit in inglese; `docs/` in italiano |
| Commit | conventional commit; scope `webapp` per il nostro codice (es. `fix(webapp): …`) |
| Branch | branch + PR, niente commit diretti su `main`; non riscrivere la storia di `main` (rompe i merge da upstream) |
| Due zone | in `jobspy/` si tocca il minimo; le fonti nuove in cartelle proprie; modifiche a file upstream annotate in `docs/upstream.md` |
| Dominio | dedup, storico, archiviazione, cache delle analisi e CV non cambiano durante un refactor; un cambio di regola va in una PR sua |
| Prompt | `PROMPT_VERSION` in `analyzer.py` si incrementa a ogni cambio del prompt |
| MCP | ogni nuova operazione dell'API ha il suo tool in `intecha-mcp`, o un'esclusione motivata |
| Upstream | allineamento con `docs/upstream.md`; `.github/workflows/publish-to-pypi.yml` resta solo `workflow_dispatch` |
| DB | backup coerente prima di ogni migrazione o deploy che tocca il DB |

## Documenti da leggere prima

`AGENTS.md`, poi `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/adr/`, `docs/plans/` (piani 01 consolidare → 07 qualità AI).
