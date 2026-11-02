# Qualità AI — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** sapere quanto è buona l'analisi e cambiarla solo con i numeri.

**Spec:** [PRODUCT.md](../PRODUCT.md) (Misurare l'AI), [adr/005](../adr/005-llm-valuta-null-se-non-sa.md).

**Dipende da:** piano 01 (analisi v3 in produzione).

## Passi

- [ ] Capire il 9% di analisi in errore: raggruppare `analysis_runs` in errore per messaggio; fix o test rosso per ogni causa.
- [ ] Set etichettato da `feedback_events`: preferiti = positivi, scarti = negativi, con l'offerta congelata. Salvato **fuori dalla repo** (è pubblica).
- [ ] `scripts/eval_ai.py`: rilancia l'analisi sul set, misura preferiti finiti in `skip`, scarti finiti in `apply`, costo in token.
- [ ] Report di base con prompt e modello di oggi.
- [ ] Prova di un modello locale (Ollama su RTX 3060) sullo stesso set, se Ale lo vuole (PRODUCT, domanda aperta 3).
- [ ] Da qui in poi: ogni PR che tocca prompt, schema o soglie allega il report.

## Fatto quando

C'è un numero che dice quanto l'analisi sbaglia, e il prompt in produzione è il migliore misurato.
