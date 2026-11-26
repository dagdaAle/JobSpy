import XCTest
@testable import JobSpy

/// Fixtures are answers of the local backend seeded by Tools/fake_backend.py: FAKE data only (public repo).
nonisolated final class JobSpyTests: XCTestCase {
    static func data(_ name: String) throws -> Data {
        let url = try XCTUnwrap(Bundle(for: JobSpyTests.self).url(forResource: name, withExtension: "json"), name)
        return try Data(contentsOf: url)
    }

    private func fixture<T: Decodable>(_ name: String, as: T.Type = T.self) throws -> T {
        try APIClient.decoder.decode(T.self, from: Self.data(name))
    }

    // MARK: decoding

    func testDecodesEveryFixture() throws {
        let jobs: JobsEnvelope = try fixture("jobs")
        XCTAssertEqual(jobs.jobs.count, 8) // 9 seeded, 1 archived
        XCTAssertEqual(jobs.feedback["https://example.com/jobs/8"], .like)
        XCTAssertEqual(jobs.feedback["https://example.com/jobs/9"], .dislike)
        XCTAssertEqual(jobs.applications["https://example.com/jobs/4"]?.status, .applied)
        let first = try XCTUnwrap(jobs.jobs.first { $0.job_url == "https://example.com/jobs/1" })
        XCTAssertEqual(first.salary_min?.value, 38000) // arrives as the string "38000"
        XCTAssertFalse(first.remote)

        let archived: JobsEnvelope = try fixture("jobs_archived")
        XCTAssertTrue(archived.jobs.allSatisfy { $0.archived_at != nil })
        let detail: JobDetail = try fixture("job")
        XCTAssertNotNil(detail.job.description)
        XCTAssertEqual(detail.analysis?.assessment?.decision, "apply")
        let channels: ChannelsResponse = try fixture("channels")
        XCTAssertEqual(channels.channels.count, 3)
        XCTAssertTrue(channels.channels.contains(where: \.failed))
        let status: Status = try fixture("status")
        XCTAssertEqual(status.feed_days, 7)
        let cvs: CvsResponse = try fixture("cvs")
        XCTAssertTrue(cvs.cvs[0].isDefault && cvs.cvs[0].isBase)
        let cv: CvResponse = try fixture("cv")
        XCTAssertTrue(cv.cv.markdown?.contains("Mario Rossi") == true)
        let match: MatchReport = try fixture("match")
        XCTAssertNil(match.components.date_consistency)
        XCTAssertTrue(match.keywords.contains { !$0.found })
        let proposal: TailorProposal = try fixture("proposal")
        XCTAssertEqual(proposal.source_hash.count, 64)
        let apps: JobsEnvelope = try fixture("applications")
        XCTAssertEqual(Set(apps.applications.keys), ["https://example.com/jobs/4", "https://example.com/jobs/7"])
        let ch: JobsEnvelope = try fixture("channel_jobs")
        XCTAssertFalse(ch.jobs.isEmpty)
    }

    /// Map keys are job URLs: no key conversion, and an empty assessment is "no assessment".
    func testMapKeysAndEmptyAssessment() throws {
        let json = #"{"jobs":[],"feedback":{"https://x.it/a_b?c=1":"like","https://x.it/d":{"verdict":"dislike"}},"analysis":{"https://x.it/a_b?c=1":{"assessment":{},"tags":[]}}}"#
        let env = try APIClient.decoder.decode(JobsEnvelope.self, from: Data(json.utf8))
        XCTAssertEqual(env.feedback["https://x.it/a_b?c=1"], .like)
        XCTAssertEqual(env.feedback["https://x.it/d"], .dislike)
        XCTAssertNotNil(env.analysis["https://x.it/a_b?c=1"])
        XCTAssertNil(env.analysis["https://x.it/a_b?c=1"]?.assessment)
    }

    // MARK: format

    func testDates() {
        XCTAssertEqual(Fmt.date("2026-11-25 11:13:23"), Fmt.date("2026-11-25T11:13:23Z"))
        let now = Fmt.date("2026-11-25T12:00:00Z")!
        XCTAssertEqual(Fmt.ago("2026-11-25 08:00:00", now: now), "4 ore fa")
        XCTAssertEqual(Fmt.ago("2026-11-25 11:59:40", now: now), "adesso")
        XCTAssertEqual(Fmt.ago("2026-11-25", now: now), "oggi")
        XCTAssertEqual(Fmt.ago("2026-11-24", now: now), "ieri")
        XCTAssertEqual(Fmt.ago("2026-11-20", now: now), "5 giorni fa")
        // 23:30 UTC on the 25th is already the 26th in Rome.
        XCTAssertEqual(Fmt.today(Fmt.date("2026-11-25 23:30:00")!), "2026-11-26")
        XCTAssertEqual(Fmt.daysLeftInFeed("2026-11-20 12:00:00", feedDays: 7, now: now), 2)
        XCTAssertEqual(Fmt.daysUntil("2026-11-27", now: now), 2)
    }

    func testSalarySkillsSiteMonogram() {
        var job = Job(job_url: "u")
        XCTAssertNil(Fmt.salary(job))
        job.salary_min = Num(38000); job.salary_max = Num(45000)
        XCTAssertEqual(Fmt.salary(job), "38–45k €")
        job.salary_max = nil; job.salary_currency = "USD"
        XCTAssertEqual(Fmt.salary(job), "38k $")
        XCTAssertEqual(Fmt.skills(#"["Python","SQL"]"#), ["Python", "SQL"])
        XCTAssertEqual(Fmt.skills("Python, SQL; Docker"), ["Python", "SQL", "Docker"])
        XCTAssertEqual(Fmt.site("weworkremotely"), "We Work Remotely")
        XCTAssertEqual(Fmt.site("xing"), "Xing")
        XCTAssertEqual(Fmt.monogram("Azienda Esempio Srl"), "AE")
        XCTAssertEqual(Fmt.monogram("dati-demo"), "DD")
        XCTAssertEqual(Fmt.monogram(nil), "?")
    }

    // MARK: decision and components (same cases as decision.tsx / JobDetailSheet.tsx)

    private func analysis(_ a: Assessment?, score: Int? = nil, tags: [String]? = nil, summary: String? = nil) -> Analysis {
        Analysis(assessment: a, relevance_score: score, tags: tags, summary: summary)
    }

    func testDecisionAndReason() {
        XCTAssertEqual(Decision(nil), .nonnoto)
        XCTAssertEqual(Decision(analysis(Assessment(decision: "apply"))), .candidati)
        XCTAssertEqual(Decision(analysis(Assessment(decision: "maybe"))), .valuta)
        XCTAssertEqual(Decision(analysis(Assessment(decision: "skip"))), .lascia)
        XCTAssertEqual(Decision(analysis(Assessment())), .nonnoto)
        XCTAssertEqual(JobText.reason(nil), "Analisi AI non ancora fatta: leggi l’annuncio e decidi tu.")
        XCTAssertEqual(JobText.reason(analysis(Assessment(blockers: ["Milano"]), summary: "x")), "Bloccante: Milano")
        XCTAssertEqual(JobText.reason(analysis(nil, summary: "Bella")), "Bella")
        XCTAssertNil(JobText.reason(analysis(nil)))
        XCTAssertEqual(JobText.badgeLabel(.nonnoto, nil), "Non noto · da analizzare")
        XCTAssertEqual(JobText.badgeLabel(.nonnoto, analysis(nil)), "Non noto · dati insufficienti")
        var job = Job(job_url: "u", location: "Verona · Veneto")
        XCTAssertEqual(JobText.place(job, analysis(Assessment(work_mode: "hybrid"))), "Verona · ibrido")
        job.is_remote = Flag(true)
        XCTAssertEqual(JobText.workMode(job, nil), "remoto")
        job.duplicates = 3; job.site = "linkedin"
        XCTAssertEqual(JobText.sources(job), "LinkedIn +2")
    }

    func testFeasibility() {
        XCTAssertTrue(Components.feasibility(nil).unknown)
        let block = Components.feasibility(analysis(Assessment(location_fit: "compatible", blockers: ["A", "B"])))
        XCTAssertEqual([block.verdict, block.text], ["✕ bloccante", "A; B"]); XCTAssertEqual(block.tone, .block)
        XCTAssertEqual(Components.feasibility(analysis(Assessment(location_fit: "incompatible", location_reason: "Milano"))).verdict, "✕ sede non compatibile")
        let unknown = Components.feasibility(analysis(Assessment(location_fit: "unknown", location_reason: "")))
        XCTAssertEqual([unknown.verdict, unknown.text], ["⚠ da verificare", "Sede o vincoli da verificare."]); XCTAssertEqual(unknown.tone, .warn)
        XCTAssertEqual(Components.feasibility(analysis(Assessment(location_fit: "compatible"))).tone, .ok)
    }

    func testMatchInterestCareerConditions() {
        XCTAssertTrue(Components.match(analysis(Assessment())).unknown)
        let m = Components.match(analysis(Assessment(missing_requirements: ["Docker"], cv_match: ["Python", "SQL", "Git"])))
        XCTAssertEqual(m.verdict, "3 di 4 dal tuo CV"); XCTAssertEqual(m.bar, 0.75); XCTAssertEqual(m.tags, ["Docker"])
        XCTAssertTrue(Components.interest(analysis(nil)).unknown)
        let i = Components.interest(analysis(nil, score: 61, tags: ["Dati"]))
        XCTAssertEqual(i.verdict, "61%"); XCTAssertEqual(i.bar, 0.61)
        XCTAssertNil(Components.interest(analysis(nil, tags: ["Dati"])).verdict)
        XCTAssertTrue(Components.career().unknown)
        var job = Job(job_url: "u", location: "Verona")
        job.job_type = "fulltime"
        let c = Components.conditions(job, analysis(Assessment(seniority: "mid", salary: "35k")))
        XCTAssertEqual(c.rows.map(\.value), ["35k", "fulltime", nil, "Mid", "Verona"])
        XCTAssertEqual(Components.all(job, nil).map(\.title), ["Fattibilità", "Corrispondenza", "Interesse", "Carriera", "Condizioni"])
    }

    func testApplicationsDue() {
        var a = Application(job_url: "u", status: .applied)
        XCTAssertFalse(a.isDue(today: "2026-11-26"))
        a.follow_up_on = "2026-11-26"
        XCTAssertTrue(a.isDue(today: "2026-11-26"))
        a.follow_up_on = "2026-11-27"
        XCTAssertFalse(a.isDue(today: "2026-11-26"))
        a.follow_up_on = "2026-11-01"; a.status = .rejected
        XCTAssertFalse(a.isDue(today: "2026-11-26"))
    }

    // MARK: client

    func testQueryEncodingAndErrors() throws {
        XCTAssertEqual(APIClient.q("https://x.it/a?b=1&c=2"), "https%3A%2F%2Fx.it%2Fa%3Fb%3D1%26c%3D2")
        let c = APIClient(base: "https://jobspy.example.com/", key: "k")
        let r = try c.request("/job?url=\(APIClient.q("https://x.it/a"))", long: true)
        XCTAssertEqual(r.url?.absoluteString, "https://jobspy.example.com/mobile/job?url=https%3A%2F%2Fx.it%2Fa")
        XCTAssertEqual(r.value(forHTTPHeaderField: "X-Api-Key"), "k")
        XCTAssertEqual(r.timeoutInterval, APIClient.longTimeout)
        XCTAssertThrowsError(try APIClient(base: "", key: "k").request("/status"))
        XCTAssertEqual(APIClient.error(status: 401, data: Data()).kind, .badKey)
        XCTAssertEqual(APIClient.error(status: 409, data: Data(#"{"detail":"Il CV è cambiato"}"#.utf8)).message, "Il CV è cambiato")
        XCTAssertEqual(APIClient.error(status: 422, data: Data(#"{"detail":[{"msg":"a"},{"msg":"b"}]}"#.utf8)).message, "a; b")
        XCTAssertEqual(APIClient.error(status: 503, data: Data(#"{"detail":"Manca la chiave API DeepSeek"}"#.utf8)).kind, .notConfigured)
    }
}

// MARK: Store with a simulated network

/// Answers by path from the fixtures; per-test overrides for status codes.
nonisolated final class MockProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var overrides: [String: (Int, Data)] = [:]
    nonisolated(unsafe) static var requests: [URLRequest] = []

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func stopLoading() {}

    override func startLoading() {
        var req = request
        if req.httpBody == nil, let body = req.httpBodyStreamData { req.httpBody = body }
        Self.requests.append(req)
        let path = request.url!.path.replacingOccurrences(of: "/mobile", with: "")
        let query = request.url!.query ?? ""
        var status = 200, body = Data("{}".utf8)
        if let o = Self.overrides["\(request.httpMethod!) \(path)"] { (status, body) = o }
        else if let name = Self.fixture(path, query) { body = (try? JobSpyTests.data(name)) ?? body }
        let res = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: ["Content-Type": "application/json"])!
        client?.urlProtocol(self, didReceive: res, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: body)
        client?.urlProtocolDidFinishLoading(self)
    }

    static func fixture(_ path: String, _ query: String) -> String? {
        switch path {
        case "/status": "status"
        case "/channels": "channels"
        case "/jobs": query.contains("archived=true") ? "jobs_archived" : "jobs"
        case "/applications": "applications"
        case "/cvs": "cvs"
        case "/cvs/1/match": "match"
        case "/cvs/1/tailor-proposal": "proposal"
        default: nil
        }
    }

    static func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockProtocol.self]
        return URLSession(configuration: config)
    }
}

nonisolated final class StoreTests: XCTestCase {
    @MainActor private func makeStore() -> Store {
        MockProtocol.overrides = [:]
        MockProtocol.requests = []
        return Store(api: APIClient(base: "https://jobspy.example.com", key: "k", session: MockProtocol.session()))
    }

    @MainActor private func settle(_ store: Store) async throws {
        for _ in 0..<100 where store.inFlight > 0 { try await Task.sleep(for: .milliseconds(20)) }
    }

    @MainActor func testLoadAllAndFeedSections() async {
        let store = makeStore()
        await store.loadAll()
        XCTAssertNil(store.error)
        XCTAssertEqual(store.channels.count, 3)
        // Liked (8), disliked (9) and tracked applications (4, 7) are not "to review".
        let feed = Set(store.feed(channel: nil).map(\.job_url))
        XCTAssertEqual(feed, ["https://example.com/jobs/1", "https://example.com/jobs/2", "https://example.com/jobs/3", "https://example.com/jobs/5"])
        XCTAssertEqual(store.sections(channel: nil).map(\.decision), [.candidati, .valuta])
        XCTAssertEqual(store.saved.map(\.job_url), ["https://example.com/jobs/8"])
        XCTAssertEqual(store.applicationRows.filter { $0.app.isDue(today: "2026-11-26") }.count, 1)
        XCTAssertTrue(MockProtocol.requests.allSatisfy { $0.value(forHTTPHeaderField: "X-Api-Key") == "k" })
    }

    @MainActor func testBadKeyIsVisible() async {
        let store = makeStore()
        MockProtocol.overrides["GET /status"] = (401, Data(#"{"detail":"chiave API non valida"}"#.utf8))
        await store.loadAll()
        XCTAssertEqual(store.error?.kind, .badKey)
    }

    @MainActor func testVerdictRevertsWhenTheServerFails() async throws {
        let store = makeStore()
        await store.loadAll()
        let job = try XCTUnwrap(store.feed(channel: nil).first)
        MockProtocol.overrides["POST /feedback"] = (502, Data(#"{"detail":"giù"}"#.utf8))
        store.setVerdict(job, .dislike)
        XCTAssertEqual(store.verdict(job.job_url), .dislike) // optimistic
        XCTAssertNotNil(store.toast?.undo)
        try await settle(store)
        XCTAssertNil(store.verdict(job.job_url))
        XCTAssertEqual(store.toast?.isError, true)
    }

    @MainActor func testUndoPutsBackThePreviousVerdict() async throws {
        let store = makeStore()
        await store.loadAll()
        let job = try XCTUnwrap(store.saved.first)
        store.setVerdict(job, nil)
        store.toast?.undo?()
        XCTAssertEqual(store.verdict(job.job_url), .like)
        try await settle(store)
        let bodies = MockProtocol.requests.filter { $0.url?.path == "/mobile/feedback" }.compactMap { $0.httpBody }
        XCTAssertEqual(bodies.count, 2)
        XCTAssertTrue(bodies.contains { String(decoding: $0, as: UTF8.self).contains(#""verdict":null"#) })
    }

    @MainActor func testCvMatchFlowAndConflict() async {
        let store = makeStore()
        let m = CvMatchModel(api: store.api, jobURL: "https://example.com/jobs/1", cvId: 1)
        await m.load()
        XCTAssertEqual(m.match?.overall, 47)
        let missing = m.missing.map(\.term)
        XCTAssertFalse(missing.isEmpty)
        m.toggle(missing[0])
        XCTAssertEqual(m.attested, [missing[0]])
        let ok = await m.propose()
        XCTAssertTrue(ok)
        XCTAssertEqual(m.chosen, Set(m.proposal!.patches.indices))
        MockProtocol.overrides["POST /cvs/tailor"] = (409, Data(#"{"detail":"Il CV è cambiato: genera di nuovo la proposta"}"#.utf8))
        let saved = await m.save()
        XCTAssertFalse(saved)
        XCTAssertNil(m.proposal)
        XCTAssertEqual(m.error, "Il CV è cambiato: rigenera la proposta")
        m.toggle(missing[0])
        XCTAssertTrue(m.attested.isEmpty)
    }
}

extension URLRequest {
    /// URLProtocol sees POST bodies as a stream.
    nonisolated var httpBodyStreamData: Data? {
        guard let s = httpBodyStream else { return nil }
        s.open(); defer { s.close() }
        var data = Data(), buf = [UInt8](repeating: 0, count: 4096)
        while s.hasBytesAvailable { let n = s.read(&buf, maxLength: buf.count); if n <= 0 { break }; data.append(buf, count: n) }
        return data
    }
}
