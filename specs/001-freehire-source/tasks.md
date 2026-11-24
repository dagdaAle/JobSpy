# Tasks: freehire come sorgente di ricerca

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: richiesti dalla constitution (principio VII): ogni storia ha i suoi test offline in
`tests/test_freehire.py`, con risposte inventate (`MagicMock` sulla sessione HTTP, come
`tests/test_workflow.py:139-212`). Mai freehire vero, mai dati di offerte reali.

**Comando test**: `cd webapp && python -m unittest discover -s ../tests`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: si può fare in parallelo (file diversi, nessuna dipendenza)
- **[Story]**: US1…US5 della spec

---

## Phase 1: Setup

- [x] T001 Creare `tests/test_freehire.py` con `setUp` come `tests/test_workflow.py:25-35` (DB temporaneo,
  `init_db`, `configure_analysis`) e un helper `fake_search(payload)` che restituisce una sessione `MagicMock`
- [x] T002 [P] Scrivere in `tests/test_freehire.py` le fixture inventate: una risposta di ricerca (offerta
  workday con stipendio, offerta `source=linkedin`, offerta sospetta, offerta chiusa), un dettaglio aperto,
  un dettaglio chiuso, una risposta con `ignored_params`, una con `ignored_values`, una ricerca aziende

---

## Phase 2: Foundational (blocca tutte le storie)

- [x] T003 Test: uno scraper finto che chiama `Scraper.fail()` fa chiudere il refresh con `status="error"`
  in `tests/test_freehire.py` (R9)
- [x] T004 In `webapp/app.py` `_refresh_channel` (:353-392): leggere `df.attrs["errors"]` dopo `search_site`
  e chiudere il log con `status="error"` e il messaggio. Commit `fix(webapp): surface scraper errors`
- [x] T005 Aggiungere `FREEHIRE = "freehire"` all'enum `Site` in `jobspy/model.py` (dopo `INPA`, :243)
- [x] T006 Creare `jobspy/freehire/__init__.py` con il client condiviso: `BASE_URL`, sessione via
  `create_session(with_retry(...))`, `search(params)`, `job(slug)`, `companies(q)`, `company(slug)`; ogni
  risposta con `meta.ignored_params` o `meta.ignored_values` non vuoti solleva `FreehireError`; 403/429
  sollevano `FreehireError` con lo status
- [x] T007 In `jobspy/freehire/__init__.py`: `location_filter(location)` secondo R11 (vuota, Italia, Europa,
  città) e `normalize_url(raw)` secondo R3 (via `utm_*`, via `/` finale, LinkedIn →
  `https://www.linkedin.com/jobs/view/<external_id>`)
- [x] T008 [P] Test unitari di `location_filter` e `normalize_url` in `tests/test_freehire.py`
- [x] T009 Migrazione in `webapp/storage.py` `_migrate()` (:344-410): `CREATE TABLE IF NOT EXISTS
  job_sources` come in data-model.md, indice su `slug`; colonna `channels.company_slug TEXT NOT NULL
  DEFAULT ''` nel dict delle colonne (:355-369)
- [x] T010 In `webapp/storage.py`: `upsert_job_sources(rows)` (upsert su `(job_url, source)`; `closed_at`
  torna `NULL` se l'offerta è aperta) e `job_source(job_url)`

**Checkpoint**: test verdi, nessuna storia ancora visibile.

---

## Phase 3: User Story 1 — Canali di ricerca su freehire (P1) 🎯 MVP

**Goal**: un canale freehire porta offerte nel feed con dedup, storico e analisi.

**Independent Test**: canale «LLM engineer, Europa, remoto, 7 giorni» con la fixture di ricerca → le offerte
aperte entrano nel feed del canale, la chiusa no, la LinkedIn ha l'URL normalizzato.

### Test

- [x] T011 [P] [US1] Test scraper in `tests/test_freehire.py`: parametri inviati (`q`, `regions`,
  `work_mode`, `posted_within_days`, `limit`, `offset`), paginazione fino a `results_wanted`, scarto delle
  chiuse, `site=linkedin` per `origin=linkedin`, `ignored_*` → `fail`, 429 → `fail`
- [x] T012 [P] [US1] Test di integrazione: refresh di un canale freehire con la fixture → righe in `jobs` e
  `channel_jobs`; un'offerta già salvata dallo scraper LinkedIn con lo stesso id resta una sola riga con lo
  stesso verdetto

### Implementazione

- [x] T013 [US1] Classe `Freehire(Scraper)` in `jobspy/freehire/__init__.py`: `scrape(scraper_input)` usa
  il client (T006), `location_filter`, `is_remote` → `work_mode=remote`, `hours_old` → `posted_within_days`
  (per eccesso), pagine da 100 fino a `results_wanted`, pausa 0,25 s; mappa su `JobPost` (titolo, azienda,
  località, `normalize_url`, descrizione con `description_text`, `date_posted`, `is_remote`, stipendio in
  `min_amount`/`max_amount`/`currency`/`interval`, `skills`); errori via `self.fail()`
- [x] T014 [US1] Registrare `Site.FREEHIRE: Freehire` in `SCRAPER_MAPPING` e l'import in
  `jobspy/__init__.py` (:13-59)
- [x] T015 [US1] In `jobspy/presets.py`: aggiungere `freehire` a `ITALY_EXTRA_SITES` (:30); in `search_site`
  (:82) un ramo `freehire` che passa `search_term`, `location` (testo, senza conversione km→miglia),
  `is_remote`, `hours_old`, `results_wanted`
- [x] T016 [US1] Etichetta e colore `freehire` in `webapp/frontend/src/lib/format.ts` (`SITE_LABELS` :100,
  `siteDot` :119)
- [x] T017 [US1] In `webapp/frontend/src/components/NewChannelDialog.tsx` (:119-199): per `freehire` il campo
  zona suggerisce «Italia, Europa, una città o vuoto» e la distanza è disabilitata

**Checkpoint**: MVP. Commit `feat: freehire source`.

---

## Phase 4: User Story 2 — Dati arricchiti (P2)

**Goal**: stipendio, competenze, requisiti e segnale sospetto usati e mostrati; sospette fuori dalla coda.

**Independent Test**: fixture con un'offerta con stipendio e una sospetta → la prima ha stipendio e
competenze nella scheda anche dopo un refresh LinkedIn della stessa offerta; la seconda non entra in coda.

### Test

- [x] T018 [P] [US2] Test in `tests/test_freehire.py`: dopo il refresh freehire, un upsert LinkedIn della
  stessa offerta con stipendio `NULL` → `/jobs` restituisce ancora lo stipendio freehire (fallback)
- [x] T019 [P] [US2] Test: l'offerta sospetta non compare in `jobs_pending_analysis`; `POST /jobs/analyze`
  la analizza comunque (analyzer finto)
- [x] T020 [P] [US2] Test: la descrizione salvata finisce con la sezione `Requisiti (dalla fonte)` con
  obbligatori e preferiti; `analyzer.PROMPT_VERSION` invariato

### Implementazione

- [x] T021 [US2] In `jobspy/freehire/__init__.py`: aggiungere a fine descrizione la sezione
  `Requisiti (dalla fonte)`; produrre per ogni offerta i dati per `job_sources` (slug, origin, stipendio,
  skills, requirements, category, posting_language, suspect secondo R6, reality, closed_at). Siccome
  `JobPost` ha `extra="forbid"`, esporli in `scraper.source_rows` (lista di dict per `job_url`) invece di
  campi nuovi del modello
- [x] T022 [US2] In `webapp/app.py` `_refresh_channel`: per `site == "freehire"` passare le
  `source_rows` a `storage.upsert_job_sources` dopo `upsert_channel_jobs`. Valutare in fase di
  implementazione se `search_site` restituisce lo scraper o le righe accanto al DataFrame, toccando
  `jobspy/__init__.py` il minimo
- [x] T023 [US2] In `webapp/storage.py`: letture di `/jobs`, `/channels/{id}/jobs` e del dettaglio con
  `LEFT JOIN job_sources` e fallback su `salary_*`/`skills`; campi in più `origin`, `suspect`,
  `source_closed_at`, `requirements`
- [x] T024 [US2] In `webapp/storage.py` `_PENDING_SQL` (:1199-1208): escludere `job_sources.suspect = 1` e
  `job_sources.closed_at IS NOT NULL`
- [x] T025 [US2] `POST /jobs/analyze` in `webapp/app.py`: 404 se l'offerta non esiste, 409 senza CV, altrimenti
  `_analyze_one` sincrono e ritorno dell'analisi
- [x] T026 [P] [US2] Frontend: tipi in `api/types.ts`, chiamata in `api/client.ts`; in
  `components/JobDetailSheet.tsx` requisiti (obbligatori/preferiti), badge «sospetta» con il motivo,
  pulsante «Analizza ora»

**Checkpoint**: commit `feat(webapp): job_sources`.

---

## Phase 5: User Story 3 — Chiusure da freehire (P2)

**Goal**: le offerte chiuse alla fonte escono dal feed entro 24 ore senza perdere verdetti e candidature.

**Independent Test**: offerta freehire nel feed + dettaglio chiuso → archiviata con `closed_at_source`; con
verdetto resta visibile con l'etichetta; con 404 o errore nessun cambio.

### Test

- [x] T027 [P] [US3] Test in `tests/test_freehire.py`: chiusa senza verdetto → `archived_at` e
  `archive_reason='closed_at_source'`; chiusa con verdetto o candidatura → non archiviata,
  `source_closed_at` valorizzato, candidatura invariata; 404 ed errore → nessun cambio; riapertura →
  `closed_at` torna `NULL`

### Implementazione

- [x] T028 [US3] In `webapp/storage.py`: `freehire_jobs_to_check()` (non archiviate, con `job_sources.slug`)
  e `mark_source_closed(job_url, closed_at)` che archivia solo senza `feedback` né `applications`
- [x] T029 [US3] In `webapp/app.py`: `_check_source_closures()` chiamato da `_refresh_all_channels` dopo i
  refresh (:406), log `kind="archive"`, `trigger="source_closed"`, `removed=n`; stop al primo 403/429
- [x] T030 [P] [US3] Frontend: etichetta «chiusa alla fonte» in `JobCard.tsx` e `JobDetailSheet.tsx`

**Checkpoint**: commit `feat(webapp): source closures`.

---

## Phase 6: User Story 4 — Canali per azienda (P3)

**Goal**: seguire tutte le offerte aperte di un'azienda.

**Independent Test**: ricerca «Acme» (fixture) → creazione canale con `company_slug` → refresh con
fixture → offerte dell'azienda nel feed; slug sparito → refresh in errore.

### Test

- [x] T031 [P] [US4] Test in `tests/test_freehire.py`: `POST /channels` con `company_slug` e `site` diverso da
  freehire → 422; refresh di un canale azienda invia `company_slug` e non `q`; slug con 404 → log `error`

### Implementazione

- [x] T032 [US4] `company_slug` in `_CHANNEL_FIELDS` (`webapp/storage.py` :819-832), `create_channel`
  (:847-875), `_channel_from_row` (:878); in `ChannelRequest`/`ChannelUpdate` (`webapp/app.py` :138-166) e nella
  chiamata di `POST /channels` (:604-637) con la validazione 422
- [x] T033 [US4] `Freehire.scrape` usa `company_slug` quando presente (arriva come parametro dal ramo
  freehire di `search_site`, T015); se 0 risultati verifica `company(slug)` e su 404 chiama `fail()`
- [x] T034 [US4] `GET /freehire/companies?q=&limit=` in `webapp/app.py` (contratto in contracts/api.md)
- [x] T035 [P] [US4] Frontend: in `NewChannelDialog.tsx` per freehire un interruttore «Segui un'azienda» con
  ricerca aziende (nome, offerte aperte) che compila `company_slug` e `search_term`

**Checkpoint**: commit `feat(webapp): company channels`.

---

## Phase 7: User Story 5 — Ricerca al volo (P3)

**Goal**: cercare su freehire senza canale e salvare solo i risultati scelti.

**Independent Test**: ricerca con fixture → nessuna riga nuova in `jobs`; salvataggio di uno slug → una riga in
`jobs` e una in `job_sources`; `in_db` vero al giro dopo.

### Test

- [x] T036 [P] [US5] Test in `tests/test_freehire.py`: `GET /freehire/search` non scrive nel DB e marca
  `in_db`; zona non traducibile → 422; `POST /freehire/save` salva, chiusa → 409, 404 → 404, errore → 502

### Implementazione

- [x] T037 [US5] `GET /freehire/search` e `POST /freehire/save` in `webapp/app.py`, riusando il client e la
  mappatura del connettore (T006, T013, T021) e `storage.upsert_jobs` + `upsert_job_sources`
- [x] T038 [P] [US5] Frontend: `components/FreehireSearch.tsx` (campi parola chiave, zona, remoto, giorni;
  lista con stipendio, origine, «già nel DB», pulsante «Salva»), voce di navigazione, hook in `hooks/index.ts`

**Checkpoint**: commit `feat(webapp): freehire on-the-fly search` e `feat(webapp): freehire UI`.

---

## Phase 8: Polish

- [x] T039 [P] `docs/upstream.md`: `jobspy/freehire/` tra le fonti nostre (:21) e nello smoke dal vivo (:33)
- [x] T040 [P] `README.md`: freehire tra le sorgenti; `docs/ARCHITECTURE.md`: tabella `job_sources` e
  controllo chiusure
- [x] T041 `cd webapp/frontend && npm run build` pulito, poi suite completa dei test verde
- [x] T042 Smoke dal vivo una volta a mano (quickstart.md), con `results_wanted=3`; nessun output salvato
  in git
- [ ] T043 PR `feat/freehire-source` → `main` con `--head` esplicito; nessun merge né deploy
- [ ] T044 Repo separato `~/Progetti/server-apps/intecha-mcp`: branch, in `servers/jobspy.py` i tool
  `search_freehire_companies`, `search_freehire`, `save_freehire_job`, `analyze_job` e `company_slug` +
  `freehire` in `create_channel` (:179-197); nomi in `tests/tool_names.txt`; PR sua

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 (MVP).
- US2 dipende da US1 (le offerte freehire devono esistere). US3 dipende da US2 (`job_sources.slug`).
- US4 dipende da US1. US5 dipende da US2 (salvataggio in `job_sources`).
- Polish dopo le storie scelte; T044 dopo che gli endpoint sono definitivi.

```text
Setup → Foundational → US1 ─┬─ US2 ─┬─ US3
                            │       └─ US5
                            └─ US4
```

## Parallel Example

- In Phase 2: T008 in parallelo a T009-T010 (file diversi).
- Dopo US1: US4 (canali azienda) in parallelo a US2 (dati arricchiti); toccano entrambe `webapp/app.py`, quindi
  stesso agente o commit in sequenza.
- Dentro ogni storia: i test [P] si scrivono insieme prima dell'implementazione.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 → canali freehire funzionanti, LinkedIn unito, errori visibili.
2. **Incrementi**: US2 → US3 → US4 → US5, ognuno con test verdi e un commit suo.
3. **Consegna**: una PR su JobSpy con tutti i commit, una PR su intecha-mcp. Merge, backup del DB e deploy
   solo col via di Ale.
