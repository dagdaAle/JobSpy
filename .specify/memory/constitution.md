# JobSpy Constitution

## Core Principles

### I. Uso personale, repo pubblica

JobSpy serve **solo Ale**: un container sul server di casa dietro Authentik (`jobspy.intecha.dev`).
La repo è un fork **pubblico** di `speedyapply/JobSpy`: niente chiavi, CV, candidature, dati di
offerte o screenshot con nomi, né nel codice né nei documenti né nei fixture dei test. Le chiavi
(es. `DEEPSEEK_API_KEY`) arrivano solo da `.env`, che è git-ignored.

*Perché*: tutto ciò che entra in git è visibile a chiunque.

### II. Due zone, upstream aggiornabile

`jobspy/` è la zona upstream: i file upstream si toccano il minimo, le fonti nostre vivono in
cartelle proprie (`jobspy/<fonte>/`) e sono elencate in `docs/upstream.md`. `webapp/` è nostro.
La storia di `main` non si riscrive (niente `rebase -i` o `filter-branch`): romperebbe i merge da
upstream. Il workflow PyPI di upstream non si attiva mai.

*Perché*: upstream segue i cambi di LinkedIn e Indeed al posto nostro (ADR 001).

### III. I verdetti sono sacri, un solo processo

`feedback` e `feedback_events` sono l'unico dato non rigenerabile: backup coerente del DB
(`/data/feedback.db`) prima di ogni migrazione o deploy che tocca il DB. SQLite con **un solo
processo** che scrive (ADR 003): niente worker separati. Dedup, storico, archiviazione e cache
delle analisi non cambiano di comportamento senza una PR dedicata (ADR 002). Il raggruppamento dei
duplicati è voluto: le copie della stessa offerta condividono il verdetto.

### IV. Fonti educate

Niente login automatizzati, CAPTCHA aggirati o proxy a rotazione. Un refresh al giorno per canale,
serializzato; una fonte che risponde 403/429 va in errore nel log e si salta fino al giorno dopo.
Un'API pubblica si usa entro i limiti dichiarati e nel rispetto dei suoi termini (niente
ridistribuzione dei dati). Nei test e in CI **mai** i siti veri: solo risposte registrate (ADR 004).

### V. L'LLM estrae, il codice decide

L'LLM estrae fatti e tag dal vocabolario controllato con evidenza; la valutazione è codice
(ADR 005, 006, 007). Ciò che non si sa resta `null`/non noto, mai inventato. La versione del
prompt si incrementa a ogni cambio. Un dato già strutturato da una fonte affidabile si usa così
com'è, senza farlo rideterminare all'LLM.

### VI. Candidature assistite, mai automatiche

Il bot precompila, **l'invio è sempre di Ale** (ADR 008). Lo stato delle candidature vive solo in
JobSpy (ADR 009). Nessuna funzione si candida da sola, nemmeno tramite servizi esterni.

### VII. Testato, semplice, raggiungibile da Hermes

`cd webapp && python -m unittest discover -s ../tests` verde, e build del frontend pulita se
toccato; una PR con test rossi non si consegna. Prima si riusa ciò che c'è, poi la libreria
standard, poi una dipendenza già presente; niente opzioni o astrazioni «per dopo». Ogni nuova
operazione dell'API ha il suo tool in `intecha-mcp`, o un'esclusione motivata.

## Vincoli tecnici

- **Stack**: Python (FastAPI + SQLite) in `webapp/`, frontend React + TS + Vite + Tailwind in
  `webapp/frontend/`, scraper in `jobspy/`. Un solo container, deploy via Coolify.
- **Fuso**: `TZ=Europe/Rome` nel compose non si toglie (il refresh giornaliero è ora italiana).
- **Dati personali**: `webapp/cv/cv.pdf` montato read-only, mai in git.
- **Ricerca**: Verona è il centro, il remoto è in più; bandi PA solo con sede a Verona.
- **Lingua**: codice, commenti e commit in **inglese** (conventional commit, scope `webapp` per il
  nostro codice); `docs/`, spec e piani in **italiano**.

## Flusso di lavoro

- Ogni funzionalità segue spec-kit: `/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`. Ale rivede ogni artefatto prima del passo successivo.
- Ogni lavoro su un **branch dedicato con PR verso `main`** (`dagdaAle/JobSpy`), con `--head`
  esplicito: mai commit diretti su `main`.
- **Merge e deploy solo col via esplicito di Ale.** Un agente non tocca il DB o il `.env` di
  produzione senza il suo via.
- I todo vivono nella todo-app e rimandano a `specs/<feature>/`.

## Governance

Questa constitution riassume `AGENTS.md`, `CLAUDE.md` e gli ADR in `docs/adr/`; in caso di
conflitto valgono gli ADR, poi questa. Modifiche con una PR dedicata che aggiorna versione e data.

**Version**: 1.0.0 | **Ratified**: 2026-11-24 | **Last Amended**: 2026-11-24
