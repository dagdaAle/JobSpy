# Feature Specification: CV match e adattamento verificato

**Feature Branch**: `feat/cv-match`

**Created**: 2026-11-25

**Status**: Draft

**Input**: "Integriamo Resume-Matcher nel nostro backend: il motore va nel backend, poi design Penpot e frontend."

## Contesto

L'adattamento attuale (`POST /cvs/tailor`) riscrive tutto il CV in una sola chiamata, senza parole chiave,
senza punteggio e senza controllo dei fatti. Portiamo il metodo di
[srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) (Apache-2.0): estrazione dei requisiti
dall'annuncio, punteggio ATS deterministico, parole chiave confermate dall'utente, modifiche puntuali
verificate. Modello: DeepSeek, con il client già usato da `analyzer.py`.

## User Scenarios

### US1 - Vedo quanto il CV corrisponde all'offerta (P1)
Nel dettaglio di un'offerta, il pannello «CV per questa offerta» mostra il punteggio 0-100 del CV scelto,
il dettaglio delle 5 componenti e le parole chiave dell'annuncio, divise in trovate e mancanti.

### US2 - Confermo le parole chiave che ho davvero (P1)
Sulle mancanti spunto «ce l'ho». Solo quelle spuntate possono entrare nel CV adattato.

### US3 - Ottengo modifiche puntuali e verificate (P1)
«Adatta CV» propone fino a 12 modifiche prima/dopo, ognuna con il motivo e le parole chiave che porta.
Le modifiche che aggiungono o tolgono numeri, nomi o tecnologie non confermate sono scartate e contate.
Accetto o scarto ognuna; il salvataggio crea un CV «adattato» e mostra il punteggio prima → dopo.

## Requisiti

- FR-001 Estrazione dei requisiti dall'annuncio con DeepSeek, salvata per offerta (tabella `job_keywords`).
- FR-002 Punteggio deterministico, pesi: parole chiave 40, competenze 20, titolo 15, sezioni 15, date 10.
  Una componente non valutabile vale `null` e il suo peso si ridistribuisce.
- FR-003 Confronto a parola intera, senza distinzione di maiuscole ("java" non trova "javascript").
- FR-004 Ogni modifica passa `cv_review`-style validation (estratto letterale unico, non sovrapposto,
  niente titoli di sezione) e il controllo fatti (`fact_violations`), con le sole parole confermate ammesse.
- FR-005 `POST /cvs/tailor` resta compatibile: senza `patches` genera la proposta e applica le modifiche valide.
- FR-006 Il punteggio è una stima di JobSpy, non quello di un ATS reale: la pagina lo dice.
- FR-007 File portati da Resume-Matcher con intestazione di attribuzione e `NOTICE` nella radice.

## Fuori scope
Sinonimi e traduzioni delle parole chiave, lettera di presentazione, PDF diverso dall'attuale.
