# Frontend per pagine — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** una rotta per pagina, client generato da `openapi.json`, token allineati alle app sorelle, decisione in primo piano.

**Spec:** [DESIGN.md](../DESIGN.md).

**Dipende da:** piano 02 (`/api/v1` e `openapi.json`).

## Passi

- [ ] Router (React Router) con le rotte di DESIGN.md; `?cv=` diventa `/cv/:id` con redirect.
- [ ] Client generato da `openapi.json` al posto di `api/client.ts` e `api/types.ts` scritti a mano.
- [ ] Token Lumina in `index.css` (colori, raggi, font) senza cambiare i componenti shadcn.
- [ ] Feed ordinato per decisione (`apply` → `maybe`), `skip` come filtro.
- [ ] Copie della stessa offerta come una card con più fonti.
- [ ] Layout telefono: menu in basso, pannello offerta a schermo intero.
- [ ] Togliere gli alias delle rotte vecchie quando frontend e MCP usano `/api/v1`.

## Fatto quando

Ogni pagina ha un URL, nessun tipo scritto a mano, Lighthouse accessibilità ≥ 95 su feed e offerta.
