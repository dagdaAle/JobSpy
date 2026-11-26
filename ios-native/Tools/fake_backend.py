"""Local backend for the iOS app with a throwaway DB of FAKE data (repo is public: no real jobs or names).

    cd webapp && FEEDBACK_DB=/tmp/jobspy-ios.db MOBILE_API_KEY=devkey python ../ios-native/Tools/fake_backend.py

Seeds channels, jobs with every kind of analysis, verdicts, applications and a CV, and replaces the
DeepSeek call of the CV tailoring with a canned answer so the whole CV match flow works offline.
"""
import json
import os
import sys

sys.path[:0] = [os.getcwd(), os.path.dirname(os.getcwd())]
os.environ.setdefault("DEEPSEEK_API_KEY", "")
import uvicorn  # noqa: E402

import app  # noqa: E402
import cv_match  # noqa: E402
import storage  # noqa: E402

CV = """# Mario Rossi
Sviluppatore software · Verona · mario.rossi@example.com

## Esperienza
### Sviluppatore backend — Azienda Esempio Srl (2023 – oggi)
- Sviluppo di API REST in Python con FastAPI e PostgreSQL.
- Automazione dei test e dei rilasci con GitHub Actions.

### Stagista IT — Studio Demo Snc (2021 – 2022)
- Supporto agli utenti e manutenzione della rete aziendale.

## Formazione
Laurea in Informatica, Università di Esempio (2021)

## Competenze
Python, FastAPI, SQL, Git, Linux
"""


def job(n, title, company, location, site="linkedin", **extra):
    return {"job_url": f"https://example.com/jobs/{n}", "site": site, "title": title, "company": company,
            "location": location, "date_posted": extra.pop("date_posted", "2026-11-24"),
            "description": f"Annuncio di prova per {title} presso {company}. Dati finti per lo sviluppo dell'app iOS.",
            **extra}


JOBS = [
    job(1, "Sviluppatore Python backend", "Azienda Esempio Srl", "Verona, Veneto", salary_min=38000, salary_max=45000,
        salary_currency="EUR", salary_interval="yearly", job_type="fulltime", skills="Python, FastAPI, PostgreSQL, Docker"),
    job(2, "Data engineer", "Dati Demo SpA", "Verona, Veneto", site="indeed", job_type="fulltime", skills="Python, SQL, Airflow"),
    job(3, "Full stack developer React", "Prova Software Srl", "Villafranca di Verona, Veneto", is_remote="False"),
    job(4, "Tecnico IT di supporto", "Servizi Fittizi Srl", "San Giovanni Lupatoto, Veneto", site="indeed"),
    job(5, "Machine learning engineer", "Esempio AI Srl", "Remoto", site="remotive", is_remote="True",
        salary_min=50000, salary_currency="EUR", salary_interval="yearly"),
    job(6, "Sviluppatore Java senior", "Banca Esempio", "Milano, Lombardia", date_posted="2026-11-20"),
    job(7, "Analista funzionale", "Consulenze Demo Srl", "Verona, Veneto", date_posted="2026-11-22"),
    job(8, "DevOps engineer", "Cloud Fittizio Srl", "Padova, Veneto", site="indeed", date_posted="2026-11-21"),
    job(9, "Sviluppatore PHP", "Web Prova Snc", "Vicenza, Veneto", date_posted="2026-11-10"),
]


def analysis(decision, score, summary, **a):
    base = {"work_mode": "onsite", "location_fit": "compatible", "location_reason": "Verona, in zona.",
            "confidence": "medium", "missing_requirements": [], "cv_match": [], "blockers": []}
    return {"relevance_score": score, "summary": summary, "reasons": [summary], "tags": a.pop("tags", []),
            "assessment": {**base, "decision": decision, **a}}


ANALYSES = {
    1: analysis("apply", 82, "Stack Python e FastAPI come nel CV, sede a Verona e RAL indicata.", work_mode="hybrid",
                cv_match=["Python", "FastAPI", "PostgreSQL", "Git", "Linux"], missing_requirements=["Docker"],
                tags=["Backend", "Python", "Ibrido"], seniority="mid", stack=["Python", "FastAPI", "PostgreSQL"]),
    2: analysis("maybe", 61, "Ruolo dati vicino al CV, ma chiede Airflow e due anni su pipeline.",
                cv_match=["Python", "SQL"], missing_requirements=["Airflow", "Spark"], tags=["Dati", "Python"]),
    3: analysis("maybe", 55, "Full stack con React: metà dello stack è nuovo.", location_fit="unknown",
                location_reason="Sede da verificare: l'annuncio cita più uffici.", cv_match=["Git"],
                missing_requirements=["React", "TypeScript"], tags=["Full stack", "React"]),
    5: analysis("apply", 77, "ML engineer da remoto in Italia, RAL sopra soglia.", work_mode="remote", remote_scope="italy",
                cv_match=["Python", "SQL", "Linux"], missing_requirements=["PyTorch"], tags=["AI/ML", "Remoto"]),
    6: analysis("skip", 20, "Senior Java a Milano in presenza.", location_fit="incompatible",
                location_reason="Milano in presenza, fuori zona.", blockers=["Sede a Milano, presenza 5 giorni"],
                cv_match=[], missing_requirements=["Java", "Spring"], tags=["Backend", "Java"], seniority="senior"),
    7: {"relevance_score": None, "summary": "", "reasons": [], "tags": [], "assessment": {
        "work_mode": "unknown", "location_fit": "unknown", "location_reason": "", "confidence": "low",
        "missing_requirements": []}},
    8: analysis("maybe", 58, "DevOps a Padova, ibrido due giorni.", work_mode="hybrid", cv_match=["Linux", "Git"],
                missing_requirements=["Kubernetes", "Terraform"], tags=["DevOps"]),
}


def seed():
    storage.init_db()
    for area in app._AREAS:
        area.store.init_tables()
    if storage.list_channels():
        return
    c1 = storage.create_channel(site="linkedin", search_term="python", name="Backend Python · Verona", location="Verona")
    c2 = storage.create_channel(site="indeed", search_term="dati", name="Dati e AI", location="Verona")
    c3 = storage.create_channel(site="remotive", search_term="machine learning", name="ML da remoto", is_remote=True)
    by_site = {"linkedin": c1, "indeed": c2, "remotive": c3}
    for j in JOBS:
        storage.upsert_channel_jobs(by_site[j["site"]], [j])
    for n, a in ANALYSES.items():
        storage.set_analysis(f"https://example.com/jobs/{n}", a, context_key="legacy")  # survives the startup context
    storage.add_log({"kind": "refresh", "trigger": "scheduler", "channel_id": c1, "site": "linkedin", "found": 5, "new_count": 2})
    storage.add_log({"kind": "refresh", "trigger": "scheduler", "channel_id": c2, "site": "indeed", "found": 4, "new_count": 1})
    log = storage.start_log({"kind": "refresh", "trigger": "scheduler", "channel_id": c3, "site": "remotive"})
    storage.finish_log(log, {"status": "error", "error": "HTTP 429 dalla fonte"})
    storage.set_feedback("https://example.com/jobs/8", "like", title="DevOps engineer", company="Cloud Fittizio Srl", site="indeed")
    storage.set_feedback("https://example.com/jobs/9", "dislike", title="Sviluppatore PHP", company="Web Prova Snc", site="linkedin")
    storage.set_application("https://example.com/jobs/4", "applied", applied_on="2026-11-10", follow_up_on="2026-11-20",
                            next_step="Richiamare la selezione", contact="Ufficio personale")
    storage.set_application("https://example.com/jobs/7", "interview", applied_on="2026-11-05", follow_up_on="2026-12-02",
                            next_step="Colloquio tecnico")
    with storage._connect() as conn:  # one archived job for the Archivio view
        conn.execute("UPDATE jobs SET archived_at='2026-11-25 08:00:00', archive_reason='stale' WHERE job_url=?",
                     ("https://example.com/jobs/6",))
    storage.create_cv("CV Mario Rossi", CV)
    storage.set_job_keywords("https://example.com/jobs/1", {
        "role": "Sviluppatore Python backend", "company": "Azienda Esempio Srl", "seniority": "mid", "experience_years": 2,
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"], "preferred_skills": ["Kubernetes", "Redis"],
        "keywords": ["API REST", "CI/CD", "microservizi"]})


def fake_chat(_prompt, _user, _max_tokens):
    return {"patches": [
        {"before": "Sviluppo di API REST in Python con FastAPI e PostgreSQL.",
         "after": "Sviluppo di API REST e microservizi in Python con FastAPI, PostgreSQL e Docker.",
         "reason": "Porta «microservizi» e «Docker», confermata da te.", "keywords": ["microservizi", "Docker"]},
        {"before": "Automazione dei test e dei rilasci con GitHub Actions.",
         "after": "Automazione di test e rilasci (CI/CD) con GitHub Actions.",
         "reason": "Usa il termine dell'annuncio «CI/CD».", "keywords": ["CI/CD"]},
    ]}


if __name__ == "__main__":
    seed()
    cv_match._chat = fake_chat
    uvicorn.run(app.app, host="127.0.0.1", port=int(os.environ.get("PORT", "8099")))
