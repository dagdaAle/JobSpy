# CLAUDE.md — JobSpy

**Fork** di [`speedyapply/JobSpy`](https://github.com/speedyapply/JobSpy) con due
aggiunte nostre: `webapp/` (FastAPI + SQLite + React/Vite che organizza le offerte
in canali e le valuta con DeepSeek contro il CV) e gli helper per il mercato
italiano in `jobspy/presets.py`. In produzione su `jobspy.intecha.dev`, dietro
Authentik (gruppo `utenti-app`), ed esposto a Claude via MCP (`jobspy` / `jobspy_scrittura`).

## Due zone, due regole

Questa è **la** cosa da capire su questa repo:

| Zona | Cosa è | Come trattarla |
|---|---|---|
| `jobspy/` | Libreria **upstream** | Toccare il minimo indispensabile. Ogni modifica qui è un conflitto al prossimo merge da upstream. Le aggiunte italiane stanno isolate in `presets.py` proprio per questo. |
| `webapp/` | **Nostro**, non esiste upstream | Zona libera. Qui si lavora normalmente. |

Prima di modificare qualcosa in `jobspy/`: chiedersi se la stessa cosa si può fare
in `webapp/` o in `presets.py`. Quasi sempre sì.

## Da non toccare

| Elemento | Regola | Perché |
|---|---|---|
| Il database in `/data` (volume `feedback-data`) | Non ricreare, non migrare senza copia | Contiene le **44 valutazioni**: giudizi tuoi su offerte reali. Non sono rigenerabili — DeepSeek riparte da zero e dà risposte diverse. Sul server **non c'è backup** (rilievo DAT-01). |
| `webapp/cv/cv.pdf` | Montato **read-only** nel compose | L'analyzer ne estrae il testo all'avvio. Non è nella repo (ed è giusto: è un dato personale) — se manca, l'analisi parte senza contesto invece di fallire. |
| `.github/workflows/publish-to-pypi.yml` | Non attivare | È il workflow **di upstream**: pubblicherebbe il nostro fork su PyPI come `python-jobspy`. |
| `TZ=Europe/Rome` nel compose | Non rimuovere | Lo scheduler fa il refresh giornaliero alle 09:00: senza TZ è 09:00 UTC, cioè le 11 d'estate. |
| `DEEPSEEK_API_KEY` | Solo da `.env` (git-ignored) | La repo è **pubblica** — lo è per forza, è un fork. Una chiave committata qui è pubblica nell'istante del push. |

## Comandi

```bash
docker compose up -d --build          # app su http://localhost:8080
docker compose logs -f jobspy-web

cd webapp/frontend && npm install && npm run dev    # frontend su :5173
```

Configurazioni già pronte in `.claude/launch.json`: `jobspy-web-docker`,
`frontend-dev`, `webapp-local`.

## Regole operative

- **Inglese**, in questa repo: codice, commenti e commit (`feat(webapp): group
  duplicate offers…`). È un fork — conventional commit e lingua di upstream
  servono a tenere i diff leggibili contro `speedyapply/JobSpy`.
  *(È l'eccezione: le altre repo INTECHA sono in italiano.)*
- Prefissare lo scope quando si tocca il nostro codice: `feat(webapp):`, `fix(webapp):`.
- Il frontend compila in `webapp/static`, servito da FastAPI. `npm run build`
  prima di un deploy che cambia il frontend.
- **Stesso stack di HNWatch e SubitoWatch** (FastAPI + SQLite + React/Vite +
  Docker + server MCP). Una soluzione trovata qui vale probabilmente anche là:
  conviene allineare le tre invece di farle divergere.

## Cosa non fare

- **Non mettere niente di segreto o personale in questa repo.** È pubblica. Vale
  per chiavi, CV, dati delle offerte, screenshot con nomi di aziende.
- **Non riscrivere la storia di git** (`rebase -i`, `filter-branch`) sul ramo
  principale: è un fork, e riscrivere rende impossibile il merge da upstream.
- **Non aggiornare da upstream senza guardare `jobspy/model.py`**: le firme
  cambiano, e `webapp/` le usa.
- Non rimuovere il raggruppamento dei duplicati "perché sembra un bug": è
  volontario, le copie della stessa offerta condividono il verdetto.

## Riferimenti

- `README.md` — API della libreria (documentazione upstream + helper italiani)
- Upstream: https://github.com/speedyapply/JobSpy
- Repo gemelle: `dagdaAle/hnwatch`, `dagdaAle/SubitoWatch`
- Vault Obsidian, `server/STATO-SERVER.md` — dove gira e come è esposta
