import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API routes handled by the FastAPI backend. In dev these are proxied to the
// running uvicorn server (default :8000). In prod, Vite builds into
// ../static and FastAPI serves both the SPA and the API from the same origin.
const API_ROUTES = [
  "/search",
  "/jobs",
  "/channels",
  "/job",
  "/status",
  "/analytics",
  "/export",
  "/feedback",
];

// The JobSpy backend is exposed on host :8080 (docker-compose maps 8080->8000).
// Override with VITE_BACKEND when running uvicorn directly on another port.
const BACKEND = process.env.VITE_BACKEND ?? "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API_ROUTES.map((route) => [route, { target: BACKEND, changeOrigin: true }]),
    ),
  },
  build: {
    // Emit the production bundle straight into the folder FastAPI serves.
    outDir: "../static",
    emptyOutDir: true,
  },
});
