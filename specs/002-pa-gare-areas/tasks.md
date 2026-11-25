# Tasks: aree Concorsi PA e Gare P.IVA

Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

## Fase 1 — infrastruttura neutra

- [x] T001 `webapp/area_common.py`: sessione HTTP con retry, `refresh_channel()`/`extract_pending()` su `refresh_log`, `Area` + `area_router()`, `llm_json()` sul
  client DeepSeek, store generico per area (tabelle con prefisso, canali, items, verdetti, estrazioni, profilo)
- [x] T002 Test dello store generico in `tests/test_areas.py`

## Fase 2 — Concorsi PA (US1, US3)

- [x] T010 `webapp/pa/sources.py`: inPA con campi strutturati e filtro sede
- [x] T011 `webapp/pa/sources.py`: Gazzetta 4ª serie (indice 30 giorni, fascicoli, atti, tipo, scadenza)
- [x] T012 `webapp/pa/evaluate.py`: fatti `pa-v1` e decisione in codice
- [x] T013 `webapp/pa/__init__.py`: router `/pa`, `init_tables`, `refresh_all`, `analyze_pending`
- [x] T014 `tests/test_areas.py`: inPA e GU registrati, filtro sede, scadenza passata, errore fonte, valutazione

## Fase 3 — Gare P.IVA (US2, US3)

- [x] T020 `webapp/gare/sources.py`: TED v3, lotti, importo totale, scadenza più vicina, titolo ita/eng
- [x] T021 `webapp/gare/evaluate.py`: fatti `gare-v1` e decisione in codice
- [x] T022 `webapp/gare/__init__.py`: router `/gare`, `init_tables`, `refresh_all`, `analyze_pending`
- [x] T023 `tests/test_areas.py`: risposta TED registrata, importo massimo, errore, valutazione

## Fase 4 — integrazione

- [x] T030 `app.py`: `include_router` (prima del mount statico), `init_tables` all'avvio, aree nello scheduler
- [x] T031 test: errore di un'area non ferma lo scheduler (SC-003); test esistenti invariati (SC-002)

## Fase 5 — frontend (US4)

- [x] T040 `App.tsx` → `LavoroArea` invariata + switch d'area in `AppHeader`, `?area=` nell'URL
- [x] T041 `components/area/`: lista, card, dialog canale, pagina profilo generici
- [x] T042 `components/pa/` e `components/gare/`: aree con viste e campi propri; client API e tipi
- [x] T043 Proxy Vite `/pa`, `/gare`; `npm run build` senza errori

## Fase 6 — chiusura

- [x] T050 `docs/ARCHITECTURE.md`: le tre aree
- [ ] T051 ruff, mypy, test, build; PR
