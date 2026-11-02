# Tagging e valutazione a componenti — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** tag a faccette con vocabolario, estrazione separata dal giudizio, valutazione deterministica a componenti
con preferenze imparate dai verdetti.

**Spec:** [PRODUCT.md](../PRODUCT.md) (Tagging strutturato, Valutazione a componenti), [ARCHITECTURE.md](../ARCHITECTURE.md) (flusso, valutazione),
[adr/006](../adr/006-tag-a-vocabolario-controllato.md), [adr/007](../adr/007-score-a-componenti.md).

**Dipende da:** piano 02 (Alembic e repository). Il passo "Con Ale" si può fare subito.

## Con Ale (prima del codice)

- [ ] Mezz'ora su 15-20 offerte già viste (preferite e scartate): cosa le rende interessanti o no. Ne esce la rubrica di Carriera
      e il primo set di preferenze (raggio, contratti, soglia RAL).
- [ ] Rivedere la prima bozza di vocabolario (sotto).

## Vocabolario

- [ ] Script che raggruppa i tag liberi già nel DB (`analysis.tags`, `jobs.skills`) per somiglianza e li propone per faccetta.
- [ ] Tabelle `tags` (faccetta, slug, etichetta, sinonimi, stato) e `offer_tags` (fonte, evidenza) con Alembic.
- [ ] Normalizzatore: sinonimi → tag canonico; termine sconosciuto → proposta.
- [ ] Regole: sede → comune/provincia/km da Verona (tabella comuni ISTAT), agenzie per il lavoro note → tipo di datore.

## Estrazione

- [ ] Schema Pydantic dell'estrazione: tag per faccetta con evidenza, requisiti obbligatori/preferenziali, modalità, sede, contratto,
      RAL come scritta, lingue, voci della rubrica Carriera con evidenza, segnali.
- [ ] Prompt di estrazione che riceve il vocabolario e **non** il CV; output solo JSON a schema; CV e annuncio non attendibili.
- [ ] Tabella `extractions` con versione e token; cache su hash(testo, versione estrazione).
- [ ] Estrazione del CV con lo stesso schema in `cv_profiles`, una volta per versione.
- [ ] Rifare l'estrazione solo delle offerte attive; le analisi vecchie restano in sola lettura.

## Valutazione

- [ ] `preferences` (zone, raggio, contratti, soglia RAL, pesi, affinità fissate) con valori iniziali da "Con Ale".
- [ ] Affinità per tag dai `feedback_events` (preferiti − scarti, smoothing), ricalcolata a ogni verdetto.
- [ ] Servizio `evaluation.py`: gate, quattro componenti, decisione, motivo, confidenza. Funzione pura, test per ogni regola.
- [ ] Ricalcolo di tutte le offerte attive quando cambiano preferenze o CV (nessuna chiamata LLM).
- [ ] API: `GET /api/v1/offers/{id}/evaluation`, `GET/PUT /api/v1/preferences`, `GET /api/v1/tags`, proposte (approva/unisci/rifiuta).

## Fatto quando

Ogni offerta attiva ha tag a faccette con evidenza e una decisione spiegata per componente; cambiare un peso aggiorna il feed
in pochi secondi senza token; il report del piano 07 sul set dei verdetti è migliore del punteggio di oggi.
