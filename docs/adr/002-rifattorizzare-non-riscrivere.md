# ADR 002 — Rifattorizzare, non riscrivere

- Data: 02/11/2026
- Stato: proposta (scelta di Claude, da confermare)

## Contesto

La webapp ha logica curata e collaudata in produzione da settembre (dedup con verdetto condiviso, storico avvistamenti
e versioni, cache delle analisi invalidata da modello/prompt/CV, revisione e rendering dei CV) dentro due file enormi:
`app.py` (998 righe) e `storage.py` (1661 righe), con SQL grezzo e migrazioni a mano.

## Decisione

Si cambia la **struttura** (strati, SQLAlchemy, Alembic, `/api/v1`) e si **sposta** la logica senza cambiarne il
comportamento. I 43 test esistenti si portano per primi e restano verdi a ogni passo.

## Perché

- La parte difficile è già pagata: una riscrittura perderebbe casi limite che oggi sono solo nel codice (es. analisi legacy
  ancora valide, verdetti ereditati tra copie).
- I passi piccoli tengono l'app in produzione durante il lavoro.

## Conseguenze

- Per un periodo convivono le rotte di oggi e `/api/v1/...` (alias), finché frontend e MCP non sono passati.
- Le regole di dominio (prompt, soglie, dedup) cambiano solo in PR dedicate.
