# ADR 006 — Tag a faccette con vocabolario controllato

- Data: 02/11/2026
- Stato: proposta (scelta di Claude, da confermare)

## Contesto

Oggi l'LLM restituisce fino a 6 tag liberi per offerta. Risultato: doppioni ("Concorso" / "Concorso Pubblico"),
tag fuori posto ("Onsite Usa", "Pubblica Amministrazione" come competenza), nessun uso possibile per filtri,
confronti o preferenze. Per Ale il tagging è da strutturare meglio.

## Decisione

- I tag hanno una **faccetta** (ruolo, tecnologie, dominio, seniority, modalità, sede, contratto, tipo di datore, condizioni, segnali, tag di Ale).
- Il vocabolario è una tabella versionata con sinonimi. L'LLM sceglie dal vocabolario che riceve nel prompt;
  un termine nuovo va in una coda di proposte che Ale approva, unisce o rifiuta.
- Ogni tag su un'offerta porta la fonte (LLM, regola, Ale) e, se LLM, la frase dell'annuncio come evidenza.
- Sede, distanza da Verona e agenzie note si decidono con regole, non con l'LLM.
- Il CV si tagga con lo stesso vocabolario.

## Perché

- Filtri, analytics e preferenze funzionano solo su un insieme chiuso e pulito.
- L'evidenza rende verificabile ogni tag e misurabile la precisione.

## Conseguenze

- Il primo vocabolario si costruisce dai tag liberi già presenti (raggruppati e ripuliti), poi si rivede con Ale.
- Un cambio di vocabolario incrementa la versione di estrazione: si rifà l'estrazione solo delle offerte attive.
