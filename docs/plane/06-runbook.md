> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 06 · Runbook

| Sintomo | Causa | Fix |
|---|---|---|
| "Failed to fetch" nella UI, l'AI sembra assente | sessione Authentik scaduta con la scheda aperta: i `fetch` in background ricevono un 302 verso il dominio di Authentik | ricaricare la pagina. Le sessioni Authentik sono state portate a quattro settimane (17/09/2026) |
| La stessa offerta compare molte volte (una per regione) | URL diversi per la stessa offerta | dedup per titolo + azienda normalizzati in `storage.py`; le copie condividono il verdetto. Se manca titolo o azienda non si raggruppa: voluto |
| Il container non parte dopo l'aggiunta di un modulo in `webapp/` | il Dockerfile copiava solo alcuni file | fix `27eb869`: si copia `webapp/*.py`. Un modulo nuovo fuori da `webapp/` va aggiunto al Dockerfile |
| Bandi inPA nazionali (Formez PA, ISS…) nei canali "Verona" | il connettore considerava "in zona" anche le sedi nazionali | fix `8b265ba` (PR #14): si tengono solo i bandi con sede nella provincia richiesta |
| Analisi in errore (9% delle esecuzioni al 02/11/2026) | DA VERIFICARE: le cause non sono ancora state analizzate (primo passo del piano 07) | rilanciare con `POST /maintenance/analyze` (tool `analyze_backlog`); l'errore è in `analysis_runs.error` |
| Nessuna analisi, `/status` dice analizzatore non configurato | `DEEPSEEK_API_KEY` mancante o CV non letto | controllare le variabili in Coolify e il file `CV_PATH` |
| Il refresh non parte alle 09:00 o parte a un'ora sbagliata | `TZ` tolta dal compose / dall'ambiente | rimettere `TZ=Europe/Rome` |
| Un sito restituisce 0 offerte o errore 403/429 | blocco anti-scraping dall'IP di casa | niente proxy né login (ADR-004): si aspetta il giorno dopo e si tengono pochi canali per sito. Errore visibile in `/logs` |
| Dopo un merge da upstream una fonte o la webapp si rompe | cambiate `Scraper`, `JobPost` o le colonne del DataFrame in `jobspy/model.py` | seguire `docs/upstream.md`: riapplicare le registrazioni, adattare le fonti, riallineare `requirements.txt`, test, smoke con `results_wanted=3` |
| Pull notturno sul NAS fallito | cambi di rete o Tailscale sul NAS non ripartito dopo un riavvio (13/11/2026) | controllare `pull.log` sul NAS e la dashboard `backup.intecha.dev`; dettagli nella nota vault `server/NAS-hermes` |
| L'attività DSM del backup non parte con "Esegui" | id dell'attività riusato da un task cancellato (osservato il 02/11/2026) | lanciare lo script a mano; se serve, ricreare l'attività dall'interfaccia DSM |
| Si vuole rianalizzare le analisi vecchie `legacy` | restano valide apposta per non ripagarle | `UPDATE analysis SET context_key = '' WHERE context_key = 'legacy'`, poi `/maintenance/analyze`. Costa token |
| Perso un verdetto / DB rovinato | | ripristino da `/data/backups` o dal NAS (05 · Deploy). Mai `docker compose down -v` in locale: cancella il volume |
