# ADR 001 — Fork con due zone: libreria upstream e webapp nostra

- Data: 02/11/2026
- Stato: in vigore (descrive com'è già la repo)

## Contesto

La repo è un fork pubblico di `speedyapply/JobSpy`. Sopra la libreria di scraping è cresciuta una webapp personale
(`webapp/`) e alcune fonti nuove (inPA, Subito, bacheche remote) dentro `jobspy/`.

## Decisione

- `jobspy/` è zona upstream: si modificano i file esistenti solo se indispensabile, e ogni modifica si annota.
- Le fonti nuove stanno in cartelle proprie sotto `jobspy/` (non toccano file upstream) e gli helper italiani in `presets.py`.
- `webapp/` e `docs/` sono nostri e liberi.
- Il workflow di pubblicazione su PyPI di upstream non si attiva.

## Perché

- Tenere aperta la strada dei merge da upstream (fix agli scraper LinkedIn/Indeed arrivano da lì).
- La repo è pubblica per forza: separare ciò che è libreria da ciò che è app personale aiuta anche a non pubblicare dati.

## Conseguenze

- Prima di ogni allineamento con upstream si controlla `jobspy/model.py`: `webapp/` ne usa le colonne.
- Oggi il fork è 40 commit dietro: l'allineamento è un lavoro a sé (piano 01, opzionale).
