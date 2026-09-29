# JobSpy frontend

React 18, TypeScript, Vite 6, Tailwind CSS 4 e TanStack Query.

## Linee guida UI

Il riferimento attuale è `components.json`: **shadcn base-nova**, primitive
**Base UI**, icone **Lucide**, font **Geist Variable**. Riutilizzare i componenti
in `src/components/ui` (Button, Input, Select, Dialog, Sheet, Table, Card, Badge,
Label, Textarea, Skeleton). Non introdurre un secondo kit UI o select native
per sostituire i componenti già disponibili.

Usare i token semantici di `src/index.css`: background/card, foreground,
muted-foreground, border/input, primary, destructive, score-mid, ecc. Conservare
i raggi, i focus ring, la tipografia e il tema chiaro/scuro esistenti. Le nuove
primitive devono riutilizzare questi token e vivere in `components/ui`.

I form hanno label associate, pulsanti disabilitati durante il salvataggio e
feedback di successo/errore con Sonner. Prevedere caricamento, errore, stato
vuoto e layout mobile. Le tabelle usano il componente Table con scorrimento
orizzontale; i dialog lunghi restano entro l’altezza della finestra.

## Sviluppo

```sh
npm ci
npm run dev
```

Le API sono inoltrate al backend su `http://localhost:8080`; usare
`VITE_BACKEND` per cambiare destinazione. `npm run build` controlla TypeScript e
compila in `../static`. Il Dockerfile esegue la build in uno stage Node.

La pagina Candidature usa filtri propri: i filtri remoto/match delle offerte
non devono nascondere candidature già inviate. I promemoria sono locali alla
pagina e non implicano notifiche email o sincronizzazione con portali esterni.
