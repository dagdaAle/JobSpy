import type { Application, ApplicationStatus } from "../api/types";

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  to_apply: "Da candidare", applied: "Inviata", contacted: "Primo contatto",
  interview: "Colloquio", offer: "Offerta ricevuta", rejected: "Rifiutata", withdrawn: "Ritirata",
};
export const STATUS_ITEMS = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }));
export const isClosed = (app: Application) => ["rejected", "withdrawn"].includes(app.status);
export function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
export const isDue = (app: Application) => !isClosed(app) && !!app.follow_up_on && app.follow_up_on <= today();
export function dateLabel(value?: string | null) {
  return value ? new Date(`${value}T12:00:00`).toLocaleDateString("it-IT") : "—";
}
export const emptyApplication = (jobUrl: string): Application => ({
  job_url: jobUrl, status: "to_apply", applied_on: null, follow_up_on: null,
  notes: "", next_step: "", contact: "", cv_label: "",
});
export const FIELD_LABELS: Record<string, string> = {
  status: "Stato", applied_on: "Data invio", notes: "Note", next_step: "Prossimo passo",
  follow_up_on: "Data prossimo passo", contact: "Contatto", cv_label: "CV utilizzato",
};
