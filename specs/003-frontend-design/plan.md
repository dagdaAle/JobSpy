# Plan: frontend dal design Penpot

Solo `webapp/frontend/`. Nessun cambio al backend.

## Struttura

- `src/index.css`: token del design (chiari e scuri) + `@theme inline` per i nostri colori, font Inter / Outfit /
  JetBrains Mono (`@fontsource-variable/*`, al posto di Geist).
- `src/components/shell/`
  - `Logo.tsx` — marchio SVG + wordmark.
  - `AppShell.tsx` — testata nera (logo, selettore d'area, stato AI, tema), slot barra filtri, colonna sinistra
    (viste + slot filtri), contenuto, `MobileNav` sotto 768 px. Lo usano Lavoro, PA e Gare.
  - `FilterBar.tsx` — barra filtri nera con `FilterField` (icona, etichetta, controllo) e `RangeField`.
  - `Facets.tsx` — gruppo di caselle per faccetta.
- `src/components/decision.tsx` — mappe decisione/esito → etichetta, icona, classi; `DecisionBadge`,
  `Deadline`, `Tag`.
- `src/components/DecisionCard.tsx` — card comune (pannello colorato, chip in alto, X e segnalibro, badge,
  azienda/ente, titolo, monogramma, motivo, tag, numero mono, luogo, «Dettagli»).
- `src/components/FeedSection.tsx` — intestazione con conteggio + griglia.
- `JobCard.tsx`, `area/ItemCard.tsx` → sopra `DecisionCard`.
- `LavoroArea.tsx` → `AppShell`, sezioni per decisione, filtri RAL/modalità/decisione, avvisi.
- `JobDetailSheet.tsx` → testa colorata, numeri, componenti ricavate (`ComponentRow`).
- `area/AreaPage.tsx` → `AppShell`, viste in colonna, sezioni per esito, filtri scadenza/importo.
- `ChannelBar.tsx`, dialog e form: restyle con i token (pillole, raggi).

## Mappature

- Decisione Lavoro: `apply` → candidati, `maybe` → valuta, `skip` → lascia, assente → non noto.
- Motivo in card: primo bloccante, altrimenti `summary`, altrimenti primo `reasons`.
- Componenti nel dettaglio: Fattibilità (bloccanti / `location_fit`), Corrispondenza (`cv_match` vs
  `missing_requirements`), Interesse (`relevance_score` + tag), Carriera (non nota), Condizioni (RAL, contratto,
  modalità, seniority; mancanti in corsivo).

## Verifica

`npm run build`, unittest invariati, controllo nel browser con backend locale e dati di prova (nessun dato vero).
