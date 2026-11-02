# CLAUDE.md — JobSpy

Leggi [AGENTS.md](AGENTS.md): contesto, documenti da leggere prima, comandi e regole valgono anche per Claude Code.

In breve, quello che non si sbaglia:

| Elemento | Regola | Perché |
|---|---|---|
| Repo | **pubblica** (fork di `speedyapply/JobSpy`) | niente chiavi, CV, candidature, dati di offerte, screenshot con nomi |
| `jobspy/` | zona upstream: file upstream si toccano il minimo, le fonti nostre stanno in cartelle proprie | il fork resta allineato a upstream ([docs/upstream.md](docs/upstream.md)) |
| DB `/data/feedback.db` | backup coerente prima di ogni migrazione o deploy che tocca il DB | i verdetti non sono rigenerabili |
| `webapp/cv/cv.pdf` | montato read-only, mai in git | dato personale |
| `.github/workflows/publish-to-pypi.yml` | solo `workflow_dispatch`, mai attivarlo | pubblicherebbe il fork su PyPI |
| `TZ=Europe/Rome` nel compose | non togliere | il refresh delle 09:00 è ora italiana |
| `DEEPSEEK_API_KEY` | solo da `.env` (git-ignored) | repo pubblica |

- Codice, commenti e commit in **inglese** (conventional commit, scope `webapp` per il nostro codice); `docs/` in italiano.
- Non riscrivere la storia di `main` (`rebase -i`, `filter-branch`): rompe i merge da upstream.
- Il raggruppamento dei duplicati è voluto: le copie della stessa offerta condividono il verdetto.
