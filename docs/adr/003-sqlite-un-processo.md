# ADR 003 — SQLite, un processo

- Data: 02/11/2026
- Stato: in vigore

## Contesto

Un solo utente, ~2.000 offerte, 46 MB di DB. Scheduler e analisi girano come thread dentro il processo FastAPI,
serializzati da `_scrape_lock` e dal lock di `storage.py`.

## Decisione

Resta SQLite su `/data/feedback.db`, un solo processo uvicorn, nessun worker esterno. Con SQLAlchemy si attiva WAL.

## Perché

- Nessun bisogno di concorrenza tra processi; backup e ripristino sono la copia di un file.
- Stessa scelta di todo-app e BuyWatcher.

## Conseguenze

- Mai più di un replica del container; mai `uvicorn --workers > 1`.
- Il backup deve essere coerente (`sqlite3 .backup` o API di backup), non una copia a caldo del file.
