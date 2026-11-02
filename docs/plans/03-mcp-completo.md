# MCP completo — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** Hermes fa tutto quello che fa Ale nella UI.

**Spec:** [ARCHITECTURE.md](../ARCHITECTURE.md) (MCP). Il codice dei tool sta in `intecha-mcp` (`servers/`).

**Dipende da:** piano 01 (filtri canale in produzione). Non serve aspettare il piano 02: i tool chiamano le rotte di oggi e si aggiornano dopo.

## Passi

- [ ] `jobspy_write__update_channel` (nome, filtri: `include_keywords`, `exclude_keywords`, `exclude_companies`, `work_mode`).
- [ ] `create_channel` accetta i filtri.
- [ ] Lettura CV: `list_cvs`, `get_cv` (markdown, senza PDF).
- [ ] Scrittura CV: `tailor_cv` (offerta → CV adattato), `review_cv`, `set_default_cv`.
- [ ] Nella console MCP: i nuovi tool compaiono nei server `jobspy` / `jobspy_write`, profili aggiornati.
- [ ] Test in `intecha-mcp` con risposte registrate.

## Fatto quando

Per ogni rotta dell'API c'è un tool o un'esclusione motivata scritta in ARCHITECTURE.md.
