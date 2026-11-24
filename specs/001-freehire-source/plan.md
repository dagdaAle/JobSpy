# Implementation Plan: freehire come sorgente di ricerca

**Branch**: `feat/freehire-source` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-freehire-source/spec.md`

## Summary

Aggiungere freehire (API pubblica JSON, 52k offerte aperte in Italia, dai siti di candidatura delle
aziende e da LinkedIn) come sorgente di JobSpy: un connettore in `jobspy/freehire/`, una tabella
`job_sources` per i dati arricchiti che l'upsert di `jobs` non cancella, il controllo giornaliero delle
chiusure, i canali per azienda e una ricerca al volo che non salva. Le offerte LinkedIn di freehire si
uniscono a quelle dello scraper LinkedIn tramite l'URL normalizzato. Dettagli e prove in
[research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11 (webapp e scraper), TypeScript + React (frontend)

**Primary Dependencies**: FastAPI, requests (già nella sessione di `jobspy.util.create_session`), pydantic;
nessuna dipendenza nuova

**Storage**: SQLite `/data/feedback.db`, un solo processo (ADR 003); migrazione additiva

**Testing**: `unittest` offline con `MagicMock` sulle sessioni HTTP, come `tests/test_workflow.py:139-212`

**Target Platform**: container Linux sul server di casa, deploy Coolify

**Project Type**: web-service + SPA (fork di una libreria di scraping)

**Performance Goals**: ricerca al volo < 5 s (SC-005); refresh di un canale freehire ≤ 4 pagine da 100

**Constraints**: 300 richieste/minuto verso freehire; un refresh al giorno per canale; nessun dato di offerte
in git; nessuna rianalisi di massa

**Scale/Scope**: 19 canali attivi + 3-5 canali freehire; poche centinaia di offerte freehire nel feed

## Constitution Check

*GATE: prima della Phase 0 e di nuovo dopo la Phase 1.*

- **I. Uso personale, repo pubblica** — OK. Fixture dei test inventate (aziende e testi finti), nessuna
  chiave: l'API non ne richiede.
- **II. Due zone** — OK. Connettore in `jobspy/freehire/` (cartella nostra). File upstream toccati il minimo:
  una riga nell'enum `Site` e una nel registro `SCRAPER_MAPPING`, come per inPA. `JobPost` non cambia.
- **III. Verdetti e un solo processo** — OK. Migrazione additiva (`job_sources`, `channels.company_slug`);
  il controllo chiusure gira nel thread dello scheduler esistente, non in un worker nuovo. L'archiviazione
  per chiusura non tocca offerte con verdetto o candidatura. Backup prima del deploy.
- **IV. Fonti educate** — OK. API pubblica, limite rispettato, stop su 403/429, nessun sito vero nei test.
  In più si corregge il gap per cui `Scraper.fail()` produceva un refresh «ok» (R9).
- **V. L'LLM estrae, il codice decide** — OK con uno scostamento motivato. Stipendio e competenze di freehire
  si usano così come sono. I requisiti entrano nella descrizione in una sezione marcata, **senza**
  cambiare il prompt, per non rimettere in coda ~880 offerte (R5). FR-008 va aggiornato di conseguenza.
- **VI. Candidature assistite** — OK. Nessuna candidatura automatica; una chiusura alla fonte non cambia lo
  stato di una candidatura.
- **VII. Testato, semplice, MCP** — OK. Nessuna dipendenza nuova; ogni endpoint nuovo ha il suo tool in
  `intecha-mcp` (PR separata nel repo `intecha-mcp`).

**Esito**: nessuna violazione bloccante. Lo scostamento su FR-008 (R5) è stato approvato da Ale il 24/11 e la
spec è aggiornata.

## Project Structure

### Documentation (this feature)

```text
specs/001-freehire-source/
├── spec.md
├── plan.md              # questo file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/api.md     # Phase 1
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks (non ancora creato)
```

### Source Code (repository root)

```text
jobspy/
├── freehire/__init__.py        # NUOVO: scraper (canali parola chiave e azienda) + client condiviso
├── model.py                    # +1 riga: Site.FREEHIRE
├── __init__.py                 # +2 righe: import e SCRAPER_MAPPING
└── presets.py                  # freehire in ITALY_EXTRA_SITES; search_site passa company_slug

webapp/
├── storage.py                  # job_sources, channels.company_slug, letture con fallback,
│                               #   coda analisi senza sospette/chiuse, archiviazione closed_at_source
├── app.py                      # errori df.attrs → log error; controllo chiusure nello scheduler;
│                               #   /freehire/companies, /freehire/search, /freehire/save, /jobs/analyze
└── frontend/src/
    ├── components/NewChannelDialog.tsx   # sorgente freehire: zona guidata, modalità «segui un'azienda»
    ├── components/FreehireSearch.tsx     # NUOVO: ricerca al volo con «salva»
    ├── components/JobDetailSheet.tsx     # requisiti, «sospetta», «chiusa alla fonte», «analizza ora»
    ├── lib/format.ts                     # etichetta e colore freehire
    └── api/{types.ts,client.ts}, hooks/index.ts

tests/
└── test_freehire.py            # NUOVO

docs/upstream.md                # freehire tra le fonti nostre e nello smoke
README.md                       # freehire tra le sorgenti

# repo separato
~/Progetti/server-apps/intecha-mcp/servers/jobspy.py, tests/tool_names.txt
```

**Structure Decision**: struttura esistente del fork. Il client HTTP di freehire vive in `jobspy/freehire/`
e viene riusato dalla webapp per ricerca al volo, salvataggio e controllo chiusure: un solo posto che parla
con freehire.

## Fasi di implementazione

Ogni fase è un commit (conventional commit in inglese) e lascia i test verdi.

1. **fix(webapp): surface scraper errors** — `_refresh_channel` legge `df.attrs["errors"]` e chiude il log in
   errore. Test: uno scraper finto che chiama `fail()` produce un log `error`. (R9)
2. **feat: freehire source** — `jobspy/freehire/`: traduzione zona (R11), paginazione, `ignored_*` → `fail`,
   403/429 → `fail`, normalizzazione URL e `site=linkedin` per `origin=linkedin` (R3), stipendio, competenze,
   requisiti in descrizione (R5), scarto delle chiuse. Registrazione in `Site`, `SCRAPER_MAPPING`, presets.
3. **feat(webapp): job_sources** — tabella, scrittura dopo l'upsert del canale, letture con fallback, coda di
   analisi senza sospette e chiuse, `POST /jobs/analyze`. Test: un refresh LinkedIn dopo freehire non
   cancella stipendio e competenze.
4. **feat(webapp): source closures** — controllo giornaliero dopo `_refresh_all_channels`, log `kind=archive`
   con `trigger=source_closed`, archiviazione solo senza verdetto/candidatura. Test: chiusa, 404, errore,
   riapertura.
5. **feat(webapp): company channels** — `channels.company_slug`, validazione, `/freehire/companies`.
6. **feat(webapp): freehire on-the-fly search** — `/freehire/search`, `/freehire/save`.
7. **feat(webapp): freehire UI** — dialog canale, pagina ricerca, scheda offerta, etichette; `npm run build`.
8. **docs** — `docs/upstream.md`, README, ARCHITECTURE (tabella `job_sources`).
9. **intecha-mcp** (repo separato, PR sua) — 4 tool nuovi + `create_channel` aggiornato.

## Rischi

- freehire cambia i nomi dei parametri o mette una chiave: i canali freehire vanno in errore nel log
  (fase 1 rende l'errore visibile), il resto di JobSpy continua.
- Doppioni da aggregatori con descrizioni diverse (es. jobleads + sito aziendale): restano due offerte;
  accettato, si misura con SC-002 dopo 2 settimane.
- Volume: una parola chiave larga in Italia dà migliaia di risultati; `results_wanted` del canale resta il
  tetto (default 25, max consigliato 100) e quindi anche il tetto di analisi DeepSeek.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Tabella nuova `job_sources` | l'upsert di `jobs` sovrascrive con `NULL` (R4) | `COALESCE` nell'upsert cambia una regola di dominio per tutte le sorgenti (ADR 002) |
