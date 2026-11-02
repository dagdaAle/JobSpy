# Backend a strati — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** `webapp/` diviso in `routers → services → repositories`, SQLAlchemy 2 + Alembic, `/api/v1` con Problem Details,
`uv` e Python 3.13. Comportamento invariato.

**Spec:** [ARCHITECTURE.md](../ARCHITECTURE.md) (Da oggi ad arrivo), [adr/002](../adr/002-rifattorizzare-non-riscrivere.md).

**Dipende da:** piano 01 (PR #10 mergiata, backup provato).

## Passi

- [ ] `webapp/pyproject.toml` con `uv`, Python 3.13; la libreria `jobspy` installata dal path locale. Test verdi con `uv run pytest`.
- [ ] Package `webapp/app/`: `main.py` (lifespan: DB, scheduler), `config.py` (pydantic-settings, variabili di oggi invariate).
- [ ] Modelli SQLAlchemy sullo **schema attuale**; prima revisione Alembic = `stamp` del DB di produzione (copia), nessun cambio.
- [ ] Repository per entità: jobs (+ sightings/versions), channels, analysis, feedback, applications, cvs, logs. Un modulo per volta,
      ogni passo con i test esistenti verdi.
- [ ] Servizi: `refresh.py` (scraping + dedup + archiviazione), `analysis.py` (ex `analyzer.py` + coda), `cv.py` (ex `cv_*`), `analytics.py`.
- [ ] Router sotto `/api/v1`; le rotte di oggi restano come alias fino al piano 04. Problem Details per gli errori.
- [ ] `/search` ad hoc senza stato in memoria; `/export` dai dati salvati (filtri del feed).
- [ ] `openapi.json` committato e test che fallisce se cambia senza essere rigenerato.
- [ ] Togliere `webapp/static/` da git (la costruisce già il Dockerfile).
- [ ] Deploy con backup prima; verifica: feed, refresh di un canale, analisi di un'offerta, CV, MCP (`get_status`, `list_channels`).

## Fatto quando

`app.py` e `storage.py` non esistono più, test verdi, schema gestito da Alembic, produzione invariata per Ale e per l'MCP.
