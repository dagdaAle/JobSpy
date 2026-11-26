# Feature Specification: app iOS nativa (area Lavoro)

**Feature Branch**: `feat/mobile-api-spec` (spec, docs, test del gate) · `feat/ios-app` (app)

**Created**: 2026-11-26

**Status**: Draft

**Input**: piano «App iOS native (Swift)» del 26/11/2026: app SwiftUI per JobSpy, v1 solo area Lavoro, design Penpot I1–I6.

## Contesto

Da telefono oggi c'è solo la web app responsive dietro Authentik. Un'app nativa non può fare il login web di
Authentik: per questo esiste già il gate `/mobile/<rotta>` con `X-Api-Key` (PR #26). Questa feature mette per
iscritto il contratto che l'app usa e aggiunge l'app SwiftUI in `ios-native/`, sullo stesso schema di HNWatch.
Il backend non cambia comportamento: l'app usa le rotte che usa la web app.

## User Scenarios

### US1 - Apro il feed e capisco cosa fare oggi (P1)
Tab Feed: titolo grande, canali come chip scorrevoli, card colorate dalla decisione (Candidati, Valuta, Non noto;
Lascia nascoste finché non le chiedo). Swipe a sinistra = Scarta con «Annulla», segnalibro = Preferito.
Banner in cima se l'AI non è configurata o se ci sono analisi in corso. Pull-to-refresh.

### US2 - Leggo il dettaglio e il perché (P1)
Tutta la card apre il dettaglio: testa colorata con badge, azienda · luogo · modalità, titolo, motivo, tre numeri
(RAL, punteggio AI, età e fonti). Scheda «Valutazione»: Fattibilità, Corrispondenza, Interesse, Carriera,
Condizioni; una componente non nota è tratteggiata con «dati insufficienti», mai bassa. Azioni in basso:
Scarta / Prepara candidatura (crea la candidatura «Da candidare»), apri annuncio, condividi.

### US3 - Adatto il CV a un'offerta (P1)
Scheda «CV per questa offerta»: scelgo il CV base, vedo anello 0–100 e 5 barre pesate, parole trovate e mancanti.
«Scegli le parole chiave» apre uno sheet con «ce l'ho» per le mancanti; «Adatta CV» apre lo sheet delle modifiche
prima → dopo con casella; «Salva CV adattato · N» crea la copia. Attese lunghe (LLM) con stato di attesa visibile;
409 = «il CV è cambiato, rigenera».

### US4 - Seguo le candidature (P2)
Tab Candidature: lista raggruppata per stato, avviso ambra in cima se ci sono richiami scaduti.

### US5 - Rivedo preferiti, scartati e archivio (P2)
Tab Preferiti con selettore Preferiti / Scartati / Archivio; «Togli dai preferiti», «Rimetti tra le offerte».

### US6 - Canali, ricerca, impostazioni (P3)
Elenco canali con stato dell'ultimo aggiornamento e «Aggiorna» (scraping, attesa lunga). Tab ricerca sulle offerte
già caricate. Impostazioni: URL del server e chiave (nel Keychain), prova della connessione.
Menu dell'area in alto a sinistra: Lavoro attivo, Concorsi PA e Gare P.IVA disabilitati «presto».

## Requisiti

- FR-001 Tutte le chiamate vanno a `<URL>/mobile/<rotta>` con header `X-Api-Key`; contratto in `contract.md`.
- FR-002 URL e chiave si inseriscono nelle Impostazioni; la chiave sta nel Keychain, mai nel binario.
  In Debug si possono precompilare da `Config/Secrets.xcconfig` (gitignored).
- FR-003 401 → «chiave non valida» con link alle Impostazioni; 503 → «accesso mobile non configurato» o
  «manca la chiave DeepSeek»; 502 → fonte o modello non raggiungibile; 409 sul salvataggio CV → rigenera.
- FR-004 La decisione e le 5 componenti si calcolano sul client con le stesse regole della web app
  (`decision.tsx`, `JobDetailSheet.tsx`, `JobCard.tsx`); il non noto resta non noto.
- FR-005 Date `YYYY-MM-DD HH:MM:SS` del backend lette come UTC; date pure `YYYY-MM-DD` come giorni di calendario
  in Europe/Rome.
- FR-006 Mappe `analysis`, `feedback`, `applications` indicizzate per `job_url` così come arriva (niente
  conversione delle chiavi).
- FR-007 Timeout lunghi (5 min) su refresh canale, match, proposta e salvataggio CV; 30 s sul resto.
- FR-008 Errori sempre visibili (toast o stato d'errore), stati vuoti e di caricamento, rilettura al ritorno
  in primo piano.
- FR-009 Colori dai token del brief Penpot in Asset Catalog con variante scura; verde solo per «Candidati».
- FR-010 Accessibilità: etichette su bottoni a sola icona, righe raggruppate, target 44, Dynamic Type.
- FR-011 Repo pubblica: fixture e screenshot solo con dati finti («Azienda Esempio Srl», «Mario Rossi»).

## Fuori da questa feature (v2)

Aree PA e Gare, editor e caricamento CV, nuovo canale e modifica canali, analytics, log, notifiche push, widget,
ricerca su freehire, dettaglio candidatura con kit e bot.

## Success Criteria

- SC-001 Dal feed al dettaglio di un'offerta in un tocco; decisione e motivo leggibili senza scorrere.
- SC-002 Un CV adattato si salva dal telefono senza passare dalla web app.
- SC-003 `xcodebuild test` verde sul simulatore e test backend verdi.
