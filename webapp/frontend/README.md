# JobSpy Frontend (React + Vite + Tailwind)

Modern SPA for the JobSpy web app, rebuilt from the **Stitch "Radical Precision"
Neobrutalist** design system. Replaces the old vanilla `webapp/static/index.html`.

- **Stack:** React 18 + TypeScript + Vite 6 + Tailwind CSS 3 + TanStack Query
- **Design tokens:** ported verbatim from Stitch into `tailwind.config.js`
  (colors, `Space Grotesk` / `JetBrains Mono`, 4px rhythm, hard black offsets,
  0px radius). Component classes (`neo-card`, `neo-button`, `neo-input`) live in
  `src/index.css`.

## Develop

```bash
cd webapp/frontend
npm install
npm run dev          # Vite on http://localhost:5173
```

The dev server proxies API routes (`/search`, `/jobs`, `/channels`, `/job`,
`/status`, `/export`, `/feedback`) to the FastAPI backend. Start the backend
separately, e.g. from `webapp/`:

```bash
uvicorn app:app --reload            # http://localhost:8000
```

Override the backend target with `VITE_BACKEND=http://host:port npm run dev`.

## Build (production)

```bash
npm run build        # type-checks, then emits into ../static
```

`vite build` writes the bundle straight into `webapp/static/`, which FastAPI
serves at `/`. Rebuild after frontend changes, then rebuild the Docker image
(`docker compose up --build`) — the existing Dockerfile copies `webapp/static`.

## Layout

```
src/
  api/        typed client + payload types (mirrors webapp/app.py)
  hooks/      TanStack Query hooks (jobs, channels, search, feedback)
  lib/        formatting helpers (salary, time-ago, score colours)
  components/  TopNav, AiBanner, ChannelBar, FiltersToolbar,
               JobGrid, JobCard, JobDetailDrawer, Footer, Icon
  App.tsx     page composition + client-side filtering
```
