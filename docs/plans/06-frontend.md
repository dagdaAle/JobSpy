# Frontend per pagine — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** una rotta per pagina, client generato, feed per decisione, scheda per componenti, pagine Tag, Preferenze e pipeline Candidature.

**Spec:** [DESIGN.md](../DESIGN.md).

**Dipende da:** piano 02 (`/api/v1` e `openapi.json`), piano 03 per feed e scheda, piano 04 per le candidature.

## Passi

- [ ] Router con le rotte di DESIGN.md; `?cv=` diventa `/cv/:id` con redirect.
- [ ] Client generato da `openapi.json` al posto di `api/client.ts` e `api/types.ts` scritti a mano.
- [ ] Token Lumina in `index.css` (colori, raggi, font) senza cambiare i componenti shadcn.
- [ ] Feed: ordinato per decisione (`candidati` → `valuta`), `lascia` come filtro; filtri per faccetta; copie come una card.
- [ ] Scheda offerta con le cinque righe delle componenti e i tag con evidenza.
- [ ] Pagina Tag (vocabolario, coda proposte) e pagina Preferenze (pesi, affinità, ricalcolo).
- [ ] Pipeline candidature e pagina candidatura (kit, eventi del bot, screenshot, "Invia" / "Segna inviata").
- [ ] Layout telefono: menu in basso, scheda offerta a schermo intero.
- [ ] Togliere gli alias delle rotte vecchie quando frontend e MCP usano `/api/v1`.

## Fatto quando

Ogni pagina ha un URL, nessun tipo scritto a mano, Lighthouse accessibilità ≥ 95 su feed e offerta.
