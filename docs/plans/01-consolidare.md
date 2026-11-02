# Consolidare PR, dati e canali — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** niente lavoro fermo su branch, dati al sicuro fuori dal server, canali allineati all'obiettivo.
Nessun cambio di architettura.

**Spec:** [PRODUCT.md](../PRODUCT.md) (decisioni 1-5), [adr/003](../adr/003-sqlite-un-processo.md).

## PR aperte

- [ ] Mergiare [#11](https://github.com/dagdaAle/JobSpy/pull/11) (ignora `graphify-out/`).
- [ ] Rebase di [#10](https://github.com/dagdaAle/JobSpy/pull/10) su `main`, test verdi (`cd webapp && python -m unittest discover -s ../tests`), merge.
      Chiudere [#9](https://github.com/dagdaAle/JobSpy/pull/9) come inclusa in #10.
- [ ] Prima del deploy: backup coerente di `/data/feedback.db`. Dopo: seguire la rianalisi nei log, annotare token e tempo.
- [ ] Aggiornare [#1](https://github.com/dagdaAle/JobSpy/pull/1): `CLAUDE.md` rimanda ad `AGENTS.md` (numeri del 18/09 superati), merge.
- [ ] Cancellare i branch locali già mergiati (`redesign`, `feat/cv-module`, `bug-fix/collapsible-channel-tags`) e il worktree `JobSpy-wt-ai` dopo il merge di #10.

## Dati

- [ ] Copia notturna fuori dal server dell'ultimo backup giornaliero (destinazione da decidere con Ale: NAS o spazio remoto cifrato).
- [ ] Retention in `/data/backups`: 14 giornalieri + i backup pre-migrazione. Oggi 16 file, 559 MB.
- [ ] Provare un ripristino su una copia locale e aprire l'app contro quel DB.

## Canali

- [ ] Con Ale: decidere se Verona resta (PRODUCT, domanda aperta 1).
- [ ] Archiviare (o cancellare, finché l'archiviazione non c'è) i canali a 0 risultati: full stack, backend, embedded.
- [ ] Creare 3-4 canali sul nucleo AI/ML e Python remoti (LinkedIn, Indeed remoto, Remotive, WeWorkRemotely) con i filtri della PR #10.
- [ ] Dopo due settimane: confrontare preferiti/scarti per canale (`get_analytics`) e togliere quelli che non producono preferiti.

## Fatto quando

Nessuna PR aperta più vecchia di una settimana, backup fuori dal server con ripristino provato, canali rivisti con Ale.
