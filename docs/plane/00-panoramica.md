> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# JobSpy — Panoramica

## Cos'è

Fork pubblico di [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) (libreria di scraping di offerte di lavoro) con sopra una **webapp personale** per la ricerca di lavoro di Ale.

Fa quattro cose:

- **Raccoglie** offerte da canali salvati (un canale = un sito + una ricerca), ogni giorno alle 09:00.
- **Toglie i doppioni**: la stessa offerta su più siti o regioni è una sola card, e le copie condividono il verdetto.
- **Valuta** ogni offerta con DeepSeek rispetto al CV (tag, riassunto, decisione).
- **Traccia** preferiti, scarti, candidature e una libreria di CV (anche adattati all'offerta, con export PDF).

Il perché: cercare a mano ogni giorno su LinkedIn, Indeed, inPA e bacheche remote vuol dire ricerche ripetute, doppioni e nessun criterio leggibile. Verona e dintorni sono il centro; bandi pubblici sì, solo con sede in provincia di Verona; il remoto dall'Italia è un'opzione in più.

## Per chi

| Utente | Uso |
|---|---|
| Ale | feed, verdetti, candidature, CV. Da Mac e da telefono |
| Hermes (profilo `jobs`, sul Mac di Ale) | valuta offerte, prepara candidature, aggiorna lo stato via MCP |
| Hermes generale / Claude | riassume le novità, crea canali, registra note via MCP |

App per una persona sola. Niente multi-utente.

## Stato

**In produzione.** Ultimo deploy noto: `main` @ `7aef32d` (PR #15, fix del Dockerfile). DA VERIFICARE che il container in produzione giri proprio su quel commit.

Lavoro in corso: le fasi del piano (`docs/plans/01…07`). La fase 01 (consolidare) è in gran parte chiusa: allineamento a upstream 1.4.1, filtro inPA solo provincia, backup notturno sul NAS. Le fasi 02-07 (backend a strati, tagging a faccette, valutazione a componenti, candidature assistite, MCP completo, frontend per pagine, qualità AI) **non sono iniziate** nel codice. La worktree locale `JobSpy-wt-ai` è sul branch `feat/ai-analysis-channel-filters`, già unito in `main` con la PR #10: non contiene lavoro nuovo.

## Riferimenti

| Cosa | Dove |
|---|---|
| URL | https://jobspy.intecha.dev (dietro Authentik) |
| Repo | https://github.com/dagdaAle/JobSpy — **pubblica** |
| Upstream | https://github.com/speedyapply/JobSpy |
| Server MCP | `jobspy` (lettura) e `jobspy_write` in `intecha-mcp`, via `mcp.intecha.dev` |
| Documenti di progetto | `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/adr/`, `docs/plans/` |

## Stack

| Parte | Tecnologia |
|---|---|
| Backend | Python 3.11, FastAPI, uvicorn, SQLite (`sqlite3` grezzo) |
| Scraping | libreria `jobspy/` (fork upstream + fonti italiane e remote) |
| LLM | DeepSeek (`deepseek-chat`) via client `openai` |
| CV | pdfplumber, reportlab, pypdf, pypdfium2 |
| Frontend | React 18 + TypeScript + Vite, TanStack Query, shadcn/Base UI, Tailwind 4 |
| Deploy | Docker multi-stage, Coolify, Authentik |

## Pagine

- 01 · Architettura
- 02 · Modello dati
- 03 · API e tool MCP
- 04 · Configurazione
- 05 · Deploy e operations
- 06 · Runbook
- 07 · Decisioni (ADR)
- 08 · Sviluppo locale
