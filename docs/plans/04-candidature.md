# Candidature assistite — piano di implementazione

> **Per agenti:** sotto-skill richiesta: superpowers:subagent-driven-development (consigliata) oppure
> superpowers:executing-plans. I passi usano le checkbox (`- [ ]`).

**Obiettivo:** una sola fonte di verità per le candidature, kit generato da JobSpy, bot `jobs` che precompila e traccia via MCP,
promemoria in todo-app.

**Spec:** [PRODUCT.md](../PRODUCT.md) (Candidatura assistita), [ARCHITECTURE.md](../ARCHITECTURE.md) (Candidature),
[adr/008](../adr/008-candidatura-assistita.md), [adr/009](../adr/009-candidature-una-fonte.md).

**Dipende da:** piano 02. Non serve il piano 03.

## Modello

- [ ] Stati nuovi (`da valutare → … → nessuna risposta`) con migrazione degli stati di oggi (`to_apply`, `applied`, `rejected`…).
- [ ] `application_events` con autore (Ale / bot / sistema); `application_files` (PDF inviato, screenshot) salvati su `/data`.
- [ ] Campo "risposte dichiarate" (cosa è stato scritto nel form), visibile solo nell'app, mai in log.
- [ ] Import una tantum delle cartelle `offerte/*/stato.md` del bot (script locale, sul Mac).

## Kit

- [ ] `POST /api/v1/applications/{id}/kit`: CV adattato (riusa `/cvs/tailor`), lettera opzionale, checklist dei campi tipici del portale.
- [ ] Riconoscimento del portale dall'URL di candidatura (Workday, Greenhouse, Lever, Teamtailor, SmartRecruiters, Indeed, LinkedIn, inPA).
- [ ] Le risposte alle domande ricorrenti restano nel bot: il kit dice *quali* servono, il bot le compila.

## Bot `jobs`

- [ ] Tool MCP: `get_application_kit`, `add_application_event`, `attach_application_file`, `set_application_status`.
- [ ] Aggiornare SOUL e skill del profilo `jobs`: la traccia ufficiale è JobSpy; `stato.md` diventa facoltativo.
- [ ] Prova su un portale ATS reale con Ale presente: kit → precompilazione → screenshot → ok → invio → evento `inviata`.

## Seguito

- [ ] A `inviata`: task in todo-app "Richiamare <azienda>" a +10 giorni (via MCP `todo_write__create_task`); a `colloquio`: evento in calendario.
- [ ] Esito: a 30 giorni senza notizie la candidatura propone `nessuna risposta` (Ale conferma).

## Fatto quando

Una candidatura vera fatta da kit a invio con tutto tracciato in JobSpy, nessuno stato tenuto altrove, promemoria in todo-app.
