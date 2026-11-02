# DESIGN — come si presenta

> Stato: bozza del 02/11/2026. Il perché sta in [PRODUCT.md](PRODUCT.md), le API in [ARCHITECTURE.md](ARCHITECTURE.md).
> Descrive la UI di oggi e la direzione; le voci marcate **(scelta di Claude)** vanno confermate, idealmente su mockup prima del codice.

## Principi

1. **La decisione prima dell'elenco.** Il feed apre su "a cosa mi candido oggi?": le offerte `apply` in cima con il motivo
   in una riga, poi `maybe`. Le `skip` sono un filtro, non il contenuto.
2. **Il motivo è il contenuto.** Ogni offerta dice perché vale o non vale (bloccanti, sede, remoto riservato ad altri paesi,
   requisiti mancanti). Il punteggio da solo non basta mai.
3. **Il non noto si vede.** Punteggio `null`, RAL assente, modalità `unknown` hanno un aspetto proprio, diverso da "basso" e da "ok".
4. **Un gesto, un'azione.** Preferito, scarto, ripristino: un clic, nessuna conferma per azioni reversibili, toast con "Annulla".
5. **Calma.** Il verde è riservato ad `apply`, il rosso agli errori delle fonti. Niente badge colorati per ogni tag.
6. **Una sola offerta, ovunque.** Le copie della stessa offerta da siti diversi si mostrano come una card con le fonti elencate.

## Base visiva

Oggi: shadcn (Base UI) + Tailwind 4, font Geist, tema chiaro/scuro con `next-themes`, icone Lucide.
È lo stesso stack della console MCP ([intecha-mcp-console adr/003](https://github.com/dagdaAle/intecha-mcp-console)),
mentre todo-app e BuyWatcher usano Mantine con i token Lumina.

**(scelta di Claude)**: tenere shadcn (rifare in Mantine non porta nulla all'utente) e allineare **i token** a Lumina
(colori, raggi, Inter/Outfit/JetBrains Mono per numeri e RAL), così le app si somigliano senza riscrivere i componenti.

## Pagine e layout

Oggi una vista unica con header (`AppHeader`) che cambia `view` in stato React, senza URL per pagina tranne `?cv=`.
Arrivo **(scelta di Claude)**: una rotta per pagina (`/`, `/offerta/:id`, `/candidature`, `/cv`, `/cv/:id`, `/analytics`, `/log`),
così link, indietro del browser e Hermes possono puntare a una pagina precisa. Barra laterale su desktop, menu in basso su telefono.

| Pagina | Contenuto | Stati da coprire |
|---|---|---|
| Feed | barra canali (comprimibile), filtri, griglia card | vuoto, nessun canale, analisi in corso, analisi non configurata, errore fonte |
| Offerta | pannello laterale: decisione, motivi, bloccanti, match CV, stack, RAL, lingue, fonti, candidatura | analisi `null`, analisi in errore, offerta archiviata |
| Candidature | tabella per stato, prossimo passo, data di richiamo | nessuna candidatura, richiamo scaduto |
| CV | libreria, editor, anteprima pagine, revisione con modifiche selezionabili | PDF non leggibile, revisione in corso |
| Analytics | KPI, competenze, aziende, settori, remoto per sito | dati insufficienti |
| Log | esecuzioni per canale e analisi, errori | refresh interrotto |

## Card offerta

- Titolo, azienda (logo se c'è), sede e modalità (`remote / hybrid / onsite / unknown`), età dell'offerta.
- Decisione `apply / maybe / skip` e una riga di motivo; punteggio come numero secondario.
- RAL in monospace solo se scritta nell'annuncio, altrimenti "RAL non indicata".
- Fonti come puntino + nome (LinkedIn, Indeed, inPA, ...), non come sfondo.

## Accessibilità

- Contrasto AA in entrambi i temi; la decisione non è comunicata solo dal colore (testo + icona).
- Tutte le azioni da tastiera; il pannello offerta chiude con Esc e restituisce il focus alla card.
- Target touch ≥ 44 px su telefono.
