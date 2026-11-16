> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 02 · Modello dati

## Dove stanno i dati

| Dato | Dove |
|---|---|
| DB | SQLite `/data/feedback.db` nel container `jobspy-api`, volume Docker `jobspy-data` |
| Backup dell'app | `/data/backups`, stesso volume (14 `daily-*` + copie pre-migrazione tenute per sempre) |
| Backup fuori server | NAS, pull notturno (vedi 05 · Deploy) |
| CV originale | `/data/cv.pdf` (in locale montato read-only da `webapp/cv/cv.pdf`, mai in git) |

**Dato non rigenerabile**: `feedback` e `feedback_events` (i verdetti di Ale). Offerte e analisi si possono riraccogliere o ricalcolare, i verdetti no.

## Tabelle

| Tabella | Chiave | Cosa contiene |
|---|---|---|
| `jobs` | `job_url` | offerta come restituita dallo scraper, più colonne ricche (stipendio, azienda, skill…) e di ciclo di vita (`first_seen_at`, `last_seen_at`, `archived_at`, `archive_reason`, `raw_json`, `feed_since`) |
| `feedback` | `job_url` | verdetto corrente: `like` / `dislike` |
| `feedback_events` | id | storico dei verdetti; `source` = user, propagated, inherited, import |
| `analysis` | `job_url` | analisi corrente: tag, riassunto, punteggio, motivi, `assessment`, `context_key` |
| `analysis_runs` | id | ogni chiamata LLM: modello, versione prompt, CV, stato, token, latenza, errore |
| `channels` | id | ricerche salvate: sito, query, luogo, raggio, filtri (parole, aziende, modalità) |
| `channel_jobs` | (`channel_id`, `job_url`) | offerte per canale, primo/ultimo avvistamento, `is_new` |
| `job_sightings` | id | ogni volta che un'offerta è stata vista, con canale e run |
| `job_versions` | id | versioni del testo (hash del contenuto + JSON completo) |
| `refresh_log` | id | eventi di refresh, analisi, archiviazione: stato, conteggi, durata, errore. Tenuto per sempre |
| `cv` | id = 1 | testo del CV corrente |
| `cv_versions` | id, `sha256` unico | versioni del testo del CV usate dalle analisi |
| `cvs` | id | libreria CV in Markdown: `base` o `tailored` (con `parent_id` e `job_url`), template, predefinito |
| `applications` | `job_url` | candidatura: stato, data, note, prossimo passo, richiamo, CV usato, contatto |
| `application_events` | id | storico della candidatura (note, cambi di stato, import) |
| `meta` | key | flag delle migrazioni una tantum (`history_v1`, `application_history_v1`…) |

## Relazioni

```
channels 1──N channel_jobs N──1 jobs 1──1 feedback
                                 │  1──N feedback_events
                                 │  1──1 analysis      1──N analysis_runs ──▶ cv_versions
                                 │  1──N job_sightings, job_versions
                                 │  1──1 applications  1──N application_events
                                 └──── cvs (tailored, job_url) ──parent_id──▶ cvs (base)
```

Le relazioni passano tutte per `job_url` come testo: non ci sono foreign key dichiarate (tranne `cvs.parent_id`). I doppioni non hanno una tabella: si raggruppano al volo per titolo + azienda.

## Migrazioni

- Nessun Alembic. `storage.init_db()` all'avvio fa `CREATE TABLE IF NOT EXISTS` e aggiunge le colonne mancanti con `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`. Idempotente.
- Migrazioni di dati una tantum protette da una chiave in `meta`.
- Prima delle migrazioni grosse `init_db` fa da sé un backup con tag (`pre-workflow-v2`, `pre-application-history`).
- Il DB passa in WAL all'avvio.
- In arrivo (piano 02): SQLAlchemy 2 + Alembic, con lo schema attuale come prima revisione.

## Regole sui dati

- Un'offerta non si cancella mai: si archivia. Rilanciare lo scraping la rimetterebbe.
- L'archiviazione automatica non tocca le offerte con un verdetto.
- Per far rianalizzare le analisi `legacy`: `UPDATE analysis SET context_key = '' WHERE context_key = 'legacy'` (costa token DeepSeek).
