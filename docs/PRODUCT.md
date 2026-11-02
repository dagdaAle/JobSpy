# PRODUCT — cosa è e perché esiste

> Stato: bozza del 02/11/2026, seconda versione dopo il confronto con Ale. Scritta leggendo il codice
> (`origin/main` = `d7d05b2`, lo stesso commit in produzione), i dati di produzione via MCP e il bot Hermes `jobs`.
> Le voci marcate **(scelta di Claude)** non sono state decise da Ale: vanno confermate o cambiate.
> La repo è **pubblica** (fork di `speedyapply/JobSpy`): in questi documenti non ci sono dati personali, candidature o CV.

## Il problema

Ale cerca lavoro a Verona e dintorni, guardandosi intorno a largo raggio. Farlo a mano vuol dire:

- **Ricerche ripetute** su LinkedIn, Indeed, inPA e bacheche remote, ogni giorno, con gli stessi termini.
- **Doppioni**: la stessa offerta compare su più siti e in più ricerche.
- **Nessun criterio leggibile**: un numero da 0 a 100 non dice *perché* un'offerta è interessante o no, e non distingue
  "non fa per me" da "non ho abbastanza dati".
- **Candidature faticose e sparse**: CV da adattare, form diversi per ogni portale, domande ricorrenti, stato tenuto
  in due posti diversi (JobSpy e la cartella del bot `jobs`).

## L'obiettivo

Non c'è un ruolo bersaglio. Il criterio è **un lavoro interessante e stimolante, che faccia bene alla carriera**,
e Ale guarda tutto. Concretamente:

- **Verona è il centro**: presenza o ibrido a Verona e dintorni è il caso principale; il remoto dall'Italia è un'opzione in più, non un obiettivo.
- **I bandi pubblici contano molto**, ma **solo quelli con sede a Verona** (o provincia).
- Ruoli diversi (sviluppo, dati/AI, sistemi, docenza, PA tecnica, ambiti laterali come robotica o droni) vanno tutti bene
  **se** sono interessanti: il sistema deve aiutare a capire quali lo sono, non restringere a priori.

Di conseguenza il cuore del prodotto non è la raccolta (funziona già) ma **capire le offerte**: tagging strutturato,
valutazione spiegabile, e candidatura assistita.

## Stato al 02/11/2026

In produzione su `https://jobspy.intecha.dev` dietro Authentik, container `jobspy-api` (Coolify), commit `d7d05b2`.

| Dato | Valore |
|---|---|
| Canali | 24 (13 LinkedIn/Indeed su Verona, 4 remoti, 2 inPA, 2 Remotive, temi droni / robotica / stampa 3D) |
| Offerte | 1958 dal 17/09, 249 nel feed, 1038 archiviate |
| Analisi | 2987 esecuzioni, **278 in errore (9%)**, ~6,1 M token DeepSeek, punteggio medio **21** |
| Verdetti | 30 preferiti, **654 scartati**, 716 eventi di feedback |
| Candidature | 5 in JobSpy, 6 cartelle nel bot `jobs` (non allineate) |
| DB | `feedback.db` 46 MB; backup giornalieri in `/data/backups` (16 file, 559 MB) **sullo stesso volume** |
| Test | 43, verdi (`unittest`) |

Cosa non va, in ordine di peso:

1. **Tagging**: l'LLM scrive fino a 6 etichette libere per offerta. Nessun vocabolario, nessuna dimensione:
   escono "It Support", "Onsite Usa", "Concorso" e "Concorso Pubblico" come tag distinti, "Pubblica Amministrazione"
   come competenza. I tag non servono per filtrare, confrontare o imparare.
2. **Punteggio**: un solo numero 0-100 deciso dal modello, che mescola corrispondenza al CV, interesse, sede e condizioni.
   Non si scompone, non si spiega, non si calibra, e ogni cambio di CV o di prompt costa una rianalisi completa.
   Il punteggio medio 21 con 654 scarti dice che oggi non aiuta a decidere.
3. **Candidature in due posti**: JobSpy traccia lo stato; il bot Hermes `jobs` (Mac di Ale, browser locale) tiene
   profilo candidato, domande ricorrenti e una cartella per offerta con `stato.md`. Le due cose non si parlano.
4. **inPA "Verona" fa entrare bandi nazionali**: il connettore considera "in zona" anche i bandi con sede nazionale
   (Formez PA, ISS compaiono tra le aziende più frequenti). Per Ale servono solo quelli con sede Verona.
5. **Lavoro fermo su branch**: PR [#9](https://github.com/dagdaAle/JobSpy/pull/9) e [#10](https://github.com/dagdaAle/JobSpy/pull/10)
   (analisi v3 orientata alla decisione + filtri dei canali) aperte dal 19/10; [#1](https://github.com/dagdaAle/JobSpy/pull/1) dal 18/09;
   [#11](https://github.com/dagdaAle/JobSpy/pull/11).
6. **Fork 40 commit dietro upstream** (ultimo upstream 27/10): fix agli scraper LinkedIn/Indeed non arrivano.
7. **Architettura**: `app.py` e `storage.py` fanno tutto; estrazione dei fatti e giudizio sono la stessa chiamata LLM,
   quindi non si può cambiare il giudizio senza rifare l'estrazione.

## Principi trasversali (gli stessi di todo-app e BuyWatcher)

- **Tutto interrogabile da un LLM via MCP**: ogni cosa visibile o fattibile nell'app lo è anche per Hermes, CV e candidature compresi.
- **Pensata per il server e per più client**: web oggi, telefono domani, stessa API.
- **Backend fatto bene**: strati, migrazioni, contratto API stabile (ARCHITECTURE.md).
- **Onestà sui dati**: ciò che non si sa resta "non noto". RAL assente non è zero, sede ignota non è incompatibile,
  dato mancante non è punteggio basso.
- **L'LLM estrae, il sistema decide** **(scelta di Claude)**: DeepSeek legge l'annuncio e restituisce fatti e tag a schema,
  con l'evidenza; il punteggio si calcola in modo deterministico da quei fatti e dalle preferenze di Ale.
  È la stessa regola di BuyWatcher ([adr/007](adr/007-score-a-componenti.md)).

## Utenti

- **Ale**: legge il feed, decide, si candida, tiene traccia. Da Mac e da telefono.
- **Hermes, profilo `jobs`**: valuta un'offerta, prepara il kit di candidatura, precompila i form nel browser locale
  di Ale, aggiorna lo stato in JobSpy.
- **Hermes generale / Claude**: riassume le novità, crea canali, registra note.

App per una persona sola. Niente multi-utente.

## Le tre capacità da costruire

### 1. Tagging strutturato **(scelta di Claude)**

I tag diventano **faccette con vocabolario controllato**, non parole libere:

| Faccetta | Esempi | Chi la decide |
|---|---|---|
| Famiglia di ruolo | sviluppo backend, sviluppo full stack, dati/AI, sistemi e reti, supporto IT, embedded/robotica, docenza, PA tecnica, consulenza | LLM, su vocabolario |
| Tecnologie | Python, Java, C++, SQL, React, Docker, cloud AWS/Azure… (sinonimi normalizzati: "py" → Python) | LLM + normalizzazione |
| Dominio | automotive, manifattura, sanità, finanza, PA, aerospazio, software house… | LLM, su vocabolario |
| Seniority | junior, mid, senior, non indicata | LLM |
| Modalità | presenza, ibrido, remoto, non noto | LLM con evidenza |
| Sede | comune e provincia; distanza da Verona **calcolata**, non stimata | regola (tabella comuni) |
| Contratto | indeterminato, determinato, P.IVA, stage, somministrazione, concorso | LLM |
| Tipo di datore | azienda di prodotto, consulenza/body rental, agenzia per il lavoro, PA, startup, università/ricerca | LLM + regole (agenzie note) |
| Condizioni | RAL come scritta, lingue richieste, trasferte | LLM, solo se scritte |
| Segnali | RAL assente, agenzia, requisiti incoerenti con la seniority, annuncio ripubblicato | regole + LLM |
| Tag di Ale | liberi: "da approfondire", "chiedere in giro", "azienda che mi piace" | Ale |

- Un termine fuori vocabolario non si scarta: va in una **coda di proposte** che Ale approva o unisce a un tag esistente.
- Ogni tag ha la **fonte** (LLM, regola, Ale) e, se viene dall'LLM, la **frase dell'annuncio** che lo giustifica.
- I tag servono a: filtri del feed, filtri dei canali, analytics, preferenze, punteggio.
- Il CV viene taggato con lo **stesso vocabolario**, una volta per versione: la corrispondenza diventa un confronto tra insiemi.

### 2. Valutazione a componenti **(scelta di Claude)**

Al posto di un numero unico, quattro componenti separate e un **gate**:

| Componente | Cosa misura | Da dove viene |
|---|---|---|
| **Fattibilità** (gate) | ci sono bloccanti? sede fuori zona, remoto riservato ad altri paesi, titolo o requisito obbligatorio mancante, lingua non posseduta | fatti estratti + regole |
| **Corrispondenza** | requisiti coperti dal CV / requisiti totali, separando obbligatori e preferenziali | tag dell'offerta vs tag del CV |
| **Interesse** | quanto i tag dell'offerta somigliano a ciò che Ale ha preferito o scartato | affinità per tag, imparata dai verdetti |
| **Carriera** | crescita: tecnologie nuove ma vicine, ruolo un passo avanti, tipo di datore, formazione, dominio | rubrica fissa + giudizio LLM motivato |
| **Condizioni** | RAL, contratto, modalità, distanza da Verona | fatti + preferenze di Ale |

- Il **risultato** è una decisione `candidati / valuta / lascia` con il motivo in una riga, più il dettaglio per componente.
  Il numero finale esiste ma è secondario.
- Ogni componente può essere **non nota**: non conta zero, abbassa la confidenza.
- I pesi stanno in un **profilo di preferenze** che Ale vede e modifica; il primo set si calibra sui 716 verdetti esistenti.
- Cambiare preferenze o pesi **non richiede DeepSeek**: si ricalcola in locale in un secondo.

### 3. Candidatura assistita **(scelta di Claude, da confermare)**

Il flusso di una candidatura, con chi fa cosa:

| Passo | Cosa succede | Chi |
|---|---|---|
| Scelta | Ale segna "candidati" | Ale |
| Kit | CV adattato (`/cvs/tailor`), lettera se serve, risposte alle domande ricorrenti, checklist dei campi | JobSpy + DeepSeek |
| Precompilazione | il bot apre il portale nel browser locale di Ale con le sue sessioni e compila | Hermes `jobs` |
| Invio | solo con "ok" esplicito di Ale per quella candidatura | Ale |
| Traccia | stato, data, CV usato, cosa è stato dichiarato, screenshot finale | JobSpy (via MCP) |
| Seguito | promemoria di richiamo e colloqui | todo-app (via MCP) |

Livelli di automazione per tipo di portale:

| Portale | Livello massimo |
|---|---|
| ATS aziendali (Workday, Greenhouse, Lever, Teamtailor, SmartRecruiters…) | precompilazione completa, invio dopo l'ok |
| Indeed (Smart Apply) | precompilazione, invio dopo l'ok |
| LinkedIn (Easy Apply) | solo precompilazione, l'invio lo fa Ale a mano |
| inPA e portali PA | kit e checklist; l'accesso SPID e l'invio sono di Ale |
| Email al recruiter | bozza, mai inviata dal bot |

Regole che restano (sono già nel bot `jobs`): niente invio senza ok, niente dati inventati, niente password / 2FA / pagamenti
digitati dal bot, stop su CAPTCHA, al massimo ~5 invii all'ora sui portali aziendali.

**Una sola fonte di verità**: le candidature vivono in JobSpy. La cartella locale del bot tiene solo i file
(PDF inviati, screenshot) e i dati del candidato che non devono andare sul server; lo stato si scrive in JobSpy via MCP.

## Obiettivi

- Aprire il feed e capire in meno di 10 secondi se oggi c'è un'offerta a cui candidarsi, e perché.
- **Rapporto preferiti/scarti molto più alto di oggi** (1:22).
- Nessun tag duplicato o fuori faccetta nelle analytics.
- Da "candidati" a form precompilato senza riscrivere a mano CV e risposte già date.
- Hermes può fare tutto quello che fa Ale nella UI.
- Pezzo da portfolio AI/ML: estrazione a schema con evidenza, valutazione deterministica spiegabile,
  preferenze imparate dai verdetti, misura della qualità.

## Non obiettivi

- **Non** un bot che si candida da solo: l'invio resta una decisione di Ale, ogni volta.
- **Non** una libreria di scraping da pubblicare: `jobspy/` resta il fork, il PyPI non si tocca.
- **Non** un modello di machine learning addestrato: le preferenze sono pesi per tag, leggibili e modificabili.
- **Non** multi-utente, **non** un'app mobile nativa.

## Anti-obiettivi (se succede, il progetto è fallito anche se funziona)

- Il feed resta pieno di offerte fuori tema: Ale smette di aprirlo e torna a cercare a mano.
- Una candidatura parte senza l'ok di Ale, o con un dato inventato.
- Un account di Ale (LinkedIn, Indeed) viene limitato o l'IP di casa bloccato per colpa dell'app o del bot.
- I tag tornano a essere parole libere che nessuno usa.
- Un dato personale (CV, candidature, profilo candidato, chiave DeepSeek) finisce nella repo pubblica.
- Si perdono i verdetti: sono l'unico dato non rigenerabile, e ora anche la base delle preferenze.

## Misurare l'AI **(scelta di Claude)**

- Set etichettato dai 716 eventi di feedback (preferito = positivo, scartato = negativo) e dagli esiti delle candidature,
  salvato **fuori dalla repo**.
- Per il tagging: precisione dei tag su un campione rivisto da Ale (50 offerte), percentuale di termini fuori vocabolario.
- Per la valutazione: preferiti finiti in "lascia", scarti finiti in "candidati", per componente.
- Prima di tutto: capire e ridurre il **9% di analisi in errore**.
- Ogni PR che tocca prompt, vocabolario o pesi allega il report.

## Decisioni prese (02/11/2026)

- **Verona è il centro** della ricerca; il remoto è in più.
- **Bandi pubblici sì, solo con sede a Verona.**
- **DeepSeek resta** il provider LLM.
- **Il fork resta allineato a upstream.**

## Decisioni da prendere **(proposte di Claude)**

1. **PR aperte**: mergiare #11, poi #10 (contiene #9, che si chiude come inclusa), deploy. La v3 di #10 è un passo verso
   la valutazione a componenti: va presa, poi superata dal piano 03.
2. **Canali**: tenerli tutti finché il nuovo tagging non dice quali producono offerte interessanti; archiviare solo i 3 a 0 risultati
   (full stack, backend, embedded). L'archiviazione sostituisce la cancellazione.
3. **inPA**: escludere i bandi con sola sede nazionale; tenere quelli che citano Verona o la provincia. Alternativa: tenerli con il segnale
   "sede da verificare".
4. **Backup fuori dal server**: copia notturna + retention (DAT-01 dell'audit resta aperto).
5. **Profilo candidato in JobSpy**: le preferenze (pesi, zone, contratti) vivono nel DB di JobSpy; i dati anagrafici e le risposte
   ricorrenti restano nella cartella locale del bot, che non va sul server.
6. **Lingua della repo**: codice e commit in inglese (è un fork); `docs/` in italiano come le app sorelle.

## Fasi **(scelta di Claude)**

1. **Consolidare**: PR aperte, allineamento a upstream, filtro inPA, backup fuori dal server, AGENTS.md.
2. **Backend**: strati, SQLAlchemy + Alembic, `/api/v1`. Comportamento invariato, i 43 test fanno da rete.
3. **Tagging e valutazione**: vocabolario, estrazione separata dal giudizio, valutazione a componenti, preferenze dai verdetti.
4. **Candidature**: una fonte di verità, kit, integrazione con il bot `jobs`, promemoria in todo-app.
5. **MCP completo**: CV, tag, preferenze, candidature, modifica canali.
6. **Frontend**: pagine con URL, feed per decisione, scheda con componenti, pipeline candidature.
7. **Qualità AI**: set etichettato, script di misura, calibrazione.

## Domande aperte

- **Cosa rende un lavoro "interessante" per Ale?** Serve una mezz'ora su 15-20 offerte già viste (preferite e scartate)
  per scrivere la rubrica di Interesse e Carriera. È l'input più importante del piano 03.
- **Fino a dove è "Verona e dintorni"?** Raggio in km o elenco di comuni; vale anche per i bandi.
- **Il bot `jobs` resta sul Mac** (browser con le sessioni di Ale) o una parte si sposta sul server? Proposta: resta sul Mac.
- **Esiti**: Ale è disposto a segnare l'esito di ogni candidatura (nessuna risposta, colloquio, offerta)? È il segnale migliore per calibrare.
