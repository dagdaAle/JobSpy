# ADR 009 — Candidature: JobSpy è l'unica fonte di verità

- Data: 02/11/2026
- Stato: proposta (scelta di Claude, da confermare)

## Contesto

Oggi lo stato delle candidature sta in due posti: `applications` in JobSpy (5) e le cartelle `offerte/<azienda>-<ruolo>/stato.md`
del bot `jobs` (6). Non si allineano.

## Decisione

- Stato, passi, date, CV usato e risposte dichiarate vivono in JobSpy (`applications`, `application_events`, `application_files`).
- Il bot scrive via MCP; la cartella locale tiene solo i file e i dati anagrafici, che non vanno sul server.
- Le 6 cartelle esistenti si importano una volta in JobSpy.

## Conseguenze

- Servono i tool MCP per eventi e allegati (piano 05).
- La skill/SOUL del bot `jobs` va aggiornata: `stato.md` non è più la traccia ufficiale.
