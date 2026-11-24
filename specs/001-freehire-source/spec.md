# Feature Specification: freehire come sorgente di ricerca

**Feature Branch**: `feat/freehire-source`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Mettiamo freehire per la parte di ricerca e integriamolo meglio: connettore
come sorgente dei canali, usare i dati arricchiti, chiusure da freehire, canali per azienda, ricerca al volo."

## Contesto

freehire è un catalogo pubblico di offerte (4,9M aperte, 52k in Italia) raccolte dai siti di candidatura
delle aziende (Workday, Greenhouse, Lever, SmartRecruiters…), da aggregatori e da LinkedIn, con un'API
pubblica senza chiave (300 richieste/minuto). Ogni offerta arriva già arricchita: stipendio, competenze,
requisiti, lingua, segnale di offerta fantasma, data di chiusura. JobSpy non ha oggi nessuna sorgente dai
siti di candidatura delle aziende; freehire non ha invece Indeed, Glassdoor, Subito, inPA né la ricerca per
raggio. freehire entra quindi come **sorgente in più**: canali, valutazione sul CV, storico e candidature
restano di JobSpy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canali di ricerca su freehire (Priority: P1)

Ale crea un canale con sorgente freehire (parola chiave, zona, solo remoto, recenza), come fa per LinkedIn o
Indeed. Il refresh giornaliero porta le offerte nel feed, con dedup, storico e analisi sul CV come per le
altre sorgenti.

**Why this priority**: è il valore principale: offerte AI/ML remote e dei siti carriere delle aziende che
oggi JobSpy non vede.

**Independent Test**: creare un canale freehire «LLM engineer, Europa, remoto, 7 giorni» con una risposta
registrata, eseguire il refresh e verificare che le offerte compaiano nel feed del canale.

**Acceptance Scenarios**:

1. **Given** un canale freehire con parola chiave, zona «Italia» e solo remoto, **When** parte il refresh,
   **Then** nel feed entrano solo offerte aperte, in Italia o compatibili, da remoto, con link all'offerta
   originale.
2. **Given** un canale con una zona che freehire non sa interpretare, **When** parte il refresh, **Then** il
   canale va in errore nel log con il motivo, senza riempire il feed di offerte non filtrate.
3. **Given** freehire risponde 403/429 o non risponde, **When** parte il refresh, **Then** il canale va in
   errore nel log e gli altri canali proseguono normalmente.
4. **Given** un'offerta LinkedIn che JobSpy ha già dai suoi canali LinkedIn, **When** freehire la riporta,
   **Then** resta una sola offerta nel feed, con il suo verdetto, e guadagna stipendio e competenze di
   freehire (vedi FR-006).
5. **Given** un'offerta LinkedIn che i canali LinkedIn di JobSpy non hanno visto, **When** freehire la
   riporta, **Then** entra nel feed come offerta LinkedIn nuova.

---

### User Story 2 - Dati arricchiti usati da JobSpy (Priority: P2)

Le offerte da freehire portano con sé stipendio, competenze, requisiti e il segnale di offerta fantasma.
JobSpy li mostra e li usa: l'analisi sul CV li riceve come fatti già noti, e le offerte fantasma o già chiuse
non vengono analizzate.

**Why this priority**: più qualità e meno token DeepSeek sulle offerte che non valgono la pena.

**Independent Test**: con una risposta registrata che contiene un'offerta con stipendio e una marcata come
fantasma, verificare che la prima abbia stipendio e competenze nella scheda e che la seconda non venga
mandata all'analisi.

**Acceptance Scenarios**:

1. **Given** un'offerta freehire con stipendio 30–35k € annui, **When** entra nel feed, **Then** la scheda
   mostra quello stipendio, senza che l'LLM lo debba ricavare dalla descrizione.
2. **Given** un'offerta freehire marcata come «falsa nuova» o ripubblicata in massa, **When** entra nel
   feed, **Then** è segnalata come sospetta e non consuma un'analisi sul CV.
3. **Given** un'offerta freehire con requisiti obbligatori e preferiti, **When** viene analizzata, **Then**
   l'analisi li riceve in una sezione marcata della descrizione.

---

### User Story 3 - Chiusure da freehire (Priority: P2)

Quando freehire segna un'offerta come chiusa, JobSpy la archivia invece di tenerla nel feed finché non
sparisce dalla ricerca.

**Why this priority**: il feed resta pulito e Ale non perde tempo su offerte già chiuse.

**Independent Test**: con un'offerta freehire nel feed e una risposta registrata che la riporta chiusa,
eseguire il controllo e verificare che l'offerta sia archiviata e che il suo verdetto resti intatto.

**Acceptance Scenarios**:

1. **Given** un'offerta freehire nel feed, **When** freehire la riporta chiusa, **Then** JobSpy la archivia
   con il motivo «chiusa alla fonte» e il verdetto resta salvato.
2. **Given** un'offerta freehire su cui Ale ha una candidatura aperta, **When** freehire la riporta chiusa,
   **Then** la candidatura non cambia stato da sola; Ale vede che l'offerta è chiusa.
3. **Given** freehire non risponde durante il controllo, **When** il controllo fallisce, **Then** nessuna
   offerta viene archiviata.

---

### User Story 4 - Canali per azienda (Priority: P3)

Ale segue un'azienda (es. Acme): un canale di tipo «azienda» porta tutte le sue offerte aperte dal
suo sito di candidatura, a prescindere dalla parola chiave, con gli eventuali filtri del canale.

**Why this priority**: per le aziende in cui Ale vuole lavorare conta vedere tutto, non solo ciò che
combacia con una parola chiave.

**Independent Test**: cercare un'azienda per nome, sceglierla, creare il canale e verificare con una risposta
registrata che il refresh porti le sue offerte.

**Acceptance Scenarios**:

1. **Given** Ale cerca «Acme», **When** sceglie tra i risultati (nome, numero di offerte aperte),
   **Then** può creare un canale che segue quell'azienda.
2. **Given** un canale azienda con il filtro «solo remoto», **When** parte il refresh, **Then** entrano solo
   le offerte remote di quell'azienda.

---

### User Story 5 - Ricerca al volo (Priority: P3)

Dalla webapp o da Hermes (MCP) Ale cerca su freehire senza creare un canale, vede i risultati e salva solo
quelli che gli interessano, che da lì in poi si comportano come le altre offerte del DB.

**Why this priority**: per esplorare una ricerca prima di decidere se vale un canale.

**Independent Test**: eseguire una ricerca al volo con risposta registrata, salvare un risultato e
verificare che sia nel DB con sorgente freehire e che gli altri risultati non lo siano.

**Acceptance Scenarios**:

1. **Given** una ricerca «AI engineer, Italia, 7 giorni», **When** Ale la lancia, **Then** vede i risultati
   con titolo, azienda, zona, stipendio se noto, e quali sono già nel DB.
2. **Given** i risultati di una ricerca al volo, **When** Ale ne salva uno, **Then** quell'offerta entra nel
   DB e può essere analizzata e candidata; gli altri non vengono salvati.
3. **Given** Hermes, **When** usa il tool MCP di ricerca al volo, **Then** ottiene gli stessi risultati della
   webapp.

### Edge Cases

- freehire ignora un parametro sbagliato e restituisce tutto il catalogo: deve contare come errore, non come
  risultato (US1, scenario 2).
- Offerta senza zona o con un elenco di decine di paesi («remoto ovunque»): resta, marcata remota.
- La stessa offerta compare due volte in freehire da due aggregatori (es. «Esempio srl» e «Esempio Srl»): il dedup
  di JobSpy la raggruppa se la descrizione coincide, altrimenti restano due offerte.
- Il link di freehire porta un parametro di tracciamento: si salva il link originale dell'offerta.
- Un'offerta chiusa che freehire riapre: rientra nel feed come le offerte riapparse delle altre sorgenti.
- Un'azienda che freehire rinomina o di cui cambia l'identificativo: il canale azienda va in errore e lo
  dice, invece di restare vuoto in silenzio.
- freehire introduce una chiave obbligatoria o chiude l'API: i canali freehire vanno in errore, il resto di
  JobSpy non ne risente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST offrire freehire come sorgente selezionabile per un canale, con parola chiave,
  zona, solo remoto, recenza e numero di risultati come le altre sorgenti.
- **FR-002**: Il sistema MUST tradurre la zona del canale nei filtri di freehire per i casi «Italia»,
  «Europa», una città italiana e «nessuna zona»; una zona non traducibile MUST mettere il canale in errore.
- **FR-003**: Il sistema MUST considerare errore qualsiasi risposta di freehire che dichiari di aver
  ignorato un filtro richiesto.
- **FR-004**: Il sistema MUST scartare le offerte già chiuse alla fonte e salvare il link originale
  dell'offerta, senza parametri di tracciamento di freehire.
- **FR-005**: Il sistema MUST rispettare il limite dichiarato da freehire e la politica delle fonti
  (un refresh al giorno per canale, errore su 403/429, nessun sito vero nei test).
- **FR-006**: Il sistema MUST tenere le offerte che freehire prende da LinkedIn (sono le più interessanti
  per Ale) e MUST ricondurle alla stessa identità che usa lo scraper LinkedIn di JobSpy: la stessa offerta
  vista da entrambe le sorgenti è una sola offerta nel DB, con un solo verdetto e una sola analisi, e
  accumula i dati arricchiti di freehire. Lo stesso vale per ogni altra sorgente di cui JobSpy e freehire
  producono lo stesso link originale.
- **FR-007**: Il sistema MUST salvare stipendio (minimo, massimo, valuta, periodo) e competenze forniti da
  freehire nei campi già esistenti dell'offerta.
- **FR-008**: Il sistema MUST passare all'analisi sul CV i requisiti forniti da freehire in una sezione
  marcata «Requisiti (dalla fonte)» in fondo alla descrizione, senza cambiare il prompt né la sua versione
  (deciso da Ale il 24/11: evita di rianalizzare ~880 offerte attive). Un input strutturato dedicato si
  introduce col prossimo cambio di prompt (piano 03).
- **FR-009**: Il sistema MUST marcare come sospette le offerte che freehire segnala come false nuove o
  ripubblicate in massa e MUST NOT mandarle all'analisi automatica; Ale può chiederne l'analisi a mano.
- **FR-010**: Il sistema MUST verificare una volta al giorno lo stato delle offerte freehire nel feed e
  archiviare quelle chiuse alla fonte, conservando verdetti, storico e candidature.
- **FR-011**: Il sistema MUST permettere di cercare un'azienda su freehire per nome e creare un canale che ne
  segue tutte le offerte aperte, con i filtri del canale.
- **FR-012**: Il sistema MUST offrire una ricerca su freehire senza canale, dalla webapp e da un tool MCP,
  che mostra i risultati senza salvarli e permette di salvare i singoli risultati scelti.
- **FR-013**: Ogni nuova operazione dell'API MUST avere il suo tool in `intecha-mcp` (creazione canale
  azienda, ricerca aziende, ricerca al volo, salvataggio di un risultato).
- **FR-014**: Il sistema MUST NOT salvare in git dati di offerte, né nei fixture dei test (risposte
  registrate anonimizzate o inventate).

### Key Entities

- **Canale freehire**: un canale come gli altri, con sorgente freehire; per parola chiave oppure per azienda.
- **Azienda freehire**: identificativo stabile, nome, numero di offerte aperte; seguita da un canale azienda.
- **Offerta freehire**: un'offerta come le altre, più i dati arricchiti (stipendio, competenze, requisiti,
  segnale fantasma, data di chiusura) e la sorgente originale dichiarata da freehire.
- **Risultato al volo**: un'offerta mostrata ma non salvata, finché Ale non la salva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Entro 2 settimane dal deploy, i canali freehire portano almeno 30 offerte nuove remote o a
  Verona in ambito AI/ML/software che non erano già nel DB.
- **SC-002**: Nessun doppione visibile nel feed tra un'offerta freehire e la stessa offerta presa da
  LinkedIn o Indeed nei canali esistenti.
- **SC-003**: Le offerte freehire sospette o chiuse non consumano analisi automatiche: zero analisi su di
  esse nel log.
- **SC-004**: Un'offerta chiusa alla fonte sparisce dal feed entro 24 ore dalla chiusura su freehire.
- **SC-005**: Una ricerca al volo restituisce i risultati in meno di 5 secondi dalla webapp e da Hermes.
- **SC-006**: Tutti i test passano senza rete; un guasto di freehire non fa fallire il refresh degli altri
  canali.

## Assumptions

- L'API pubblica di freehire resta gratuita e senza chiave per l'uso personale; i termini vietano la
  ridistribuzione, non l'uso dentro JobSpy.
- freehire filtra per città ma non per raggio: un canale «Verona» su freehire copre il comune, non i 30 km;
  il raggio resta un vantaggio dei canali LinkedIn/Indeed.
- La verifica delle chiusure riguarda solo le offerte arrivate da freehire; le copie dello stesso annuncio
  prese da altre sorgenti seguono le regole di archiviazione attuali.
- I canali iniziali proposti: «LLM engineer, Europa, remoto, 7 giorni», «machine learning, Italia, remoto»,
  «AI engineer, Italia, 7 giorni»; si creano dopo il deploy, non fanno parte del codice.
- Per i canali per azienda e la ricerca al volo si usa la stessa API pubblica; nessun account freehire.
