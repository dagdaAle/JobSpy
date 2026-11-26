import Foundation

// Port of webapp/frontend/src/components/decision.tsx, JobCard.tsx (reason, work mode) and the
// five components of JobDetailSheet.tsx. Keep it 1:1 with the web app: the backend does not compute these.

nonisolated enum Decision: String, Sendable, CaseIterable {
    case candidati, valuta, lascia, nonnoto

    var label: String {
        switch self {
        case .candidati: "Candidati"
        case .valuta: "Valuta"
        case .lascia: "Lascia"
        case .nonnoto: "Non noto"
        }
    }

    var icon: String {
        switch self {
        case .candidati: "checkmark.circle"
        case .valuta, .nonnoto: "questionmark.circle"
        case .lascia: "xmark.circle"
        }
    }

    var dashed: Bool { self == .nonnoto }

    /// Feed section title, in the web app's order.
    var section: String {
        switch self {
        case .candidati: "Da candidare oggi"
        case .valuta: "Da valutare"
        case .nonnoto: "Non noto"
        case .lascia: "Lascia"
        }
    }

    /// Lavoro: the v3 analysis decision, "non noto" when there is no analysis or no decision.
    init(_ analysis: Analysis?) {
        switch analysis?.assessment?.decision {
        case "apply": self = .candidati
        case "maybe": self = .valuta
        case "skip": self = .lascia
        default: self = .nonnoto
        }
    }
}

nonisolated enum JobText {
    static func reason(_ analysis: Analysis?) -> String? {
        let a = analysis?.assessment
        if let b = a?.blockers?.first { return "Bloccante: \(b)" }
        if let s = analysis?.summary, !s.isEmpty { return s }
        if let r = analysis?.reasons?.first { return r }
        if analysis == nil { return "Analisi AI non ancora fatta: leggi l’annuncio e decidi tu." }
        return nil
    }

    static func workMode(_ job: Job, _ analysis: Analysis?) -> String? {
        let m = analysis?.assessment?.work_mode
        if job.remote || m == "remote" { return "remoto" }
        if m == "hybrid" { return "ibrido" }
        if m == "onsite" { return "in sede" }
        return nil
    }

    static func badgeLabel(_ decision: Decision, _ analysis: Analysis?) -> String {
        guard decision == .nonnoto else { return decision.label }
        return analysis != nil ? "Non noto · dati insufficienti" : "Non noto · da analizzare"
    }

    /// "Verona · ibrido", or nil when nothing is known.
    static func place(_ job: Job, _ analysis: Analysis?) -> String? {
        let parts = [job.location?.components(separatedBy: " · ").first, workMode(job, analysis)].compactMap { $0 }.filter { !$0.isEmpty }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    /// "LinkedIn +2": source plus the number of recognised copies.
    static func sources(_ job: Job) -> String {
        let dups = job.duplicates ?? 1
        return [Fmt.site(job.site), dups > 1 ? "+\(dups - 1)" : ""].filter { !$0.isEmpty }.joined(separator: " ")
    }

    static func salary(_ job: Job, _ analysis: Analysis?) -> String? {
        Fmt.salary(job) ?? analysis?.assessment?.salary.flatMap { $0.isEmpty ? nil : $0 }
    }
}

/// One component of the judgement. An unknown one is dashed with "dati insufficienti", never shown as low.
nonisolated struct Component: Sendable, Equatable, Identifiable {
    enum Tone: Sendable { case ok, warn, block }
    let title: String
    let icon: String
    var verdict: String?
    var tone: Tone?
    var bar: Double?
    var unknown = false
    var text: String?
    var tagsLabel: String?
    var tags: [String] = []
    var rows: [(key: String, value: String?, mono: Bool)] = []
    var id: String { title }

    static func == (l: Component, r: Component) -> Bool {
        l.title == r.title && l.verdict == r.verdict && l.tone == r.tone && l.bar == r.bar && l.unknown == r.unknown
            && l.text == r.text && l.tags == r.tags && l.rows.map(\.key) == r.rows.map(\.key) && l.rows.map(\.value) == r.rows.map(\.value)
    }
}

nonisolated enum Components {
    static func all(_ job: Job, _ analysis: Analysis?) -> [Component] {
        [feasibility(analysis), match(analysis), interest(analysis), career(), conditions(job, analysis)]
    }

    static func feasibility(_ analysis: Analysis?) -> Component {
        let t = "Fattibilità"
        guard let a = analysis?.assessment else {
            return Component(title: t, icon: "questionmark.circle", verdict: "dati insufficienti", unknown: true, text: "Analisi non ancora fatta.")
        }
        if let b = a.blockers, !b.isEmpty {
            return Component(title: t, icon: "xmark.circle", verdict: "✕ bloccante", tone: .block, text: b.joined(separator: "; "))
        }
        if a.location_fit == "incompatible" {
            return Component(title: t, icon: "xmark.circle", verdict: "✕ sede non compatibile", tone: .block, text: a.location_reason)
        }
        if a.location_fit == "unknown" {
            let r = a.location_reason?.isEmpty == false ? a.location_reason : "Sede o vincoli da verificare."
            return Component(title: t, icon: "questionmark.circle", verdict: "⚠ da verificare", tone: .warn, text: r)
        }
        return Component(title: t, icon: "checkmark.circle", verdict: "✓ nessun bloccante", tone: .ok, text: a.location_reason)
    }

    static func match(_ analysis: Analysis?) -> Component {
        let a = analysis?.assessment
        let have = a?.cv_match?.count ?? 0, miss = a?.missing_requirements?.count ?? 0
        guard a != nil, have + miss > 0 else {
            return Component(title: "Corrispondenza", icon: "list.bullet", verdict: "dati insufficienti", unknown: true,
                             text: "Requisiti non estratti dall’annuncio.")
        }
        return Component(title: "Corrispondenza", icon: "list.bullet", verdict: "\(have) di \(have + miss) dal tuo CV",
                         bar: Double(have) / Double(have + miss),
                         tagsLabel: miss > 0 ? "Manca o da verificare:" : nil, tags: a?.missing_requirements ?? [])
    }

    static func interest(_ analysis: Analysis?) -> Component {
        let score = analysis?.relevance_score, tags = analysis?.tags ?? []
        if score == nil && tags.isEmpty {
            return Component(title: "Interesse", icon: "sparkles", verdict: "dati insufficienti", unknown: true,
                             text: "Punteggio non calcolabile con le informazioni dell’annuncio.")
        }
        return Component(title: "Interesse", icon: "sparkles", verdict: score.map { "\($0)%" }, bar: score.map { Double($0) / 100 }, tags: tags)
    }

    static func career() -> Component {
        Component(title: "Carriera", icon: "chart.bar", verdict: "dati insufficienti", unknown: true,
                  text: "L’analisi di oggi non valuta team, crescita o formazione.")
    }

    static func conditions(_ job: Job, _ analysis: Analysis?) -> Component {
        let a = analysis?.assessment
        func v(_ s: String?) -> String? { s?.isEmpty == false ? s : nil }
        return Component(title: "Condizioni", icon: "wallet.bifold", rows: [
            ("RAL", JobText.salary(job, analysis), true),
            ("Contratto", v(job.job_type), false),
            ("Modalità", JobText.workMode(job, analysis), false),
            ("Seniority", Fmt.seniority[a?.seniority ?? ""], false),
            ("Sede", v(a?.location_reason) ?? v(job.location), false),
        ])
    }

    /// The «extra» grid of the detail: only the known values.
    static func extra(_ job: Job, _ analysis: Analysis?) -> [(String, String)] {
        let a = analysis?.assessment
        let pairs: [(String, String?)] = [
            ("Area remota", Fmt.remoteScope[a?.remote_scope ?? ""]),
            ("Stack", a?.stack?.joined(separator: ", ")),
            ("Lingue", a?.languages?.joined(separator: ", ")),
            ("Livello", job.job_level), ("Settore", job.company_industry), ("Funzione", job.job_function), ("Contatto", job.emails),
        ]
        return pairs.compactMap { k, v in v.flatMap { $0.isEmpty ? nil : (k, $0) } }
    }
}

/// Where a job sits for the user: drives the card buttons and the detail actions.
nonisolated enum JobState: Sendable { case open, saved, dismissed, archived }

// Applications (lib/applications.ts)

extension ApplicationStatus {
    nonisolated var label: String {
        switch self {
        case .to_apply: "Da candidare"
        case .applied: "Inviata"
        case .contacted: "Primo contatto"
        case .interview: "Colloquio"
        case .offer: "Offerta ricevuta"
        case .rejected: "Rifiutata"
        case .withdrawn: "Ritirata"
        }
    }
    nonisolated var isClosed: Bool { self == .rejected || self == .withdrawn }
}

extension Application {
    /// The follow-up date is today or past and the application is still open.
    nonisolated func isDue(today: String = Fmt.today()) -> Bool {
        guard !status.isClosed, let f = follow_up_on, !f.isEmpty else { return false }
        return f.prefix(10) <= today
    }
}

/// Groups of the Candidature tab, in pipeline order; closed ones together at the end.
nonisolated enum ApplicationGroups {
    static let order: [(title: String, statuses: [ApplicationStatus])] = [
        ("Da candidare", [.to_apply]), ("Inviate", [.applied]), ("Primo contatto", [.contacted]),
        ("Colloquio", [.interview]), ("Offerta", [.offer]), ("Chiuse", [.rejected, .withdrawn]),
    ]
}

// CV match components and weights (CvMatchPanel.tsx)

nonisolated enum MatchWeights {
    static let rows: [(key: any KeyPath<MatchComponents, Int?> & Sendable, label: String, weight: Int)] = [
        (\.keyword_match, "Parole chiave", 40), (\.skills_coverage, "Competenze", 20), (\.title_match, "Titolo del ruolo", 15),
        (\.section_completeness, "Sezioni", 15), (\.date_consistency, "Date", 10),
    ]
    static let maxAttested = 30

    static func kindLabel(_ kind: String) -> String {
        kind == "required" ? "Obbligatorie" : kind == "preferred" ? "Preferite" : "Altre parole chiave"
    }
}
