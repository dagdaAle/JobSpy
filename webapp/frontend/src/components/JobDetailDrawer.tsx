import { useEffect } from "react";
import { Icon } from "./Icon";
import { useJobDetail } from "../hooks";
import type { Analysis, Feedback, Job } from "../api/types";
import { parseSkills, salaryLabel, scoreColor, timeAgo } from "../lib/format";

interface Props {
  job: Job;
  analysis?: Analysis;
  feedback?: Feedback;
  onClose: () => void;
}

export function JobDetailDrawer({ job, analysis, onClose }: Props) {
  const detail = useJobDetail(job.job_url);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "auto";
    };
  }, [onClose]);

  // Merge the (light) list job with the full detail once it arrives.
  const full: Job = { ...job, ...(detail.data?.job ?? {}) };
  const ana: Analysis | undefined = detail.data?.analysis ?? analysis;

  const score = ana?.relevance_score ?? null;
  const skills = parseSkills(full.skills);
  const salary = salaryLabel(full);
  const applyUrl = full.job_url_direct || full.job_url;
  const meta = [full.company, full.is_remote ? "Remote" : full.location, salary]
    .filter(Boolean)
    .join(" • ");
  const loading = detail.isLoading;

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/80 flex items-start md:items-center justify-center p-4 md:p-8 overflow-y-auto"
      style={{ backdropFilter: "blur(8px)" }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-3xl bg-surface border-thick border-black neo-shadow-lg my-auto max-h-[92vh] overflow-y-auto"
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="sticky top-4 float-right mr-4 z-[70] bg-primary-fixed text-on-primary-fixed p-2 border-thick border-black neo-button"
          aria-label="Chiudi"
        >
          <Icon name="close" />
        </button>

        {/* Header banner */}
        <div className="relative bg-primary-container p-margin-page pb-6">
          <div
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage:
                "repeating-linear-gradient(45deg, #000 0, #000 1px, transparent 0, transparent 50%)",
              backgroundSize: "10px 10px",
            }}
          />
          <div className="relative z-10 pr-10">
            <span className="text-meta-xs uppercase text-on-primary-fixed opacity-70">
              {full.site} · {timeAgo(full.date_posted)}
            </span>
            <h2 className="text-headline-lg md:text-headline-xl uppercase text-on-primary-fixed leading-tight mt-1">
              {full.title}
            </h2>
            <p className="text-headline-md uppercase text-on-primary-fixed opacity-80 mt-1">
              {meta}
            </p>
          </div>
        </div>

        <div className="p-margin-page space-y-8">
          {/* Apply actions */}
          <div className="flex gap-4">
            <a
              href={applyUrl}
              target="_blank"
              rel="noreferrer"
              className="flex-1 bg-primary-fixed text-on-primary-fixed py-3 text-headline-md uppercase border-thick border-black neo-shadow hover:-translate-y-1 transition-all text-center"
            >
              CANDIDATI ORA
            </a>
            <a
              href={full.job_url}
              target="_blank"
              rel="noreferrer"
              className="bg-surface p-3 border-thick border-black neo-button flex items-center"
              title="Apri annuncio originale"
            >
              <Icon name="open_in_new" />
            </a>
          </div>

          {/* AI analysis */}
          {ana && (score != null || ana.summary) && (
            <div className="bg-surface-container border-thick border-black p-6 neo-shadow">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-meta-sm uppercase text-secondary-fixed">AI Analysis</h4>
                {score != null && (
                  <span className={`font-black px-2 py-1 text-sm border-thin border-black bg-black/40 ${scoreColor(score).text}`}>
                    {score}%
                  </span>
                )}
              </div>
              {ana.summary && (
                <p className="text-body-md text-on-surface mb-4">{ana.summary}</p>
              )}
              {ana.reasons && ana.reasons.length > 0 && (
                <ul className="space-y-2 mb-4">
                  {ana.reasons.map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Icon name="chevron_right" className="text-secondary-fixed text-base mt-0.5" />
                      <span className="text-meta-sm text-on-surface-variant">{r}</span>
                    </li>
                  ))}
                </ul>
              )}
              {ana.tags && ana.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {ana.tags.map((t) => (
                    <span key={t} className="text-[10px] font-black px-1.5 py-0.5 bg-tertiary-container text-on-tertiary-container uppercase">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Details grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {full.job_type && <Detail label="Tipo" value={full.job_type} />}
            {full.job_level && <Detail label="Livello" value={full.job_level} />}
            {full.company_industry && <Detail label="Settore" value={full.company_industry} />}
            {full.job_function && <Detail label="Funzione" value={full.job_function} />}
            {salary && <Detail label="RAL" value={salary} />}
            {full.emails && <Detail label="Contatto" value={full.emails} mono />}
          </div>

          {skills.length > 0 && (
            <div>
              <h5 className="text-meta-xs uppercase text-outline mb-2">Skills</h5>
              <div className="flex flex-wrap gap-1">
                {skills.map((s) => (
                  <span key={s} className="bg-black border-thin border-outline px-2 py-1 text-[10px] uppercase">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <section className="space-y-3">
            <h3 className="text-headline-md uppercase border-b-thick border-secondary-fixed inline-block">
              Descrizione
            </h3>
            {loading ? (
              <p className="text-body-md text-outline animate-pulse">Caricamento dettaglio…</p>
            ) : (
              <div className="text-body-md leading-relaxed text-on-surface-variant whitespace-pre-line">
                {full.description || "Nessuna descrizione disponibile per questo annuncio."}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="border-thin border-black bg-black/40 p-3">
      <h5 className="text-meta-xs uppercase text-outline mb-1">{label}</h5>
      <p className={`text-meta-sm ${mono ? "break-all" : "uppercase"}`}>{value}</p>
    </div>
  );
}
