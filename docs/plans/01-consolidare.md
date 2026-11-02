# Consolidare PR, upstream, dati e fonti — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** niente lavoro fermo su branch, fork allineato, dati al sicuro fuori dal server, inPA solo su Verona.
Nessun cambio di architettura.

**Spec:** [PRODUCT.md](../PRODUCT.md) (decisioni prese, decisioni 1-4), [adr/001](../adr/001-fork-due-zone.md), [adr/003](../adr/003-sqlite-un-processo.md).

## PR aperte

- [ ] Mergiare [#11](https://github.com/dagdaAle/JobSpy/pull/11) (ignora `graphify-out/`).
- [ ] Rebase di [#10](https://github.com/dagdaAle/JobSpy/pull/10) su `main`, test verdi (`cd webapp && python -m unittest discover -s ../tests`), merge.
      Chiudere [#9](https://github.com/dagdaAle/JobSpy/pull/9) come inclusa in #10.
- [ ] Prima del deploy: backup coerente di `/data/feedback.db`. Dopo: seguire la rianalisi nei log, annotare token e tempo.
- [ ] Aggiornare [#1](https://github.com/dagdaAle/JobSpy/pull/1): `CLAUDE.md` rimanda ad `AGENTS.md`, merge.
- [ ] Cancellare i branch locali già mergiati e il worktree `JobSpy-wt-ai` dopo il merge di #10.

## Upstream

- [ ] Elencare in `docs/upstream.md` i file upstream modificati da noi (`git diff upstream/main origin/main -- jobspy`, solo file esistenti upstream).
- [ ] Merge di `upstream/main` su un branch, conflitti risolti tenendo le nostre fonti, controllo di `jobspy/model.py` contro le colonne usate da `webapp/`.
- [ ] Test verdi + un refresh manuale di un canale LinkedIn e uno Indeed su copia locale del DB. PR, merge, deploy.
- [ ] Da qui in poi: allineamento a ogni rilascio upstream (annotato in `docs/upstream.md`).

## inPA

- [ ] Test rosso: un bando con sola sede nazionale non passa `_in_area` per `location="Verona"`.
- [ ] Fix in `jobspy/inpa` (fonte nostra): i nazionali si escludono quando è data una provincia; i regionali restano solo se citano la provincia.
- [ ] Archiviare i bandi nazionali già nel feed del canale "Concorsi PA Verona" (non cancellarli).

## Dati

- [ ] Copia notturna fuori dal server dell'ultimo backup giornaliero (destinazione con Ale: NAS o spazio remoto cifrato).
- [ ] Retention in `/data/backups`: 14 giornalieri + i backup pre-migrazione.
- [ ] Provare un ripristino su una copia locale.

## Canali

- [ ] Archiviare (o cancellare, finché l'archiviazione non c'è) i 3 canali a 0 risultati: full stack, backend, embedded.
- [ ] Gli altri restano finché il piano 03 non dice quali producono offerte interessanti.

## Fatto quando

Nessuna PR aperta più vecchia di una settimana, fork allineato a upstream, inPA solo Verona, backup fuori dal server con ripristino provato.
