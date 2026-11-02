# PRODUCT — cosa è e perché esiste

> Stato: bozza del 02/11/2026, scritta leggendo il codice (`origin/main` = `d7d05b2`, lo stesso commit in produzione)
> e i dati di produzione via MCP. Le voci marcate **(scelta di Claude)** non sono state decise da Ale: vanno confermate o cambiate.
> La repo è **pubblica** (fork di `speedyapply/JobSpy`): in questi documenti non ci sono dati personali, candidature o CV.

## Il problema

Ale cerca lavoro. Farlo a mano vuol dire:

- **Ricerche ripetute** su LinkedIn, Indeed, inPA e bacheche remote, ogni giorno, con gli stessi termini.
- **Doppioni**: la stessa offerta compare su più siti e in più ricerche.
- **Nessun filtro sul senso**: "software engineer" restituisce ruoli in sede negli USA, vendite, consulenza body rental.
- **Candidature sparse**: dove si è mandato cosa, con quale CV, quando richiamare.

## L'idea

Un radar personale delle offerte di lavoro, sul server di casa:

- **Canali**: una ricerca salvata (sito + termine + luogo + raggio + finestra temporale), rinfrescata ogni giorno alle 09:00.
- Le offerte vengono **normalizzate, deduplicate** (le copie condividono il verdetto) e tenute con lo storico
  (avvistamenti, versioni). Nulla si cancella: ciò che esce dal feed viene archiviato.
- Un **LLM (DeepSeek)** valuta ogni offerta contro il CV: tag, riassunto, punteggio 0-100, motivi, modalità di lavoro,
  compatibilità della sede. Se mancano dati il punteggio è `null`, non basso.
- Ale mette **mi piace / scarta**, traccia le **candidature** (stato, date, prossimo passo, note) e gestisce una
  **libreria di CV** (base e adattati a un'offerta via LLM, revisione, export PDF).

## Stato al 02/11/2026

In produzione su `https://jobspy.intecha.dev` dietro Authentik, container `jobspy-api` (Coolify), commit `d7d05b2`.

| Dato | Valore |
|---|---|
| Canali | 24 (13 LinkedIn/Indeed su Verona, 4 remoti, 2 inPA, 2 Remotive, temi droni / robotica / stampa 3D) |
| Offerte | 1958 dal 17/09, 249 nel feed, 1038 archiviate |
| Analisi | 2987 esecuzioni, **278 in errore (9%)**, ~6,1 M token, punteggio medio **21** |
| Verdetti | 30 preferiti, **654 scartati** |
| Candidature | 5 tracciate |
| DB | `feedback.db` 46 MB; backup giornalieri in `/data/backups` (16 file, 559 MB) **sullo stesso volume** |
| Test | 43, verdi (`unittest`) |

Lettura dei numeri:

- **Il feed è rumoroso**: 654 scarti contro 30 preferiti e punteggio medio 21. La maggior parte del lavoro di Ale è ancora buttare via.
- **I canali non rispecchiano l'obiettivo**: l'obiettivo è **full remote in AI/ML**, ma metà dei canali
  è "informatico / sviluppatore / IT manager a Verona" e altri sono temi laterali. 3 canali (full stack, backend, embedded) danno 0 risultati.
- **Lavoro fermo su branch**: PR [#9](https://github.com/dagdaAle/JobSpy/pull/9) (modifica canale) e
  [#10](https://github.com/dagdaAle/JobSpy/pull/10) (analisi v3 orientata alla decisione + filtri dei canali) aperte dal 19/10;
  [#1](https://github.com/dagdaAle/JobSpy/pull/1) (CLAUDE.md) dal 18/09; [#11](https://github.com/dagdaAle/JobSpy/pull/11) (ignora `graphify-out/`).

## Principi trasversali (gli stessi di todo-app e BuyWatcher)

- **Tutto interrogabile da un LLM via MCP**: oggi lo è quasi tutto (canali, offerte, verdetti, candidature, log, analisi),
  **ma non il modulo CV** né la modifica dei canali.
- **Pensata per il server e per più client**: web oggi, telefono domani, stessa API.
- **Backend fatto bene**: strati, migrazioni, contratto API stabile (ARCHITECTURE.md).
- **Onestà sui dati**: ciò che non si sa resta "non noto". Punteggio `null` non è punteggio basso, RAL assente non è zero,
  sede ignota non è incompatibile. Il principio c'è già nel prompt e va tenuto.

## Utenti

- **Ale**: legge il feed, decide, si candida, tiene traccia. Da Mac e da telefono.
- **Hermes / Claude**: riassume le novità, crea canali, registra candidature e note, prepara un CV adattato.

App per una persona sola. Niente multi-utente.

## Le pagine (oggi)

1. **Feed**: offerte nuove e attive dei canali, con filtri, punteggio e motivo; preferiti e scarti.
2. **Offerta** (pannello laterale): analisi completa, dati ricchi (RAL, livello, azienda), candidatura.
3. **Candidature**: elenco con stato, prossimo passo, CV usato.
4. **CV**: libreria, CV adattato a un'offerta, revisione con modifiche selezionabili, anteprima ed export PDF.
5. **Analytics**: KPI, competenze, aziende, settori, remoto per sito.
6. **Log**: esecuzioni dei canali e dell'analisi.

## Obiettivi

- Aprire il feed e capire in meno di 10 secondi se oggi c'è un'offerta a cui candidarsi.
- **Rapporto preferiti/scarti molto più alto di oggi** (1:22): meno offerte, più pertinenti.
- Ogni giudizio è spiegato: perché candidarsi, perché no, cosa manca per decidere (`apply / maybe / skip` della PR #10).
- Hermes può fare tutto quello che fa Ale nella UI, CV compresi.
- Pezzo da portfolio AI/ML: valutazione LLM con output a schema, cache invalidata da CV/prompt/modello,
  **e un sistema di misura della qualità** (vedi sotto).

## Non obiettivi

- **Non** un bot che si candida da solo: compilare e inviare resta una decisione di Ale.
- **Non** una libreria di scraping da pubblicare: `jobspy/` resta il fork upstream, il PyPI non si tocca.
- **Non** multi-utente, **non** un'app mobile nativa.
- **Non** copertura di tutti i siti: meglio poche fonti che danno offerte utili.

## Anti-obiettivi (se succede, il progetto è fallito anche se funziona)

- Il feed resta pieno di offerte fuori tema: Ale smette di aprirlo e torna a cercare a mano.
- Un punteggio alto su un'offerta incompatibile (remoto solo USA, sede lontana) fa perdere tempo a una candidatura.
- L'IP di casa viene bloccato da LinkedIn o Indeed per colpa dei refresh.
- Un dato personale (CV, candidature, chiave DeepSeek) finisce nella repo pubblica.
- Si perdono i verdetti: sono l'unico dato non rigenerabile.

## Misurare l'AI **(scelta di Claude)**

Le soglie e il prompt (`v2-verona-italy`, poi v3 nella PR #10) non sono mai stati misurati. I dati per farlo ci sono già:
**716 eventi di feedback** (preferiti e scarti) nel DB.

- set etichettato: offerte con verdetto di Ale (preferito = positivo, scartato = negativo), congelato in un file fuori dalla repo pubblica;
- script che rilancia l'analisi sul set e misura: preferiti sotto soglia, scarti sopra soglia, `skip` su offerte poi preferite;
- confronto tra prompt e modelli sullo stesso set prima di cambiarli; il report va allegato alla PR.
- capire e ridurre il **9% di analisi in errore** prima di qualunque altra ottimizzazione.

## Decisioni da prendere **(proposte di Claude)**

1. **PR aperte**: mergiare #11, poi #10 (contiene #9, che si chiude come inclusa), deploy, misurare costo e risultato della rianalisi.
   #1 (CLAUDE.md) si aggiorna e diventa `AGENTS.md` + `CLAUDE.md` come nelle altre app.
2. **Canali ripensati sull'obiettivo**: canali AI/ML e Python/backend in remoto dall'Italia ed EU come nucleo; Verona come secondo
   binario solo se Ale lo vuole ancora; via (archiviati, non cancellati) i canali a 0 risultati e i temi laterali che non producono preferiti.
3. **Prompt**: oggi dice di *non penalizzare* Verona rispetto al remoto. Se l'obiettivo è full remote, il prompt va cambiato
   (cambio di regola → PR sua, con report di misura).
4. **Backup fuori dal server**: i backup giornalieri ci sono ma stanno sullo stesso volume del DB (DAT-01 dell'audit resta aperto).
   Copia notturna fuori dal server + retention (oggi 559 MB e cresce).
5. **Canali archiviabili** invece che cancellabili, come gruppi in todo-app e topic in BuyWatcher.
6. **MCP**: aggiungere i tool del modulo CV (elenco, dettaglio, adattamento, revisione) e `update_channel` con i filtri della PR #10.
7. **Lingua della repo**: la PR #1 fissa l'inglese per codice e commit (è un fork). I documenti in `docs/` sono in italiano come nelle app sorelle:
   confermare questa eccezione.

## Fasi **(scelta di Claude)**

1. **Consolidare**: merge delle PR aperte, deploy, backup fuori dal server, canali ripuliti, AGENTS.md.
2. **Backend**: `webapp/` a strati `routers → services → repositories`, SQLAlchemy + Alembic, `/api/v1` con Problem Details,
   `uv` e Python 3.13. La logica (dedup, storico, cache delle analisi, CV) si sposta senza cambiare comportamento: i 43 test fanno da rete.
3. **MCP completo**: CV, modifica canali, filtri.
4. **Frontend**: pagine separate, client generato da OpenAPI, stesso design system delle app sorelle.
5. **Qualità AI**: set etichettato dai verdetti, script di misura, calibrazione di prompt e soglie.

## Domande aperte

- **Verona conta ancora?** O il feed deve essere solo remoto? Cambia canali, prompt e filtri.
- **inPA**: 44 bandi nel canale "tutti" con 9 nuovi: servono davvero o sono rumore?
- **DeepSeek**: si resta su un provider remoto (riceve CV e annunci) o si prova un modello locale sulla RTX 3060, misurando la differenza?
- **Upstream**: il fork è 40 commit dietro `speedyapply/JobSpy` (ultimo 27/10). Si allinea periodicamente o si congela la libreria?
