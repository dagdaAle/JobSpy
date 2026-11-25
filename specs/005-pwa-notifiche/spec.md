# Feature Specification: PWA e notifiche push

**Feature Branch**: `feat/pwa-notifiche`

**Created**: 2026-11-25

**Status**: Draft

**Input**: "JobSpy installabile su iPhone come PWA + notifiche Web Push (VAPID), da iOS 16.4+ con l'app su Home."

## Contesto

Ale controlla JobSpy dal telefono. Oggi deve aprirlo per sapere se il giro delle 9 ha portato qualcosa che conta.
Con l'app sulla schermata Home (PWA) iOS 16.4+ permette le notifiche Web Push: una al giorno per area, solo se
serve, porta Ale direttamente all'area giusta.

## User Scenarios & Testing

### User Story 1 - Installare JobSpy su iPhone (P1)

Da Safari, Condividi → «Aggiungi alla schermata Home»: icona JobSpy, si apre a tutto schermo, la barra in basso
rispetta la safe area.

### User Story 2 - Attivare le notifiche (P1)

Nella vista **Notifiche** (Lavoro → Sistema) Ale vede lo stato del dispositivo e con un tocco le attiva.

1. **Given** Safari su iPhone non installato, **Then** «installa su Home» con le istruzioni.
2. **Given** il server senza chiavi VAPID, **Then** «non configurate sul server»; nessun invio.
3. **Given** il permesso negato, **Then** come riattivarlo dalle impostazioni.
4. **Given** attive, **Then** interruttori per area, «Invia prova», «Disattiva».

### User Story 3 - Una notifica per area dopo il giro delle 9 (P1)

1. **Lavoro**: offerte nel feed con decisione «Candidati» (`assessment.decision = apply`), senza verdetto né
   candidatura, mai notificate prima. Parte alla fine dell'analisi in background avviata dallo scheduler.
2. **Concorsi PA**: bandi nel feed con esito «adatto» mai notificati, più promemoria per bandi salvati o adatti con
   scadenza entro 3 giorni (una volta per bando).
3. **Gare P.IVA**: gare nel feed con esito «adatto» mai notificate.
4. Sempre **una notifica per area** con conteggio e fino a 3 titoli, mai una per elemento; nessuna se zero novità.
5. **Limite**: al massimo una notifica per area ogni 12 ore (`PUSH_MIN_HOURS`); ciò che resta fuori va nella
   successiva. Un invio fallito non segna gli elementi: riprova al giro dopo.
6. Il tocco apre l'area (`/`, `/?area=pa`, `/?area=gare`).
7. Errori di invio o di raccolta finiscono nel log del processo e non fermano lo scheduler.

## Requirements

- **FR-001** Manifest, icone 192/512/maskable, `apple-touch-icon`, meta iOS, `viewport-fit=cover`.
- **FR-002** `/sw.js` alla radice: solo `push` e `notificationclick`, nessuna cache.
- **FR-003** Tabelle `push_subscriptions` e `push_sent` nel DB SQLite (create all'avvio, come le altre).
- **FR-004** API `/push/key`, `/push/subscribe`, `/push/unsubscribe`, `/push/test`, dietro lo stesso login delle altre.
- **FR-005** Chiavi solo da env: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`. Senza: nessun invio.
- **FR-006** Risposta 404/410 del servizio push → la sottoscrizione si cancella.
- **FR-007** Endpoint accettati solo dei servizi push noti (Apple, Google, Mozilla, Microsoft): il server ci fa POST.
- **FR-008** Cosa notificare riusa le decisioni esistenti (ADR 005/007): nessuna regola nuova.

## Fuori scope

- Cache offline, notifiche per singolo elemento, orari di silenzio, link al dettaglio di un'offerta (l'app non ha
  ancora URL per il dettaglio).
- **MCP**: esclusione motivata — la sottoscrizione è legata al browser del dispositivo, non ha senso via agente.

## Note di deploy

- Env su Coolify: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (`mailto:` di Ale), opzionale
  `PUSH_MIN_HOURS`. Generare le chiavi (fuori dalla repo):

  ```bash
  uv run --no-project --with py-vapid python -c 'import base64;from py_vapid import Vapid01;from cryptography.hazmat.primitives import serialization as s;v=Vapid01();v.generate_keys();b=lambda x:base64.urlsafe_b64encode(x).rstrip(b"=").decode();print("VAPID_PRIVATE_KEY="+b(v.private_key.private_numbers().private_value.to_bytes(32,"big")));print("VAPID_PUBLIC_KEY="+b(v.public_key.public_bytes(s.Encoding.X962,s.PublicFormat.UncompressedPoint)))'
  ```

  Cambiare le chiavi invalida tutte le sottoscrizioni: vanno riattivate sui dispositivi.
- **Login (Authentik forward-auth)**: tutto il dominio è dietro il cookie di sessione, anche `/sw.js` e il
  manifest. Il manifest si carica con `crossorigin="use-credentials"` perché altrimenti il browser lo chiede senza
  cookie e riceve il redirect al login; il service worker si registra dalla stessa origine e porta il cookie.
  Le notifiche arrivano anche a sessione scaduta (il push non passa dal proxy); serve il login solo per aprire l'app.
  Se il manifest o l'icona non si caricassero, aggiungere in Authentik come percorsi non autenticati
  `^/(sw\.js|manifest\.webmanifest|icons/.*)$` (file statici senza dati).
