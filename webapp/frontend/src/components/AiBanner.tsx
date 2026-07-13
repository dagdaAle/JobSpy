import { Icon } from "./Icon";
import type { StatusResponse } from "../api/types";

export function AiBanner({ status }: { status?: StatusResponse }) {
  if (!status) return null;

  if (status.analyzer_configured && status.cv_loaded) {
    return (
      <div className="w-full bg-surface-container border-thick border-black p-4 flex items-center justify-between neo-shadow">
        <div className="flex items-center gap-4">
          <Icon name="check_circle" className="text-headline-lg text-secondary-fixed" />
          <div>
            <h2 className="text-headline-md uppercase text-secondary-fixed">Analizzatore AI attivo</h2>
            <p className="text-body-md text-on-surface-variant">
              Il tuo CV è caricato ({status.cv_chars.toLocaleString("it-IT")} caratteri). Punteggio di rilevanza calcolato automaticamente.
            </p>
          </div>
        </div>
        <span className="text-meta-xs uppercase text-outline hidden md:block">
          max {status.max_analysis_per_search}/ricerca
        </span>
      </div>
    );
  }

  const missingCv = status.analyzer_configured && !status.cv_loaded;
  return (
    <div className="w-full bg-error-container border-thick border-black p-4 flex items-center justify-between neo-shadow">
      <div className="flex items-center gap-4">
        <Icon name="warning" className="text-headline-lg text-on-error-container" />
        <div>
          <h2 className="text-headline-md uppercase text-on-error-container">
            {missingCv ? "CV NON CARICATO" : "ANALIZZATORE AI NON ATTIVO"}
          </h2>
          <p className="text-body-md text-on-error-container opacity-90">
            {missingCv
              ? "Monta un CV PDF per sbloccare il calcolo automatico del punteggio di rilevanza."
              : "Configura la API key DeepSeek per abilitare l'analisi AI dei lavori."}
          </p>
        </div>
      </div>
    </div>
  );
}
