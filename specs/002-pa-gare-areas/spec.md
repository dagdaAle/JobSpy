# Feature Specification: aree Concorsi PA e Gare P.IVA

**Feature Branch**: `feat/pa-gare-areas`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "Implementiamo la parte di pubblica amministrazione e la proposta per la P.IVA
(gare TED), ma devono rimanere 3 cose staccate sia a livello di codice che di frontend."

## Contesto

Oggi JobSpy segue solo offerte di lavoro dipendente (freehire, LinkedIn, Indeed…). Ale vuole altre due
cose, tenute separate dal lavoro:

- **Concorsi PA**: bandi della pubblica amministrazione italiana. Fonti: inPA (API pubblica, già usata da
  `jobspy/inpa` per i canali lavoro) e la **Gazzetta Ufficiale 4ª serie speciale "Concorsi ed esami"**, che
  inPA non copre del tutto (enti che pubblicano solo in GU, esami di abilitazione).
- **Gare P.IVA**: gare d'appalto per lavori da P.IVA o da azienda (Intecha). Fonte: **TED** (Tenders
  Electronic Daily), API pubblica senza chiave dell'UE, filtrabile per paese e codice CPV.

Decisioni prese con Ale (25/11):

- **Stessa app, tre aree**: un container, un DB SQLite (ADR 003), login Authentik, scheduler e CV in comune.
  Codice, tabelle, API e pagine di ogni area sono separati.
- **Valutazione AI sul CV** anche per concorsi e gare, con prompt e punteggio propri di ciascuna area.
- **Tool MCP** delle due aree: dopo, in una PR separata su intecha-mcp.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Area Concorsi PA (Priority: P1)

Ale apre l'area «Concorsi PA», crea un canale (parola chiave, sede, fonte inPA o Gazzetta) e il refresh
giornaliero porta i bandi aperti con ente, sede, scadenza domande e link al bando.

**Why this priority**: è la ricerca che oggi Ale fa a mano e che i canali inPA della parte lavoro coprivano
male (niente scadenza strutturata, niente GU).

**Independent Test**: con risposte registrate di inPA e di un fascicolo GU, creare un canale «informatica,
Verona» e verificare che i bandi entrino nel feed dell'area con scadenza ed ente, e che non compaiano
nell'area lavoro.

**Acceptance Scenarios**:

1. **Given** un canale inPA «informatic», sede «Verona», **When** parte il refresh, **Then** entrano i bandi
   aperti con sede Verona, il Veneto per intero o nazionali, con ente, scadenza e link.
2. **Given** un canale Gazzetta con parola chiave «informatico», **When** parte il refresh, **Then** entrano
   gli atti dei fascicoli degli ultimi 30 giorni il cui titolo o ente contiene la parola, con tipo (concorso,
   avviso, graduatoria…), scadenza se indicata e link all'atto.
3. **Given** lo stesso bando presente su inPA e in GU, **When** entrambi i canali lo riportano, **Then**
   restano due voci (la deduplicazione tra fonti è fuori scope), ciascuna con la sua fonte.
4. **Given** un bando con scadenza passata, **When** si apre il feed, **Then** non compare tra gli aperti
   (resta nell'archivio).
5. **Given** inPA o la GU non rispondono, **When** parte il refresh, **Then** il canale va in errore nel log
   e gli altri canali (anche delle altre aree) proseguono.

---

### User Story 2 - Area Gare P.IVA (Priority: P1)

Ale apre l'area «Gare P.IVA», crea un canale (testo libero, codici CPV, paese, importo massimo) e il
refresh giornaliero porta le gare TED attive con ente appaltante, importo stimato, scadenza offerte e
link all'avviso.

**Why this priority**: è il canale B2B per Intecha/P.IVA che oggi non esiste.

**Independent Test**: con una risposta registrata di TED, creare un canale «CPV 72000000, Italia» e
verificare che le gare entrino nel feed dell'area con importo e scadenza, e non nelle altre aree.

**Acceptance Scenarios**:

1. **Given** un canale con CPV 72000000 e paese Italia, **When** parte il refresh, **Then** entrano le gare
   attive pubblicate negli ultimi N giorni, con titolo, ente, importo stimato, scadenza, luogo e link TED.
2. **Given** un canale con importo massimo 500.000 €, **When** arriva una gara da 3 milioni, **Then** non
   entra nel feed; una gara senza importo entra.
3. **Given** TED risponde con errore o timeout, **When** parte il refresh, **Then** il canale va in errore nel
   log, gli altri proseguono.

---

### User Story 3 - Valutazione AI per area (Priority: P2)

Bandi e gare nuovi passano da un'estrazione AI con prompt proprio dell'area, poi da una valutazione in
codice contro un profilo dell'area (ADR 005 e 007: l'LLM estrae fatti con evidenza, ciò che non sa resta
`null`; la decisione è codice):

- concorsi: l'LLM estrae titolo di studio richiesto, classi di laurea, limiti di età, tipo di contratto,
  numero di posti, area del profilo (informatica, amministrativa, tecnica…); il codice confronta con il
  profilo PA (titoli posseduti, aree di interesse, sedi) e decide adatto / da valutare / non adatto, con
  motivo;
- gare: l'LLM estrae i servizi richiesti (tag a vocabolario: sviluppo software, AI/dati, cloud,
  consulenza, manutenzione, forniture hardware…), requisiti di partecipazione (fatturato minimo,
  certificazioni), subappalto o raggruppamento ammessi, durata; il codice confronta con il profilo Gare
  (servizi offerti, fatturato annuo, certificazioni) e decide allo stesso modo.

Il profilo di ogni area si imposta in una pagina dell'area; cambiarlo non richiede una nuova analisi.

**Why this priority**: senza punteggio i feed PA e gare sono lunghi e poco leggibili.

**Independent Test**: con il client LLM simulato, verificare che un bando nuovo riceva un'analisi salvata
nella tabella dell'area, e che uno scaduto o scartato non venga analizzato.

**Acceptance Scenarios**:

1. **Given** un bando nuovo e l'AI configurata, **When** gira l'analisi, **Then** il bando ha i fatti
   estratti e un esito (adatto / da valutare / non adatto) con motivo.
2. **Given** un bando che richiede una laurea magistrale e un profilo senza magistrale, **When** si valuta,
   **Then** l'esito è «non adatto» con motivo «titolo di studio»; se il titolo richiesto non è noto,
   l'esito è «da valutare».
3. **Given** Ale cambia il profilo, **When** riapre il feed, **Then** gli esiti si aggiornano senza nuove
   chiamate all'AI.
4. **Given** l'AI non è configurata, **When** gira l'analisi, **Then** nessun errore: il feed mostra i bandi
   senza esito.

---

### User Story 4 - Frontend a tre aree (Priority: P1)

In testata Ale sceglie l'area: **Lavoro**, **Concorsi PA**, **Gare P.IVA**. Ogni area ha le sue viste
(feed, preferiti, scartati, archivio, canali) e i suoi filtri; l'area Lavoro resta com'è.

**Independent Test**: cambiare area e verificare che feed, canali e contatori siano solo di quell'area, e
che l'area scelta resti al ricaricamento della pagina.

**Acceptance Scenarios**:

1. **Given** Ale è nell'area Lavoro, **When** passa a Concorsi PA, **Then** vede solo canali e bandi PA.
2. **Given** Ale salva o scarta un bando, **When** torna all'area, **Then** il bando è nella vista giusta e
   non tocca i verdetti dell'area Lavoro.

### Edge Cases

- Fascicolo GU con un atto senza scadenza (graduatorie, rettifiche): entra senza scadenza.
- Atto GU «rettifica» o «riapertura termini»: entra con il suo tipo, così Ale lo riconosce.
- Gara TED con più lotti: si mostra la scadenza più vicina e l'importo totale (somma dei lotti) se noto.
- Gara TED con titolo solo in lingue straniere: si usa il titolo in italiano se c'è, poi l'inglese.
- La GU risponde 200 con «Pagina non trovata»: conta come errore, non come zero risultati.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le aree PA e Gare hanno tabelle proprie (`pa_*`, `gare_*`) nello stesso DB; nessuna tabella
  dell'area Lavoro viene modificata.
- **FR-002**: Il codice di ogni area vive in un pacchetto proprio (`webapp/pa/`, `webapp/gare/`) con
  router FastAPI proprio (`/pa/*`, `/gare/*`); l'unico punto di contatto con `app.py` è: registrazione del
  router, creazione tabelle all'avvio, chiamata del refresh/analisi dentro il giro dello scheduler.
- **FR-003**: Nessun modulo di un'area importa moduli di un'altra area. In comune solo infrastruttura:
  connessione e lock di `storage`, client LLM, testo del CV di default, log del refresh.
- **FR-004**: Connettore inPA dell'area PA con campi strutturati: ente, sede, figura, scadenza, data di
  pubblicazione, link al bando. Filtro sede come `jobspy/inpa` (provincia, regione intera, nazionale).
- **FR-005**: Connettore Gazzetta 4ª serie scritto da zero (il progetto `concorsi_check` non ha licenza):
  indice `/30giorni/concorsi`, pagina di ogni fascicolo, un record per atto con tipo, scadenza, ente,
  titolo, codice atto (es. `26E06298`), link. Una pausa tra le richieste (ADR 004).
- **FR-006**: Connettore TED v3 (`POST https://api.ted.europa.eu/v3/notices/search`, scope `ACTIVE`):
  filtri testo, CPV, paese, giorni di pubblicazione; filtro importo massimo applicato dopo.
- **FR-007**: Ogni area ha canali, verdetti (preferito/scartato), archivio e analisi AI propri.
- **FR-008**: Un refresh al giorno per canale dentro il giro dello scheduler esistente, serializzato;
  un errore di una fonte non ferma le altre (ADR 004).
- **FR-009**: Nei test non si chiamano mai i siti veri: solo risposte registrate.
- **FR-010**: Frontend: selettore di area in testata, stato salvato nell'URL; componenti di ogni area in
  `components/pa/` e `components/gare/`, l'area Lavoro non cambia comportamento.

### Key Entities

- **Canale PA**: nome, fonte (`inpa` | `gazzetta`), parola chiave, sede, risultati massimi.
- **Bando PA**: chiave (fonte + id), titolo, ente, tipo, sede, scadenza, pubblicazione, link, descrizione.
- **Canale Gare**: nome, testo, CPV (lista), paese (ISO3, default ITA), giorni, importo massimo.
- **Gara**: chiave (numero di pubblicazione TED), titolo, ente, CPV, importo stimato, valuta, scadenza,
  luogo, pubblicazione, link.
- **Verdetto** e **Analisi**: per area, legati alla chiave del bando o della gara.

## Success Criteria *(mandatory)*

- **SC-001**: Con i canali di prova, il primo refresh porta almeno un bando inPA, un atto GU e una gara TED,
  ciascuno solo nella sua area.
- **SC-002**: Lavoro invariato: tutti i test esistenti passano senza modifiche.
- **SC-003**: Un errore di TED o della GU durante lo scheduler non impedisce il refresh dei canali lavoro.

## Assumptions

- Le gare TED sono sopra soglia UE (servizi ≈ 140k €): per una P.IVA sono soprattutto subappalto o
  raggruppamento. Le gare sotto soglia (ANAC, piattaforme regionali) sono una fase 2, fuori scope.
- Niente deduplicazione tra inPA e GU in questa fase.
- Candidature strutturate (stati, note) solo per l'area Lavoro; per PA e Gare bastano preferito/scartato.
- I tool MCP di PA e Gare arrivano dopo, in intecha-mcp.
