# Research: freehire come sorgente di ricerca

Tutte le prove sull'API sono state fatte il 24/11/2026 con chiamate reali a `https://freehire.me`.

## R1. Endpoint e filtri di ricerca

- **Decisione**: `GET /api/v1/jobs/search` con `q`, `countries` (es. `it`), `regions` (es. `eu`), `cities`
  (es. `verona`), `work_mode=remote`, `posted_within_days`, `company_slug`, `limit` (≤100), `offset`.
- **Perché**: è l'unico endpoint che applica i filtri; `GET /api/v1/jobs` li ignora tutti. I nomi giusti
  sono al plurale (`countries`, `regions`): con `country`/`region` l'API risponde 200 ma mette il
  parametro in `meta.ignored_params` e restituisce tutto il catalogo; un valore sconosciuto finisce in
  `meta.ignored_values` e restituisce 0 risultati.
- **Conseguenza**: una risposta con `ignored_params` o `ignored_values` non vuoti è un errore (FR-003).
- **Alternative**: il server MCP di freehire (`freehire-mcp`): scartato, aggiunge un processo e una
  dipendenza per le stesse chiamate HTTP.

## R2. Limiti e termini

- Header `x-ratelimit-limit: 300` per finestra di 60 s, senza chiave. `robots.txt` non vieta `/api/`
  agli user-agent generici. I termini vietano rivendita e ridistribuzione dei dati, non l'uso personale.
- **Decisione**: user-agent esplicito di JobSpy, pausa di 0,25 s tra le pagine, stop su 403/429 (ADR 004).

## R3. Identità delle offerte e doppioni con LinkedIn

- freehire espone `source` (linkedin, workday, jobleads…), `external_id` e `url` originale con
  `?utm_source=freehire.me` (o `&utm_source=…`).
- Lo scraper LinkedIn di JobSpy salva `https://www.linkedin.com/jobs/view/<id>` (`jobspy/linkedin/__init__.py:164`)
  e `jobs.job_url` è la chiave primaria.
- **Decisione**: normalizzare l'URL togliendo `utm_*` e la `/` finale; per `source=linkedin` costruire
  esattamente `https://www.linkedin.com/jobs/view/<external_id>`. Stessa offerta → stessa riga, un verdetto,
  un'analisi (FR-006).
- **Decisione**: per le offerte con `source=linkedin` il campo `site` resta `linkedin`, così una riga non
  oscilla tra `linkedin` e `freehire` a ogni refresh; la provenienza freehire resta in `job_sources`
  (vedi R4). Per le altre sorgenti `site=freehire`.

## R4. Dove salvare i dati arricchiti

- L'upsert di `jobs` sovrascrive ogni colonna con il valore nuovo, anche `NULL`
  (`webapp/storage.py:597-603`). Se lo scraper LinkedIn ripassa dopo freehire, stipendio e competenze di
  freehire verrebbero cancellati.
- **Decisione**: tabella nuova `job_sources` (una riga per offerta e sorgente esterna), scritta solo dal
  connettore freehire e mai toccata dall'upsert di `jobs`. Lettura con fallback: stipendio e competenze
  mostrati = quelli di `jobs`, se vuoti quelli di `job_sources`. Il connettore valorizza comunque anche
  `salary_*` e `skills` del `JobPost`, così le offerte solo-freehire li hanno nei campi standard.
- **Alternative**: `COALESCE` su `salary_*`/`skills` nell'upsert. Scartata: cambia una regola di dominio per
  tutte le sorgenti (ADR 002 chiede una PR dedicata). Colonne nuove su `jobs`: scartata, sarebbero
  sovrascritte dallo stesso upsert.

## R5. Requisiti all'analisi senza rianalizzare tutto

- Il contesto di analisi include `PROMPT_VERSION` (`storage.configure_analysis`); cambiarlo rimette in coda
  tutte le offerte attive (circa 880 non archiviate) = migliaia di chiamate DeepSeek.
- **Decisione**: nessun cambio al prompt. Il connettore aggiunge in fondo alla descrizione una sezione
  marcata `Requisiti (dalla fonte)` con obbligatori e preferiti. L'analizzatore la legge come parte della
  descrizione già esistente; nessun cambio di `PROMPT_VERSION`, nessuna rianalisi.
- **Scostamento dalla spec** (approvato da Ale il 24/11): FR-008 chiedeva un input distinto e un incremento di
  versione; ora dice «requisiti in una sezione marcata della descrizione». Un input strutturato al prompt si
  fa insieme al prossimo cambio di prompt già previsto (piano 03, valutazione a componenti).

## R6. Offerte sospette

- freehire espone `reality.fake_freshness` (bool), `reality.repost_count`, `reality.mass_posting_count`,
  `reality.class` (es. `fresh`).
- **Decisione**: sospetta se `fake_freshness` è vero oppure `mass_posting_count >= 5`. Salvata in
  `job_sources.suspect`. `_PENDING_SQL` esclude le offerte sospette, come già fa con `site='manual'`.
- **Decisione**: nuovo endpoint `POST /jobs/analyze?job_url=` per l'analisi forzata di una singola offerta
  (oggi esiste solo `POST /maintenance/analyze` per tutta la coda).

## R7. Chiusure

- `GET /api/v1/jobs/{public_slug}` per un'offerta chiusa risponde **200** con `closed_at` valorizzato
  (provato su un'offerta chiusa il giorno prima). Uno slug inesistente risponde **404**.
- C'è anche un feed `GET /api/v1/jobs/changes?since=&cursor=` (opened/closed), ma è globale: milioni di
  eventi al giorno su tutto il mondo. Scartato.
- **Decisione**: controllo giornaliero dopo il refresh, una chiamata per offerta con `job_sources.slug`,
  solo per quelle non archiviate e viste nel feed (decine o poche centinaia: lontano dal limite di 300/min).
  `closed_at` valorizzato → `job_sources.closed_at`; 404 o errore → nessun cambio (spec US3, scenario 3).
- **Decisione**: archiviazione con `archive_reason='closed_at_source'` **solo** se l'offerta non ha verdetto
  né candidatura, come la regola attuale di `archive_stale_jobs`. Con verdetto o candidatura resta visibile
  con l'etichetta «chiusa alla fonte». Così preferiti e candidature non spariscono.

## R8. Canali per azienda

- `GET /api/v1/companies?q=<nome>&limit=` → `slug`, `name`, `job_count`, `tagline`.
  `GET /api/v1/jobs/search?company_slug=<slug>` restituisce le offerte aperte dell'azienda (provato su un'azienda con 18 offerte).
- **Decisione**: colonna nuova `channels.company_slug TEXT DEFAULT ''`. Un canale freehire con
  `company_slug` cerca per azienda; `search_term` (NOT NULL) contiene il nome dell'azienda per la UI.
  Slug che non dà risultati e non esiste più (`GET /api/v1/companies/{slug}` → 404) → refresh in errore.

## R9. Errori dei connettori oggi invisibili

- `Scraper.fail()` scrive in `df.attrs["errors"]`, ma nessuno in `webapp/` lo legge: un connettore che fallisce
  produce un refresh «ok» con 0 offerte (gap trovato nel codice).
- **Decisione**: `_refresh_channel` legge `df.attrs["errors"]` e chiude il log con `status="error"`.
  Vale per tutte le sorgenti: è una correzione, va in un commit separato dentro la stessa PR.

## R10. Ricerca al volo

- Esiste già `POST /search` (`upsert_jobs`), ma **salva** tutti i risultati e non ha UI. Non è adatto.
- **Decisione**: `GET /freehire/search` (non salva, segna i risultati già nel DB) e `POST /freehire/save`
  (prende uno slug, rilegge il dettaglio, salva l'offerta e la sua riga `job_sources`).
  `GET /freehire/companies?q=` per la ricerca aziende. Ogni endpoint ha il suo tool MCP.

## R11. Località dei canali

- **Decisione**: traduzione fissa, senza indovinare:
  - vuota → nessun filtro di zona
  - «Italia» / «Italy» → `countries=it`
  - «Europa» / «Europe» / «EU» → `regions=eu`
  - un nome di città → `cities=<nome minuscolo>` (es. `verona`). Verificato in implementazione: freehire **non**
    segnala le città sconosciute (risponde 0 risultati). Dopo una ricerca vuota si chiede
    `cities=<nome>&limit=1`: se anche quella è vuota la città è sconosciuta e il canale va in errore.
  - `distance_km` ignorato (freehire non filtra per raggio).
