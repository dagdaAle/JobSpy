# MCP completo — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** Hermes (generale e `jobs`) fa tutto quello che fa Ale nella UI.

**Spec:** [ARCHITECTURE.md](../ARCHITECTURE.md) (MCP). Il codice dei tool sta in `intecha-mcp` (`servers/`).

**Dipende da:** piano 01 per canali e CV (si può fare subito, sulle rotte di oggi); piani 03 e 04 per tag, preferenze e candidature.

## Subito

- [ ] `jobspy_write__update_channel` e `create_channel` con i filtri (`include_keywords`, `exclude_keywords`, `exclude_companies`, `work_mode`).
- [ ] CV: `list_cvs`, `get_cv` (markdown, senza PDF), `tailor_cv`, `review_cv`, `set_default_cv`.

## Dopo il piano 03

- [ ] `get_offer_evaluation` (componenti, decisione, motivo), `list_tags`, `list_tag_proposals`, `resolve_tag_proposal`,
      `get_preferences`, `update_preferences`, `tag_offer` (tag di Ale).

## Dopo il piano 04

- [ ] `get_application_kit`, `add_application_event`, `attach_application_file`, `set_application_status`.

## Sempre

- [ ] Nella console MCP: i nuovi tool compaiono nei server `jobspy` / `jobspy_write`, profili aggiornati.
- [ ] Test in `intecha-mcp` con risposte registrate.

## Fatto quando

Per ogni rotta dell'API c'è un tool o un'esclusione motivata scritta in ARCHITECTURE.md.
