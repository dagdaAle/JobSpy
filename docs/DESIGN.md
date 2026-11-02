# DESIGN — come si presenta

> Stato: bozza del 02/11/2026, seconda versione. Il perché sta in [PRODUCT.md](PRODUCT.md), le API in [ARCHITECTURE.md](ARCHITECTURE.md).
> Le voci marcate **(scelta di Claude)** vanno confermate, idealmente su mockup prima del codice.

## Principi

1. **La decisione prima dell'elenco.** Il feed apre su "a cosa mi candido oggi?": le offerte `candidati` in cima con il motivo
   in una riga, poi `valuta`. Le `lascia` sono un filtro, non il contenuto.
2. **Il motivo è il contenuto.** Ogni offerta dice perché vale o non vale. Il numero da solo non basta mai: si vedono le componenti.
3. **Il non noto si vede.** Componente non nota, RAL non indicata, modalità `non noto` hanno un aspetto proprio, diverso da "basso" e da "ok".
4. **I tag sono filtri, non decorazione.** Ogni tag è cliccabile e filtra il feed; si raggruppano per faccetta, non in fila.
5. **Un gesto, un'azione.** Preferito, scarto, tag, ripristino: un clic, nessuna conferma per azioni reversibili, toast con "Annulla".
6. **Niente parte senza Ale.** Ogni passo di candidatura che il bot fa è visibile; "Invia" è sempre un'azione esplicita di Ale.
7. **Calma.** Verde solo per `candidati`, rosso solo per errori e bloccanti certi.
8. **Una sola offerta, ovunque.** Le copie della stessa offerta da siti diversi sono una card con le fonti elencate.

## Base visiva

Oggi: shadcn (Base UI) + Tailwind 4, font Geist, tema chiaro/scuro, icone Lucide — lo stesso stack della console MCP.
**(scelta di Claude)**: tenere shadcn e allineare **i token** a Lumina (todo-app, BuyWatcher): colori, raggi, Inter/Outfit,
JetBrains Mono per RAL, km e numeri.

## Pagine

Una rotta per pagina **(scelta di Claude)**. Barra laterale su desktop, menu in basso su telefono.

| Pagina | Rotta | Contenuto |
|---|---|---|
| Feed | `/` | barra canali, filtri per faccetta, card ordinate per decisione |
| Offerta | `/offerta/:id` (anche come pannello sul feed) | decisione, motivo, componenti, tag per faccetta con evidenza, fonti, azioni |
| Candidature | `/candidature` | pipeline per stato (colonne su desktop, elenco su telefono), richiami scaduti in cima |
| Candidatura | `/candidature/:id` | kit, cosa il bot ha compilato, screenshot, eventi, "Invia" / "Segna inviata" |
| CV | `/cv`, `/cv/:id` | libreria, editor, anteprima, revisione, tag estratti dal CV |
| Tag | `/tag` | vocabolario per faccetta, coda di proposte (approva / unisci / rifiuta), conteggi |
| Preferenze | `/preferenze` | zona e raggio, contratti, soglia RAL, pesi delle componenti, affinità dei tag (imparate e fissate) |
| Analytics | `/analytics` | per faccetta: offerte, preferiti, scarti, candidature, esiti |
| Log | `/log` | esecuzioni dei canali, estrazione, errori |

## Card offerta

```
┌───────────────────────────────────────────────────────┐
│ ● CANDIDATI   Backend developer Python                 │
│ Azienda Srl · San Giovanni Lupatoto · 6 km · ibrido    │
│ Copre 5/6 requisiti obbligatori; dominio nuovo e vicino│
│ [Python] [FastAPI] [manifattura] [indeterminato]       │
│ RAL non indicata · LinkedIn, Indeed · 2 giorni         │
└───────────────────────────────────────────────────────┘
```

- Decisione come etichetta testuale + icona, non solo colore.
- Riga di motivo generata dalla componente più forte e dal bloccante, se c'è.
- Al massimo 4 tag in card (ruolo, 2 tecnologie, contratto); gli altri nella scheda.

## Scheda offerta: le componenti

| Componente | Come si mostra |
|---|---|
| Fattibilità | ✓ nessun bloccante · ⚠ da verificare (con cosa) · ✕ bloccante (con quale) |
| Corrispondenza | barra "5 di 6 obbligatori" e l'elenco dei mancanti |
| Interesse | barra + i 3 tag che pesano di più, in positivo e in negativo |
| Carriera | voci della rubrica soddisfatte, ognuna con la frase dell'annuncio |
| Condizioni | RAL, contratto, modalità, km — "non indicato" in grigio |

Ogni componente non nota è una barra tratteggiata con "dati insufficienti".

## Stati da coprire

| Dove | Stati |
|---|---|
| Feed | vuoto, nessun canale, estrazione in corso, LLM non configurato, errore fonte |
| Offerta | estrazione in errore, estrazione vecchia (versione precedente), offerta archiviata |
| Tag | coda proposte vuota, tag unito (mostra dove è andato) |
| Candidatura | bot al lavoro, bot fermo (CAPTCHA, login richiesto), invio in attesa dell'ok, richiamo scaduto |
| Preferenze | pesi modificati e non ancora applicati (ricalcolo in corso) |

## Accessibilità

- Contrasto AA in entrambi i temi; decisione e componenti mai solo a colori.
- Tutte le azioni da tastiera; il pannello offerta chiude con Esc e restituisce il focus alla card.
- Target touch ≥ 44 px su telefono.
