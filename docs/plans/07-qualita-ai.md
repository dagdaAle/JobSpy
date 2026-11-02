# Qualità AI — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** sapere quanto sono buoni estrazione, tag e valutazione, e cambiarli solo con i numeri.

**Spec:** [PRODUCT.md](../PRODUCT.md) (Misurare l'AI), [adr/006](../adr/006-tag-a-vocabolario-controllato.md), [adr/007](../adr/007-score-a-componenti.md).

**Dipende da:** piano 01 per il primo passo; piano 03 per il resto.

## Passi

- [ ] Capire il 9% di analisi in errore: raggruppare `analysis_runs` in errore per messaggio; fix o test rosso per ogni causa.
- [ ] Set etichettato da `feedback_events` ed esiti delle candidature, con l'offerta congelata. Salvato **fuori dalla repo** (è pubblica).
- [ ] Campione di 50 offerte con tag rivisti da Ale: precisione per faccetta, quota di termini fuori vocabolario.
- [ ] `scripts/eval_ai.py`: rilancia estrazione (DeepSeek) e valutazione (locale) sul set; misura preferiti finiti in `lascia`,
      scarti finiti in `candidati`, contributo di ogni componente, token.
- [ ] Report di base: punteggio di oggi vs valutazione a componenti sullo stesso set.
- [ ] Calibrare i pesi delle preferenze sul set (ricerca a griglia semplice, niente modelli addestrati).
- [ ] Da qui in poi: ogni PR che tocca prompt, vocabolario o pesi allega il report.

## Fatto quando

C'è un numero che dice quanto estrazione e valutazione sbagliano, e i pesi in produzione sono i migliori misurati.
