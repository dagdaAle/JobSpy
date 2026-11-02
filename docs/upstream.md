# Allineamento a upstream

Fork di `speedyapply/JobSpy`. Decisione in `docs/adr/001-fork-due-zone.md`: il fork resta allineato a upstream.

## Stato

- Ultimo allineamento: 02/11/2026, merge di `upstream/main` fino a `68b88d6` (release 1.4.1).
- Upstream ha sostituito tls-client con curl_cffi, validato tutti gli argomenti di `scrape_jobs`, riscritto `model.py` e `Scraper`.

## File upstream modificati da noi

- `jobspy/model.py`: 6 voci in più nell'enum `Site` (le nostre fonti).
- `jobspy/__init__.py`: import e voci in `SCRAPER_MAPPING` per le nostre fonti.
- `README.md`: una riga di avviso sul fork.
- `.github/workflows/publish-to-pypi.yml`: trigger solo `workflow_dispatch` (niente pubblicazione su PyPI / MCP).

Tutto il resto di `jobspy/` è identico a upstream.

## Nostre fonti (cartelle nuove, non esistono upstream)

`jobspy/inpa/`, `subito/`, `remotive/`, `remoteok/`, `weworkremotely/`, `workingnomads/`, più `jobspy/presets.py` e `jobspy/recency.py`.
Ogni fonte estende `Scraper`, ritorna `list[JobPost]` e usa `RequestsRotating` / `TLSRotating` + `create_session` da `jobspy/util.py`.

## Prossimo allineamento

1. `git fetch upstream && git checkout -b chore/sync-upstream main && git merge upstream/main`
2. Conflitti: tieni la versione upstream (`git checkout --theirs`) di `model.py`, `__init__.py`, `README.md` e ri-applica le nostre registrazioni.
3. Controlla `jobspy/model.py`: `Scraper`, `ScraperInput`, `JobPost` e le colonne del DataFrame che `webapp/app.py` usa
   (`_DISPLAY_COLUMNS`, `_RICH_PASSTHROUGH`, `_SALARY_MAP`). Adatta le nostre fonti al minimo.
4. Allinea `webapp/requirements.txt` alle `dependencies` del nuovo `pyproject.toml` (il Dockerfile installa con `--no-deps`).
5. Se il merge porta workflow di pubblicazione, disattivali.
6. Test: `cd webapp && PYTHONPATH=.. python -m unittest discover -s ../tests`
7. Smoke dal vivo, una chiamata per sito con `results_wanted=3`: linkedin, indeed, inpa, remotive.
