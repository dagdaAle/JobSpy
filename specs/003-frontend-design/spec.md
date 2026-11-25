# Feature Specification: frontend dal design Penpot

**Feature Branch**: `feat/frontend-design` (sopra `feat/pa-gare-areas`, PR #20)

**Created**: 2026-11-25

**Status**: Draft

**Input**: "Implementiamo il frontend disegnato in Penpot (file «JobSpy — Brand e frontend», progetto JOBSPY)."

## Contesto

Il design è in Penpot e descritto nel brief `~/Documents/progetti-creativi/jobspy-penpot/BRIEF-design.md`
(fuori dalla repo: contiene solo dati finti, ma resta nella cartella di lavoro di Ale). I principi sono quelli di
[DESIGN.md](../../docs/DESIGN.md): la decisione prima dell'elenco, il motivo è il contenuto, il non noto si vede,
calma, un gesto un'azione.

Questa feature è **solo frontend**: nessuna API nuova, nessuna tabella toccata. Le cinque componenti di DESIGN.md
(fattibilità, corrispondenza, interesse, carriera, condizioni) non esistono ancora nel backend: il dettaglio le
ricava dai campi dell'analisi v3 che ci sono già (`decision`, `blockers`, `missing_requirements`, `cv_match`,
`location_fit`, `salary`, `work_mode`, `seniority`, `relevance_score`); ciò che manca si mostra come «non noto».

## User Scenarios & Testing

### User Story 1 - Feed Lavoro per decisione (Priority: P1)

Ale apre JobSpy e vede la testata nera con il selettore d'area e la barra filtri, a sinistra le viste e i filtri
per faccetta, al centro le offerte divise in sezioni «Candidati», «Valuta», «Non noto» (le «Lascia» solo se
attiva la casella). Ogni card ha il pannello colorato dalla decisione, il badge testo + icona, il motivo in una
riga, al massimo 4 tag, la RAL in mono o «RAL non indicata».

**Independent Test**: con il backend locale e alcune offerte analizzate, il feed mostra le sezioni nell'ordine
giusto; togliere «Valuta» dai filtri nasconde la sezione; un'offerta senza analisi finisce in «Non noto» con
bordo tratteggiato.

**Acceptance Scenarios**:
1. **Given** offerte con decisione apply/maybe/skip e senza analisi, **When** si apre il feed, **Then** compaiono
   le sezioni Candidati, Valuta, Non noto con il conteggio; Lascia è nascosta finché non si spunta.
2. **Given** un'offerta, **When** si clicca X o il segnalibro, **Then** il verdetto cambia e un toast offre «Annulla».
3. **Given** il cursore «RAL minima» a 30.000 €, **When** un'offerta non indica la RAL, **Then** resta nel feed
   (il non noto non è basso).

### User Story 2 - Dettaglio offerta con i motivi (Priority: P1)

Aprendo un'offerta, il pannello laterale ha la testa colorata dalla decisione, i numeri (RAL, modalità,
pubblicazione) e le componenti ricavate dall'analisi; quelle senza dati sono tratteggiate con «dati insufficienti».
Candidatura, CV e descrizione restano come oggi.

### User Story 3 - Concorsi PA e Gare P.IVA con la stessa struttura (Priority: P1)

Le aree PA e Gare usano la stessa testata, la stessa colonna sinistra (Feed, Preferiti, Scartati, Archivio,
Canali, Profilo) e la stessa card, con la scadenza in evidenza (chip pieno entro 7 giorni) ed esito
Adatto / Da valutare / Non adatto. Il feed è diviso per esito e ordinabile per scadenza.

### User Story 4 - Stati, tema scuro e telefono (Priority: P2)

Avvisi per LLM non configurato, estrazione in corso, canale in errore; stati vuoti; tema scuro con gli stessi
token; sotto 768 px la colonna sinistra diventa una barra in basso e le card vanno a tutta larghezza.

### Edge Cases

- Analisi v2 senza `decision`: card «Non noto» con il punteggio nel dettaglio, se c'è.
- Bando senza scadenza: chip tratteggiato «Scadenza non indicata».
- Gara senza importo: «Importo non indicato» in corsivo; il cursore importo non la esclude.
- Nessun canale: stato vuoto con «Nuovo canale».

## Requirements

- **FR-001**: Token e font come `jobspy-tokens.css` (Inter, Outfit, JetBrains Mono); verde solo per
  candidati/adatto, rosso solo per errori e bloccanti.
- **FR-002**: Una sola struttura di pagina per le tre aree (testata, barra filtri, colonna sinistra, contenuto,
  barra in basso su telefono).
- **FR-003**: Decisione ed esito sempre con testo + icona, mai solo colore.
- **FR-004**: Filtri lato client sui dati già caricati; nessuna chiamata API nuova.
- **FR-005**: Il comportamento esistente resta: verdetti con Annulla, ripristino dall'archivio, candidature, CV,
  ricerca freehire, analytics, log, canali, profili.
- **FR-006**: Target touch ≥ 44 px su telefono; tutte le azioni da tastiera; contrasto AA in chiaro e in scuro.

## Success Criteria

- **SC-001**: `npm run build` pulito; `python -m unittest` invariato e verde.
- **SC-002**: Le schermate del brief (feed Lavoro/PA/Gare, dettaglio, dialog, stati, mobile) corrispondono a
  vista nel browser con il backend locale.

## Fuori scope

Pagine Tag e Preferenze, componenti calcolate dal backend, dettaglio candidatura e bot, nuove API.
