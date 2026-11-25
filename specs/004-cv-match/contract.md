# Contratto API (vincolante per backend e frontend)

Errori: 404 offerta/CV non trovati, 503 `"Manca la chiave API DeepSeek"`, 502 risposta del modello non valida,
409 CV cambiato (source_hash diverso), 422 modifiche non valide.

## GET /cvs/{cv_id}/match?job_url=<url>[&refresh=1]
Estrae (o legge da `job_keywords`) i requisiti dell'annuncio e calcola il punteggio del CV. Prima chiamata
per un'offerta: una chiamata DeepSeek. `refresh=1` rifà l'estrazione.

```ts
interface JobKeywords {
  role: string; company: string; seniority: string | null; experience_years: number | null;
  required_skills: string[]; preferred_skills: string[]; keywords: string[];
}
interface MatchKeyword { term: string; kind: "required" | "preferred" | "keyword"; found: boolean }
interface MatchReport {
  cv_id: number; job_url: string;
  overall: number;                       // 0-100 intero
  components: {                          // 0-100 intero o null se non valutabile
    keyword_match: number | null; skills_coverage: number | null; title_match: number | null;
    section_completeness: number | null; date_consistency: number | null;
  };
  keywords: MatchKeyword[];              // senza duplicati (case-insensitive), required prima
  job: JobKeywords;
}
```

## POST /cvs/{cv_id}/tailor-proposal
Body `{ job_url: string, attested: string[] }` (attested = parole mancanti confermate, max 30).

```ts
interface TailorPatch { before: string; after: string; reason: string; keywords: string[] }
interface TailorProposal {
  source_hash: string;                   // sha256 del markdown del CV, come cv_review
  patches: TailorPatch[];                // max 12, già validate
  rejected: number;                      // modifiche scartate dai controlli
  score_before: number; score_after: number;  // score_after = applicando tutte le patches
}
```

## POST /cvs/tailor (esteso, 201)
Body `{ job_url, base_cv_id?: number|null, attested?: string[], patches?: TailorPatch-like[{before,after,reason}], source_hash?: string }`.
- Con `patches` (+ `source_hash` obbligatorio): applica le patch scelte al CV base, rivalidate.
- Senza `patches` (vecchi client, MCP): genera la proposta e applica tutte le patch valide.
Crea un CV `kind="tailored"` (changes = i `reason`). Risposta:

```ts
{ cv: Cv; score_before: number; score_after: number }
```
