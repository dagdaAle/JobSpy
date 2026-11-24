# Quickstart: provare freehire in JobSpy

## Test (senza rete)

```bash
cd webapp && python -m unittest discover -s ../tests
```

Coprono: traduzione delle zone, `ignored_params`/`ignored_values` → errore, URL LinkedIn normalizzato e unito
alla riga esistente, `job_sources` non cancellata da un refresh LinkedIn, sospette fuori dalla coda,
chiusura con e senza verdetto, 404 durante il controllo, canale per azienda, ricerca al volo che non salva.

## In locale

```bash
docker compose up -d --build          # mai `down -v`
```

1. Webapp → Nuovo canale → sorgente «freehire», parola chiave «LLM engineer», zona «Europa», solo remoto,
   7 giorni → il primo refresh riempie il feed.
2. Nuovo canale → freehire → «Segui un'azienda» → cerca «Acme» → crea.
3. Pagina «Cerca su freehire» → «AI engineer», Italia, 7 giorni → salva un risultato → compare nel feed.
4. Dopo il refresh automatico delle 09:00, nella pagina Log compare la riga «Chiuse alla fonte (freehire)».

## Smoke dal vivo (una volta, a mano, non in CI)

```bash
curl -s 'https://freehire.me/api/v1/jobs/search?q=LLM&regions=eu&work_mode=remote&posted_within_days=7&limit=3'
```

## Deploy (solo col via di Ale)

1. Backup coerente di `/data/feedback.db`.
2. Deploy da Coolify; la migrazione crea `job_sources` e `channels.company_slug` all'avvio.
3. Creare i 3 canali iniziali (spec, Assumptions).
