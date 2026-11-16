> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 05 · Deploy e operations

## Dove gira

| Voce | Valore |
|---|---|
| Dominio | `jobspy.intecha.dev` |
| Piattaforma | Coolify sul server di casa |
| Container | `jobspy-api` (porta 8000) |
| Id servizio Coolify | DA VERIFICARE. Il volume si chiama `gexnfxjumzlpglzxbfpdxymp-jobspy-data`: il prefisso è probabilmente l'uuid della risorsa |
| Auth | Authentik forward-auth, gruppo `utenti-app` |
| Rete | rete Docker interna condivisa con `mcp-backend` (intecha-mcp) |
| Repliche | **una**. Mai `uvicorn --workers > 1` (ADR-003) |

## Build

`webapp/Dockerfile`, multi-stage:

1. `node:22-slim`: `npm ci` e `npm run build` del frontend.
2. `python:3.11-slim`: installa `webapp/requirements.txt`, poi la libreria `jobspy` con `--no-deps`, copia **tutti** i `webapp/*.py` e la build statica.
3. `uvicorn app:app --host 0.0.0.0 --port 8000`.

## Come si aggiorna

1. Branch + PR su `dagdaAle/JobSpy`, merge su `main`.
2. **Se la modifica tocca il DB: backup coerente prima** (vedi sotto).
3. Deploy da Coolify. DA VERIFICARE se il deploy parte da solo al push su `main` o va lanciato a mano.
4. Controllo: `GET /status` (analizzatore configurato, CV caricato) e `/logs`.

## Healthcheck

Non c'è un endpoint di health dedicato né un `HEALTHCHECK` nel Dockerfile. `GET /status` fa da controllo. DA VERIFICARE se in Coolify è configurato un healthcheck.

## Backup

| Livello | Cosa | Quando | Retention |
|---|---|---|---|
| App | `storage.backup_db("daily")`, SQLite online backup in `/data/backups` | a ogni giro dello scheduler (09:00) | 14 giornalieri; le copie con altri tag restano |
| NAS | pull dal NAS: script `~/backup/jobspy/pull.sh` dell'utente `nas`, attività DSM "JobSpy backup notturno" | 03:00 | 14 giornalieri + 12 mensili |
| Dashboard | `backup.intecha.dev` (backup-monitor) controlla i job | | |

Come funziona il pull: il NAS entra sul server con una chiave dedicata limitata a un solo comando (`jobspy-backup-stream`), che fa la copia coerente del DB dentro `jobspy-api` e la manda su stdout. La copia si scarta se `integrity_check` non è ok o `feedback_events` è vuota. Log: `~/backup/jobspy/pull.log` sul NAS. Dal 12/11/2026 il NAS raggiunge il server via Tailscale.

**Ripristino** (provato il 02/11/2026 in locale): fermare `jobspy-api`, copiare il file in `/data/feedback.db` del volume, riavviare. Prova locale: avviare l'app con `FEEDBACK_DB=<copia>` e controllare `/status`, `/channels`, `/jobs`.

**Backup manuale prima di un deploy** che tocca il DB: copia coerente con l'API di backup di SQLite (`sqlite3 .backup`), mai una copia a caldo del file. DA VERIFICARE il comando esatto usato finora sul server.

## Log

- `stdout` del container (prefissi `[scheduler]`, analisi): log di Coolify / `docker logs jobspy-api`.
- Pagina **Log** dell'app = tabella `refresh_log` (anche via MCP `get_logs`).
