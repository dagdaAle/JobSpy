# ADR 007 — L'LLM estrae, la valutazione è deterministica a componenti

- Data: 02/11/2026
- Stato: proposta (scelta di Claude, da confermare)

## Contesto

Il punteggio 0-100 di oggi è deciso dal modello in una sola chiamata che mescola CV, interesse, sede e condizioni.
Non si scompone, non si calibra, e ogni cambio di CV o prompt costa una rianalisi (6,1 M token in sei settimane).
Punteggio medio 21, 654 scarti contro 30 preferiti: per Ale lo score è fatto male.

## Decisione

- **Estrazione** (DeepSeek): fatti e tag a schema con evidenza, indipendenti dal CV e dalle preferenze. Cache su testo + versione.
- **Valutazione** (codice): gate di fattibilità + quattro componenti (corrispondenza, interesse, carriera, condizioni),
  pesi in `preferences`, decisione `candidati / valuta / lascia` con motivo.
- L'interesse si impara dai verdetti come affinità per tag (conteggi con smoothing), leggibile e modificabile da Ale.
- Le componenti non note non contano e abbassano la confidenza.

## Perché

- Spiegabile: si vede quale componente decide.
- Economico: cambiare preferenze o CV non chiama DeepSeek.
- Calibrabile: i pesi si misurano sul set dei verdetti (piano 07).
- Coerente con BuyWatcher ([adr/004 di BuyWatcher](https://github.com/dagdaAle/SubitoWatch)): l'LLM estrae fatti, la convenienza è deterministica.

## Conseguenze

- La PR #10 (decisione `apply/maybe/skip` dall'LLM) si prende come passo intermedio; il piano 03 la sostituisce.
- Il punteggio vecchio resta visibile in sola lettura per le offerte non rianalizzate.
