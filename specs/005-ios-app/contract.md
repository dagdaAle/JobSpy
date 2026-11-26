# Contratto API dell'app iOS (v1, area Lavoro)

Base: `<URL>/mobile`, header `X-Api-Key`. Dettaglio di autenticazione ed errori in
[docs/mobile-api.md](../../docs/mobile-api.md). Le rotte sono quelle della web app, invariate.

## Tipi (come arrivano dal backend)

```ts
Job { job_url, site, title, company?, location?, is_remote?, job_type?, date_posted? ("YYYY-MM-DD"),
  is_new?, first_seen_at?, feed_since?, archived_at? ("YYYY-MM-DD HH:MM:SS" UTC), duplicates?, duplicate_urls?,
  job_url_direct?, company_industry?, job_level?, job_function?, emails?, skills? (stringa CSV o JSON),
  description?, salary_min?, salary_max?, salary_currency?, salary_interval?,
  source_closed_at?, source_suspect?, source? }
Analysis { relevance_score?, tags?, summary?, reasons?, assessment? {
  decision?: "apply"|"maybe"|"skip", work_mode, location_fit, location_reason, confidence,
  missing_requirements[], remote_scope?, seniority?, stack?, salary?, languages?, cv_match?, blockers? } }
Application { job_url, status: "to_apply"|"applied"|"contacted"|"interview"|"rejected"|"offer"|"withdrawn",
  applied_on?, follow_up_on? ("YYYY-MM-DD"), notes, next_step, contact, cv_label, cv_id?, updated_at? }
JobsEnvelope { jobs: Job[], analysis: {job_url: Analysis}, feedback: {job_url: "like"|"dislike"},
  applications: {job_url: Application}, count, analyzer_configured }
Channel { id, site, search_term, name, location, distance_km, is_remote, total_count, new_count,
  last_refresh_at?, last_refresh_status?: "ok"|"error"|"running" }
CvSummary { id, name, kind: "base"|"tailored", parent_id?, job_url?, is_default, created_at, updated_at, chars, template }
MatchReport, TailorProposal: come in specs/004-cv-match/contract.md
```

## Rotte usate

| Metodo | Rotta | Uso nell'app | Timeout |
|---|---|---|---|
| GET | `/status` | banner AI non configurata / analisi in corso | 30 s |
| GET | `/channels` | chip del feed, elenco canali | 30 s |
| POST | `/channels/{id}/refresh` | «Aggiorna» un canale (scraping) | 5 min |
| GET | `/jobs?archived=false` | feed, preferiti, scartati, ricerca | 30 s |
| GET | `/jobs?archived=true` | archivio | 30 s |
| GET | `/channels/{id}/jobs` | feed filtrato per canale | 30 s |
| GET | `/job?url=<job_url>` | dettaglio completo (descrizione) | 30 s |
| POST | `/feedback` `{job_url, verdict: "like"\|"dislike"\|null, title, company, site}` | preferito, scarta, annulla | 30 s |
| POST | `/jobs/restore?url=<job_url>` | rimetti nel feed dall'archivio | 30 s |
| GET | `/applications` | tab Candidature (JobsEnvelope con `applications`) | 30 s |
| POST | `/applications` `Application` | «Prepara candidatura» (stato `to_apply`) | 30 s |
| GET | `/cvs` | scelta del CV, tab CV | 30 s |
| GET | `/cvs/{id}` | testo del CV (tab CV) | 30 s |
| GET | `/cvs/{id}/match?job_url=&refresh=1` | analisi del CV per l'offerta (LLM la prima volta) | 5 min |
| POST | `/cvs/{id}/tailor-proposal` `{job_url, attested[]}` | modifiche proposte (LLM) | 5 min |
| POST | `/cvs/tailor` `{job_url, base_cv_id, attested[], patches[], source_hash}` | salva il CV adattato | 5 min |

`job_url` va sempre in query string con percent-encoding completo (contiene `:`, `/`, `?`, `&`).
