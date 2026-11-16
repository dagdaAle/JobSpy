> Stato: bozza generata da agente · Aggiornato: 2026-11-16 · Fonte: dagdaAle/JobSpy@7aef32d

# 07 · Decisioni (ADR)

Sintesi degli ADR in `docs/adr/` (tutti del 02/11/2026). Lo stato è quello scritto nel file: "proposta" vuol dire scelta di Claude non ancora confermata da Ale.

## ADR-001 — Fork con due zone (in vigore)

- **Contesto**: la repo è un fork pubblico di `speedyapply/JobSpy`; sopra è cresciuta una webapp personale.
- **Decisione**: `jobspy/` è upstream e si tocca il minimo, annotando ogni modifica in `docs/upstream.md`; le fonti nuove stanno in cartelle proprie; `webapp/` e `docs/` sono liberi; il workflow PyPI non si attiva.
- **Alternative scartate**: staccarsi da upstream (si perderebbero i fix agli scraper LinkedIn/Indeed).
- **Conseguenze**: prima di ogni allineamento si controlla `jobspy/model.py`, di cui la webapp usa le colonne.

## ADR-002 — Rifattorizzare, non riscrivere (proposta)

- **Contesto**: logica collaudata in due file enormi (`app.py`, `storage.py`) con SQL grezzo.
- **Decisione**: cambiare la struttura (strati, SQLAlchemy, Alembic, `/api/v1`) senza cambiare il comportamento; i test restano verdi a ogni passo.
- **Alternative scartate**: riscrittura, che perderebbe casi limite presenti solo nel codice.
- **Conseguenze**: per un periodo convivono rotte vecchie e `/api/v1`; le regole di dominio cambiano solo in PR dedicate.

## ADR-003 — SQLite, un processo (in vigore)

- **Contesto**: un utente, ~2.000 offerte, DB di decine di MB.
- **Decisione**: SQLite su `/data/feedback.db`, un solo processo uvicorn, nessun worker esterno; WAL.
- **Alternative scartate**: un DB server o worker separati: nessun bisogno di concorrenza.
- **Conseguenze**: mai più di una replica né `--workers > 1`; backup coerente con l'API di SQLite.

## ADR-004 — Politica delle fonti (proposta)

- **Contesto**: LinkedIn e Indeed bloccano chi interroga troppo; l'app gira dall'IP di casa.
- **Decisione**: niente login automatizzato, CAPTCHA o proxy a rotazione; un refresh al giorno per canale, serializzato; nei test mai i siti veri.
- **Alternative scartate**: proxy e rotazione, che la libreria supporterebbe.
- **Conseguenze**: pochi canali per sito.

## ADR-005 — L'LLM valuta, "non so" resta non noto (in vigore)

- **Decisione**: output JSON a schema; punteggio `null` e confidenza bassa se i dati sono scarsi; non si inventano distanze, RAL, permessi; CV e annuncio sono dati non attendibili (prompt injection); cache per `context_key` = hash(modello, versione prompt, CV); `PROMPT_VERSION` si incrementa a ogni cambio.
- **Conseguenze**: cambiare prompt costa una rianalisi; la parte sul punteggio sarà superata dall'ADR-007.

## ADR-006 — Tag a faccette con vocabolario controllato (proposta)

- **Contesto**: tag liberi duplicati e fuori posto, inutili per filtri e preferenze.
- **Decisione**: tag con faccetta, vocabolario versionato con sinonimi, coda di proposte per i termini nuovi, evidenza dall'annuncio; sede e distanza decise da regole.
- **Conseguenze**: primo vocabolario costruito dai tag esistenti; un cambio di vocabolario rifà l'estrazione solo delle offerte attive.

## ADR-007 — L'LLM estrae, la valutazione è deterministica a componenti (proposta)

- **Contesto**: punteggio 0-100 del modello non scomponibile; media 21 con 654 scarti contro 30 preferiti.
- **Decisione**: estrazione LLM indipendente da CV e preferenze; valutazione in codice: gate di fattibilità + corrispondenza, interesse (imparato dai verdetti), carriera, condizioni; decisione `candidati / valuta / lascia`.
- **Alternative scartate**: un modello ML addestrato (i pesi devono restare leggibili).
- **Conseguenze**: cambiare CV o preferenze non chiama DeepSeek.

## ADR-008 — Candidatura assistita, mai autonoma (proposta)

- **Decisione**: il sistema prepara il kit, il bot `jobs` precompila, **Ale invia**. Livelli per portale (LinkedIn solo precompilazione, PA solo kit). Il bot non digita password, 2FA o pagamenti, si ferma su CAPTCHA, ~5 invii all'ora al massimo.
- **Conseguenze**: il bot resta sul Mac con le sessioni di Ale; il server non fa login sui portali.

## ADR-009 — Candidature: JobSpy unica fonte di verità (proposta)

- **Contesto**: stato diviso tra `applications` e le cartelle `stato.md` del bot.
- **Decisione**: stato, passi e risposte in JobSpy; il bot scrive via MCP; la cartella locale tiene solo file e dati anagrafici.
- **Conseguenze**: servono tool MCP per eventi e allegati (piano 05).

## Altre decisioni (da PRODUCT.md e note)

- Verona è il centro; bandi pubblici solo con sede in provincia di Verona; DeepSeek resta il provider; il fork resta allineato a upstream (Ale, 02/11/2026).
- Le copie della stessa offerta condividono il verdetto, e uno scarto non sovrascrive mai un preferito (17/09/2026).
- Non esiste la cancellazione delle offerte: lo scarto viene ricordato, l'offerta si archivia.
