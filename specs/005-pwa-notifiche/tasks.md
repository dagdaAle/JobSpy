# Tasks: PWA e notifiche push

- [x] T001 `frontend/public/`: `manifest.webmanifest`, `sw.js`, icone dal logo; meta iOS in `index.html`; safe area in alto in `AppShell`
- [x] T002 `webapp/push.py`: tabelle, sottoscrizioni, invio con `pywebpush`, pulizia 404/410, router `/push/*`
- [x] T003 Selezione e raggruppamento: Lavoro `apply`, PA `adatto` + scadenze a 3 giorni, Gare `adatto`; limite 12 h per area
- [x] T004 Aggancio in `app.py`: `init_tables` all'avvio, Lavoro dopo l'analisi dello scheduler, PA/Gare dopo `_refresh_areas`
- [x] T005 Vista «Notifiche» in Lavoro → Sistema: stato, attiva, disattiva, prova, interruttori per area
- [x] T006 `tests/test_push.py` offline; build del frontend in `webapp/static/`
- [ ] T007 Prova su iPhone reale dopo il deploy (chiavi su Coolify, app su Home, «Invia prova»)
