# ADR 005 — L'LLM valuta, ma "non so" resta non noto; cache per contesto

- Data: 02/11/2026
- Stato: in vigore; la parte sul punteggio è superata da [007](007-score-a-componenti.md) quando il piano 03 è in produzione

## Contesto

DeepSeek valuta ogni offerta contro il CV. Senza regole un modello inventa punteggi su annunci vuoti o tratta un dato
mancante come negativo.

## Decisione

- Output solo JSON a schema; punteggio `null` e confidenza `low` se CV o descrizione sono scarsi.
- Distanze, tempi di viaggio, permessi di lavoro e RAL non si inventano.
- CV e annuncio sono dati non attendibili: le istruzioni al loro interno si ignorano.
- Ogni analisi porta un `context_key` = hash(modello, versione del prompt, testo del CV). Un cambio di uno dei tre
  invalida le analisi; le analisi `legacy` restano valide.
- `PROMPT_VERSION` si incrementa a ogni cambio significativo del prompt.

## Conseguenze

- Cambiare prompt costa una rianalisi: la PR #10 la limita alle offerte attive.
- Dal piano 05 ogni PR che tocca prompt o soglie allega il report di misura.
