# ADR 004 — Politica delle fonti

- Data: 02/11/2026
- Stato: proposta (scelta di Claude, da confermare; allinea JobSpy a BuyWatcher)

## Contesto

LinkedIn e Indeed bloccano chi interroga troppo. La libreria supporta proxy e rotazione, ma l'app gira dall'IP di casa.

## Decisione

- Nessun login automatizzato, nessun CAPTCHA aggirato, nessun proxy a rotazione.
- Un refresh al giorno per canale (09:00), serializzato. Refresh manuali sì, ma uno alla volta.
- Una fonte che risponde 403/429 passa in errore nel log e si salta fino al giorno dopo.
- Nei test e in CI non si chiamano mai i siti veri: solo risposte registrate.

## Perché

- Il rischio peggiore è perdere l'accesso (IP bloccato) a un sito utile mentre si cerca lavoro.

## Conseguenze

- Il numero di canali per sito va tenuto basso: meglio pochi canali buoni (PRODUCT, decisione 2).
