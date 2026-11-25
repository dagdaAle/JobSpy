# Data model: freehire come sorgente di ricerca

Migrazioni con il meccanismo esistente (`storage._migrate`, `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`,
`CREATE TABLE IF NOT EXISTS`). Nessuna colonna esistente cambia significato. Backup del DB prima del deploy
(constitution, principio III).

## Tabella nuova `job_sources`

Una riga per offerta e sorgente esterna arricchita. La scrive solo il connettore freehire; l'upsert di
`jobs` non la tocca.

- `job_url TEXT NOT NULL`: chiave dell'offerta in `jobs`, già normalizzata (R3)
- `source TEXT NOT NULL`: `freehire`
- `slug TEXT NOT NULL`: `public_slug` di freehire, per il controllo chiusure e il salvataggio
- `origin TEXT`: sorgente originale dichiarata da freehire (`linkedin`, `workday`, `jobleads`…)
- `salary_min REAL`, `salary_max REAL`, `salary_currency TEXT`, `salary_interval TEXT`
- `skills TEXT`: JSON array
- `requirements TEXT`: JSON array di `{text, priority}` (`required` | `preferred`)
- `category TEXT`, `posting_language TEXT`
- `suspect INTEGER DEFAULT 0`: 1 se `fake_freshness` o `mass_posting_count >= 5`
- `reality TEXT`: JSON grezzo del blocco `reality`, per mostrarlo nella scheda
- `closed_at TEXT`: data di chiusura alla fonte, `NULL` se aperta
- `checked_at TEXT`: ultimo controllo chiusura
- `updated_at TEXT`
- `PRIMARY KEY (job_url, source)`; indice su `slug`

Regole:
- se un refresh rivede un'offerta prima chiusa e ora aperta, `closed_at` torna `NULL` (edge case riapertura)
- un 404 o un errore durante il controllo non cambiano `closed_at`

## Colonna nuova `channels.company_slug`

- `TEXT NOT NULL DEFAULT ''`. Non vuota solo per i canali freehire per azienda.
- Validazione API: `company_slug` ammesso solo con `site='freehire'`.

## Campi riusati

- `jobs.site`: `freehire`, oppure `linkedin` se `origin=linkedin` (R3).
- `jobs.salary_*`, `jobs.skills`: valorizzati dal connettore come per le altre sorgenti.
- `jobs.description`: descrizione + sezione `Requisiti (dalla fonte)` (R5).
- `jobs.archived_at` / `archive_reason`: nuovo valore `closed_at_source` (R7).

## Letture con fallback

- Scheda, card, feed e `/jobs`: `salary_*` e `skills` = `jobs` se valorizzati, altrimenti `job_sources`.
  In più: `source_closed_at`, `suspect`, `origin`, `requirements`.
- Coda di analisi (`_PENDING_SQL`): esclude le offerte con `job_sources.suspect = 1` o con
  `job_sources.closed_at` non nullo.

## Stati di un'offerta freehire

```text
nuova ──refresh──▶ nel feed ──analisi──▶ valutata
  │                   │
  │ suspect=1         │ closed_at alla fonte
  ▼                   ▼
sospetta (niente   senza verdetto/candidatura ──▶ archiviata (closed_at_source)
analisi automatica) con verdetto o candidatura ──▶ visibile, etichetta «chiusa alla fonte»
```
