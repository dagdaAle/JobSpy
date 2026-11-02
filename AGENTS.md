# AGENTS.md — JobSpy

Fork di [`speedyapply/JobSpy`](https://github.com/speedyapply/JobSpy) con una webapp personale sopra: canali di ricerca
offerte, dedup e storico, valutazione LLM (DeepSeek) contro il CV, candidature e libreria CV.
FastAPI + SQLite + React, un solo container sul server di casa dietro Authentik (`jobspy.intecha.dev`).
Hermes lo usa via MCP (`intecha-mcp`, server `jobspy` / `jobspy_write`).

**La repo è pubblica.** Niente chiavi, CV, candidature, dati di offerte o screenshot con nomi, né nel codice né nei documenti.

Prima di toccare il codice leggi:
- [docs/PRODUCT.md](docs/PRODUCT.md): perché esiste, stato, obiettivi, anti-obiettivi, decisioni aperte
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): due zone, architettura di arrivo, modello dati, flussi, MCP
- [docs/DESIGN.md](docs/DESIGN.md): UI, pagine, stati, accessibilità
- [docs/adr/](docs/adr/): decisioni prese, da non rimettere in discussione senza motivo nuovo
- [docs/plans/](docs/plans/): piani per fase (01 consolidare → 05 qualità AI)

## Comandi

```bash
cd webapp && python -m unittest discover -s ../tests     # test, senza rete
docker compose up -d --build                             # app su http://localhost:8080; mai `down -v`
cd webapp/frontend && npm ci && npm run dev              # frontend su :5173
```

## Regole

- **Due zone** ([adr/001](docs/adr/001-fork-due-zone.md)): `jobspy/` è upstream, si tocca il minimo; `webapp/` è nostro.
- **Comportamento di dominio** (dedup, storico, archiviazione, cache analisi, CV) non cambia durante il refactor
  ([adr/002](docs/adr/002-rifattorizzare-non-riscrivere.md)). Un cambio di regola va in una PR sua.
- **Verdetti**: `feedback` e `feedback_events` sono l'unico dato non rigenerabile. Backup coerente prima di ogni migrazione o deploy che tocca il DB.
- **Un solo processo** ([adr/003](docs/adr/003-sqlite-un-processo.md)): niente worker o processi in più che scrivono sul DB.
- **Fonti** ([adr/004](docs/adr/004-politica-fonti.md)): niente login, CAPTCHA o proxy a rotazione; mai i siti veri nei test.
- **LLM** ([adr/005](docs/adr/005-llm-valuta-null-se-non-sa.md)): ciò che non si sa resta `null`/`unknown`; `PROMPT_VERSION` si incrementa a ogni cambio di prompt.
- **MCP**: ogni nuova operazione dell'API ha il suo tool in `intecha-mcp`, o un'esclusione motivata.
- **Lingua**: codice, commenti e commit in inglese (è un fork); `docs/` in italiano come le app sorelle.
- `TZ=Europe/Rome` nel compose non si toglie; il workflow PyPI di upstream non si attiva.
