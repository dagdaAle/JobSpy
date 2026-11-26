import Foundation

// Models mirror the backend JSON (webapp/app.py, specs/005-ios-app/contract.md). They are tolerant:
// almost everything is optional and numbers/booleans may arrive as strings (SQLite text columns).
// No convertFromSnakeCase: analysis/feedback/applications maps are keyed by job_url.

/// A number that may arrive as `38000`, `38000.0` or `"38000"`.
nonisolated struct Num: Codable, Sendable, Hashable {
    let value: Double
    init(_ value: Double) { self.value = value }
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let d = try? c.decode(Double.self) { value = d; return }
        if let s = try? c.decode(String.self), let d = Double(s.trimmingCharacters(in: .whitespaces)) { value = d; return }
        throw DecodingError.dataCorruptedError(in: c, debugDescription: "not a number")
    }
    func encode(to encoder: Encoder) throws { var c = encoder.singleValueContainer(); try c.encode(value) }
}

/// A boolean that may arrive as `true`, `1` or `"True"`.
nonisolated struct Flag: Codable, Sendable, Hashable {
    let value: Bool
    init(_ value: Bool) { self.value = value }
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let b = try? c.decode(Bool.self) { value = b; return }
        if let i = try? c.decode(Int.self) { value = i != 0; return }
        if let s = try? c.decode(String.self) { value = ["true", "1", "yes"].contains(s.lowercased()); return }
        value = false
    }
    func encode(to encoder: Encoder) throws { var c = encoder.singleValueContainer(); try c.encode(value) }
}

nonisolated enum Verdict: String, Codable, Sendable { case like, dislike }

nonisolated struct JobSource: Codable, Sendable, Hashable {
    struct Requirement: Codable, Sendable, Hashable { let text: String; let priority: String? }
    struct Reality: Codable, Sendable, Hashable { let repost_count: Int?; let mass_posting_count: Int?; let fake_freshness: Bool? }
    let slug: String?
    let origin: String?
    let requirements: [Requirement]?
    let suspect: Bool?
    let reality: Reality?
    let closed_at: String?
}

nonisolated struct Job: Codable, Sendable, Hashable, Identifiable {
    let job_url: String
    var site: String?
    var title: String?
    var company: String?
    var location: String?
    var is_remote: Flag?
    var job_type: String?
    var date_posted: String?
    var is_new: Flag?
    var first_seen_at: String?
    var feed_since: String?
    var archived_at: String?
    var duplicates: Int?
    var duplicate_urls: [String]?
    var job_url_direct: String?
    var company_industry: String?
    var job_level: String?
    var job_function: String?
    var emails: String?
    var skills: String?
    var description: String?
    var salary_min: Num?
    var salary_max: Num?
    var salary_currency: String?
    var salary_interval: String?
    var source_closed_at: String?
    var source_suspect: Flag?
    var source: JobSource?

    var id: String { job_url }
    var displayTitle: String { title?.isEmpty == false ? title! : "Offerta senza titolo" }
    var remote: Bool { is_remote?.value == true }
    var isNew: Bool { is_new?.value == true }

    /// The detail payload has more fields: keep ours where the detail has none.
    func merged(with detail: Job) -> Job {
        var out = detail
        out.location = location ?? detail.location
        out.duplicates = detail.duplicates ?? duplicates
        out.duplicate_urls = detail.duplicate_urls ?? duplicate_urls
        out.is_new = detail.is_new ?? is_new
        return out
    }
}

nonisolated struct Assessment: Codable, Sendable, Hashable {
    var work_mode: String?
    var location_fit: String?
    var location_reason: String?
    var confidence: String?
    var missing_requirements: [String]?
    var decision: String?
    var remote_scope: String?
    var seniority: String?
    var stack: [String]?
    var salary: String?
    var languages: [String]?
    var cv_match: [String]?
    var blockers: [String]?
}

nonisolated struct Analysis: Codable, Sendable, Hashable {
    var assessment: Assessment?
    var relevance_score: Int?
    var tags: [String]?
    var summary: String?
    var reasons: [String]?

    init(assessment: Assessment? = nil, relevance_score: Int? = nil, tags: [String]? = nil, summary: String? = nil, reasons: [String]? = nil) {
        self.assessment = assessment; self.relevance_score = relevance_score; self.tags = tags; self.summary = summary; self.reasons = reasons
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        // An empty assessment ({}) is "no assessment", like the web app's optional chaining.
        let a = try c.decodeIfPresent(Assessment.self, forKey: .assessment)
        assessment = a == Assessment() ? nil : a
        relevance_score = (try? c.decodeIfPresent(Num.self, forKey: .relevance_score)).flatMap { $0.map { Int($0.value.rounded()) } }
        tags = try c.decodeIfPresent([String].self, forKey: .tags)
        summary = try c.decodeIfPresent(String.self, forKey: .summary)
        reasons = try c.decodeIfPresent([String].self, forKey: .reasons)
    }

    enum CodingKeys: String, CodingKey { case assessment, relevance_score, tags, summary, reasons }
}

nonisolated enum ApplicationStatus: String, Codable, Sendable, CaseIterable {
    case to_apply, applied, contacted, interview, offer, rejected, withdrawn
}

nonisolated struct Application: Codable, Sendable, Hashable {
    var job_url: String
    var status: ApplicationStatus
    var applied_on: String?
    var follow_up_on: String?
    var notes: String = ""
    var next_step: String = ""
    var contact: String = ""
    var cv_label: String = ""
    var cv_id: Int?
    var updated_at: String?

    init(job_url: String, status: ApplicationStatus) { self.job_url = job_url; self.status = status }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        job_url = try c.decode(String.self, forKey: .job_url)
        status = (try? c.decode(ApplicationStatus.self, forKey: .status)) ?? .to_apply
        applied_on = try c.decodeIfPresent(String.self, forKey: .applied_on)
        follow_up_on = try c.decodeIfPresent(String.self, forKey: .follow_up_on)
        notes = try c.decodeIfPresent(String.self, forKey: .notes) ?? ""
        next_step = try c.decodeIfPresent(String.self, forKey: .next_step) ?? ""
        contact = try c.decodeIfPresent(String.self, forKey: .contact) ?? ""
        cv_label = try c.decodeIfPresent(String.self, forKey: .cv_label) ?? ""
        cv_id = try c.decodeIfPresent(Int.self, forKey: .cv_id)
        updated_at = try c.decodeIfPresent(String.self, forKey: .updated_at)
    }

    /// POST /applications body (ApplicationRequest): updated_at is server-side only.
    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(job_url, forKey: .job_url)
        try c.encode(status, forKey: .status)
        try c.encode(applied_on, forKey: .applied_on)
        try c.encode(follow_up_on, forKey: .follow_up_on)
        try c.encode(notes, forKey: .notes)
        try c.encode(next_step, forKey: .next_step)
        try c.encode(contact, forKey: .contact)
        try c.encode(cv_label, forKey: .cv_label)
        try c.encode(cv_id, forKey: .cv_id)
    }

    enum CodingKeys: String, CodingKey { case job_url, status, applied_on, follow_up_on, notes, next_step, contact, cv_label, cv_id, updated_at }
}

/// Envelope of /jobs, /channels/{id}/jobs and /applications.
nonisolated struct JobsEnvelope: Decodable, Sendable {
    var jobs: [Job]
    var analysis: [String: Analysis]
    var feedback: [String: Verdict]
    var applications: [String: Application]
    var analyzer_configured: Bool?

    init(jobs: [Job] = [], analysis: [String: Analysis] = [:], feedback: [String: Verdict] = [:], applications: [String: Application] = [:]) {
        self.jobs = jobs; self.analysis = analysis; self.feedback = feedback; self.applications = applications
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        jobs = try c.decodeIfPresent([Job].self, forKey: .jobs) ?? []
        analysis = try c.decodeIfPresent([String: Analysis].self, forKey: .analysis) ?? [:]
        // Values are bare verdict strings; tolerate {"verdict": "like"} too.
        let raw = try c.decodeIfPresent([String: VerdictValue].self, forKey: .feedback) ?? [:]
        feedback = raw.compactMapValues(\.verdict)
        applications = try c.decodeIfPresent([String: Application].self, forKey: .applications) ?? [:]
        analyzer_configured = try c.decodeIfPresent(Bool.self, forKey: .analyzer_configured)
    }

    enum CodingKeys: String, CodingKey { case jobs, analysis, feedback, applications, analyzer_configured }
}

nonisolated struct VerdictValue: Decodable, Sendable {
    let verdict: Verdict?
    init(from decoder: Decoder) throws {
        if let s = try? decoder.singleValueContainer().decode(String.self) { verdict = Verdict(rawValue: s); return }
        struct Wrapped: Decodable { let verdict: Verdict? }
        verdict = (try? Wrapped(from: decoder))?.verdict
    }
}

nonisolated struct JobDetail: Decodable, Sendable {
    let job: Job
    let analysis: Analysis?
    let feedback: VerdictValue?
}

nonisolated struct Channel: Codable, Sendable, Hashable, Identifiable {
    let id: Int
    var name: String?
    var site: String?
    var search_term: String?
    var location: String?
    var is_remote: Flag?
    var total_count: Int?
    var new_count: Int?
    var last_refresh_at: String?
    var last_refresh_status: String?
    var distance_km: Int?
    var results_wanted: Int?
    var hours_old: Int?
    var include_keywords: [String]?
    var exclude_keywords: [String]?
    var exclude_companies: [String]?
    var work_mode: String?
    var company_slug: String?

    var title: String { name?.isEmpty == false ? name! : "\(site ?? "")\(search_term.map { ": \($0)" } ?? "")" }
    var failed: Bool { last_refresh_status == "error" }
}

nonisolated struct ChannelsResponse: Decodable, Sendable { let channels: [Channel]; var sites: [String]? }

/// POST /channels (all fields) and PUT /channels/{id} (same body: every field is sent).
nonisolated struct ChannelBody: Codable, Sendable, Equatable {
    var site = "linkedin"
    var search_term = ""
    var name = ""
    var location = "Verona"
    var distance_km = 25
    var results_wanted = 25
    var hours_old: Int? = 7 * 24
    var is_remote = false
    var include_keywords: [String] = []
    var exclude_keywords: [String] = []
    var exclude_companies: [String] = []
    var work_mode = "any"
    var company_slug = ""

    init() {}

    init(_ c: Channel) {
        site = c.site ?? site; search_term = c.search_term ?? ""; name = c.name ?? ""; location = c.location ?? ""
        distance_km = c.distance_km ?? 25; results_wanted = c.results_wanted ?? 25; hours_old = c.hours_old
        is_remote = c.is_remote?.value ?? false; include_keywords = c.include_keywords ?? []
        exclude_keywords = c.exclude_keywords ?? []; exclude_companies = c.exclude_companies ?? []
        work_mode = c.work_mode ?? "any"; company_slug = c.company_slug ?? ""
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(site, forKey: .site); try c.encode(search_term, forKey: .search_term); try c.encode(name, forKey: .name)
        try c.encode(location, forKey: .location); try c.encode(distance_km, forKey: .distance_km)
        try c.encode(results_wanted, forKey: .results_wanted)
        try c.encode(hours_old, forKey: .hours_old) // explicit null = no age limit
        try c.encode(is_remote, forKey: .is_remote); try c.encode(include_keywords, forKey: .include_keywords)
        try c.encode(exclude_keywords, forKey: .exclude_keywords); try c.encode(exclude_companies, forKey: .exclude_companies)
        try c.encode(work_mode, forKey: .work_mode); try c.encode(company_slug, forKey: .company_slug)
    }
}

nonisolated struct ChannelCreated: Decodable, Sendable { let channel: Channel?; let new_count: Int? }

nonisolated struct FreehireCompany: Decodable, Sendable, Hashable, Identifiable {
    let slug: String
    let name: String?
    let job_count: Int?
    var id: String { slug }
}

nonisolated struct LogEntry: Decodable, Sendable, Hashable {
    let id: Int
    let kind: String?
    let channel_id: Int?
    let status: String?
    let error: String?
    let finished_at: String?
}

nonisolated struct Status: Decodable, Sendable, Equatable {
    var analyzer_configured: Bool?
    var cv_loaded: Bool?
    var analysis_pending: Int?
    var analysis_running: Bool?
    var feed_days: Int?
}

nonisolated struct CvSummary: Codable, Sendable, Hashable, Identifiable {
    let id: Int
    var name: String
    var kind: String?
    var parent_id: Int?
    var job_url: String?
    var is_default: Flag?
    var created_at: String?
    var updated_at: String?
    var chars: Int?

    var isBase: Bool { kind != "tailored" }
    var isDefault: Bool { is_default?.value == true }
}

nonisolated struct CvsResponse: Decodable, Sendable { let cvs: [CvSummary] }

nonisolated struct Cv: Decodable, Sendable, Hashable {
    let id: Int
    var name: String
    var kind: String?
    var parent_id: Int?
    var job_url: String?
    var is_default: Flag?
    var markdown: String?
    var changes: [String]?
    var updated_at: String?
}

nonisolated struct CvResponse: Decodable, Sendable { let cv: Cv }

nonisolated struct CvReview: Decodable, Sendable, Hashable {
    let source_hash: String
    var patches: [TailorPatch]
    var observations: [String]?
    var questions: [String]?
}

nonisolated struct RevisionBody: Encodable, Sendable { let source_hash: String; let patches: [TailorBody.Patch] }

// CV match (specs/004-cv-match/contract.md)

nonisolated struct JobKeywords: Decodable, Sendable, Hashable {
    var role: String?
    var company: String?
    var seniority: String?
    var experience_years: Num?
    var required_skills: [String]?
    var preferred_skills: [String]?
    var keywords: [String]?
}

nonisolated struct MatchKeyword: Decodable, Sendable, Hashable, Identifiable {
    let term: String
    let kind: String
    let found: Bool
    var id: String { term }
}

nonisolated struct MatchComponents: Decodable, Sendable, Hashable {
    var keyword_match: Int?
    var skills_coverage: Int?
    var title_match: Int?
    var section_completeness: Int?
    var date_consistency: Int?
}

nonisolated struct MatchReport: Decodable, Sendable, Hashable {
    let cv_id: Int
    let job_url: String
    let overall: Int
    let components: MatchComponents
    let keywords: [MatchKeyword]
    let job: JobKeywords
}

nonisolated struct TailorPatch: Codable, Sendable, Hashable {
    let before: String
    let after: String
    let reason: String
    var keywords: [String]?
}

nonisolated struct TailorProposal: Decodable, Sendable, Hashable {
    let source_hash: String
    let patches: [TailorPatch]
    let rejected: Int
    let score_before: Int
    let score_after: Int
}

nonisolated struct TailorResult: Decodable, Sendable {
    let cv: Cv
    let score_before: Int?
    let score_after: Int?
}

// Request bodies

nonisolated struct FeedbackBody: Encodable, Sendable {
    let job_url: String
    let verdict: Verdict?
    let title: String
    let company: String
    let site: String

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(job_url, forKey: .job_url)
        try c.encode(verdict, forKey: .verdict) // explicit null clears the verdict
        try c.encode(title, forKey: .title)
        try c.encode(company, forKey: .company)
        try c.encode(site, forKey: .site)
    }
    enum CodingKeys: String, CodingKey { case job_url, verdict, title, company, site }
}

nonisolated struct ProposalBody: Encodable, Sendable { let job_url: String; let attested: [String] }

nonisolated struct TailorBody: Encodable, Sendable {
    struct Patch: Encodable, Sendable { let before: String; let after: String; let reason: String }
    let job_url: String
    let base_cv_id: Int
    let attested: [String]
    let patches: [Patch]
    let source_hash: String
}
