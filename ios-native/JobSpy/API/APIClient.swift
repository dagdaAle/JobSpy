import Foundation

nonisolated struct APIError: LocalizedError, Equatable, Sendable {
    enum Kind: Sendable { case badKey, notConfigured, conflict, upstream, notFound, invalid, network, other }
    let kind: Kind
    let message: String
    var status: Int = 0
    var errorDescription: String? { message }

    static let noSettings = APIError(kind: .badKey, message: "Imposta URL del server e chiave nelle Impostazioni")
}

/// Client of the mobile API: `<URL>/mobile/<route>` with the `X-Api-Key` header (docs/mobile-api.md).
nonisolated struct APIClient: Sendable {
    var base: String
    var key: String
    var session: URLSession = APIClient.defaultSession

    /// LLM and scraping calls can take minutes; everything else should answer quickly.
    static let shortTimeout: TimeInterval = 30
    static let longTimeout: TimeInterval = 300

    static let defaultSession: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = longTimeout
        config.timeoutIntervalForResource = longTimeout * 2
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: config)
    }()

    static let decoder = JSONDecoder()
    static let encoder = JSONEncoder()

    var isConfigured: Bool { !base.trimmingCharacters(in: .whitespaces).isEmpty && !key.isEmpty }

    /// job_url goes in the query string: encode everything that is not unreserved (":", "/", "?", "&", "=", "+").
    static func q(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")) ?? value
    }

    func request(_ path: String, method: String = "GET", body: (any Encodable)? = nil, long: Bool = false) throws -> URLRequest {
        guard isConfigured else { throw APIError.noSettings }
        var trimmed = base.trimmingCharacters(in: .whitespaces)
        while trimmed.hasSuffix("/") { trimmed.removeLast() }
        guard let url = URL(string: "\(trimmed)/mobile\(path)"), url.scheme == "https" || url.scheme == "http" else {
            throw APIError(kind: .invalid, message: "URL del server non valido")
        }
        var req = URLRequest(url: url, timeoutInterval: long ? Self.longTimeout : Self.shortTimeout)
        req.httpMethod = method
        req.setValue(key, forHTTPHeaderField: "X-Api-Key")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try Self.encoder.encode(body)
        }
        return req
    }

    private struct ErrorBody: Decodable {
        let detail: Detail?
        enum Detail: Decodable {
            case text(String), list([Item])
            struct Item: Decodable { let msg: String? }
            init(from decoder: Decoder) throws {
                let c = try decoder.singleValueContainer()
                if let s = try? c.decode(String.self) { self = .text(s) } else { self = .list(try c.decode([Item].self)) }
            }
            var message: String {
                switch self {
                case .text(let s): s
                case .list(let items): items.compactMap(\.msg).joined(separator: "; ")
                }
            }
        }
    }

    /// Maps the HTTP status to what the user can do about it (401 key, 409 reload, 502 source, 503 not configured).
    static func error(status: Int, data: Data) -> APIError {
        let detail = (try? decoder.decode(ErrorBody.self, from: data))?.detail?.message
        switch status {
        case 401: return APIError(kind: .badKey, message: "Chiave API non valida: controllala nelle Impostazioni", status: status)
        case 404: return APIError(kind: .notFound, message: detail ?? "Non trovato", status: status)
        case 409: return APIError(kind: .conflict, message: detail ?? "Dati cambiati sul server: ricarica", status: status)
        case 422: return APIError(kind: .invalid, message: detail ?? "Dati non validi", status: status)
        case 502: return APIError(kind: .upstream, message: detail ?? "Fonte o modello non raggiungibile: riprova", status: status)
        case 503: return APIError(kind: .notConfigured, message: detail ?? "Servizio non configurato sul server", status: status)
        default: return APIError(kind: .other, message: detail ?? "Errore del server (\(status))", status: status)
        }
    }

    func send(_ path: String, method: String = "GET", body: (any Encodable)? = nil, long: Bool = false) async throws -> Data {
        let req = try request(path, method: method, body: body, long: long)
        let data: Data, res: URLResponse
        do {
            (data, res) = try await session.data(for: req)
        } catch let e as URLError where e.code == .timedOut {
            throw APIError(kind: .network, message: "Il server non ha risposto in tempo")
        } catch let e as URLError where e.code != .cancelled {
            throw APIError(kind: .network, message: "Server non raggiungibile: \(e.localizedDescription)")
        }
        let status = (res as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else { throw Self.error(status: status, data: data) }
        return data
    }

    func get<T: Decodable>(_ path: String, method: String = "GET", body: (any Encodable)? = nil, long: Bool = false) async throws -> T {
        let data = try await send(path, method: method, body: body, long: long)
        do { return try Self.decoder.decode(T.self, from: data) } catch {
            throw APIError(kind: .other, message: "Risposta del server non leggibile")
        }
    }

    // stato e canali
    func status() async throws -> Status { try await get("/status") }
    func channels() async throws -> [Channel] { try await (get("/channels") as ChannelsResponse).channels }
    func refresh(channel id: Int) async throws { _ = try await send("/channels/\(id)/refresh", method: "POST", long: true) }
    func sites() async throws -> [String] { try await (get("/channels") as ChannelsResponse).sites ?? [] }
    /// Creating a channel runs its first scraping: long timeout.
    func createChannel(_ b: ChannelBody) async throws -> ChannelCreated { try await get("/channels", method: "POST", body: b, long: true) }
    func updateChannel(_ id: Int, _ b: ChannelBody) async throws { _ = try await send("/channels/\(id)", method: "PUT", body: b) }
    func deleteChannel(_ id: Int) async throws { _ = try await send("/channels/\(id)", method: "DELETE") }
    func logs(limit: Int = 100) async throws -> [LogEntry] {
        struct R: Decodable { let logs: [LogEntry] }
        return try await (get("/logs?limit=\(limit)") as R).logs
    }
    func freehireCompanies(_ q: String) async throws -> [FreehireCompany] {
        struct R: Decodable { let companies: [FreehireCompany] }
        return try await (get("/freehire/companies?q=\(Self.q(q))") as R).companies
    }

    // offerte
    func jobs(archived: Bool = false) async throws -> JobsEnvelope { try await get("/jobs?archived=\(archived)") }
    func channelJobs(_ id: Int) async throws -> JobsEnvelope { try await get("/channels/\(id)/jobs") }
    func job(_ url: String) async throws -> JobDetail { try await get("/job?url=\(Self.q(url))") }
    func feedback(_ job: Job, _ verdict: Verdict?) async throws {
        let body = FeedbackBody(job_url: job.job_url, verdict: verdict, title: job.title ?? "", company: job.company ?? "", site: job.site ?? "")
        _ = try await send("/feedback", method: "POST", body: body)
    }
    func restore(_ url: String) async throws { _ = try await send("/jobs/restore?url=\(Self.q(url))", method: "POST") }

    // candidature
    func applications() async throws -> JobsEnvelope { try await get("/applications") }
    func save(_ application: Application) async throws { _ = try await send("/applications", method: "POST", body: application) }

    // CV
    func cvs() async throws -> [CvSummary] { try await (get("/cvs") as CvsResponse).cvs }
    func cv(_ id: Int) async throws -> Cv { try await (get("/cvs/\(id)") as CvResponse).cv }
    func pages(cv id: Int) async throws -> Int {
        struct R: Decodable { let pages: Int }
        return try await (get("/cvs/\(id)/preview") as R).pages
    }
    func setDefault(cv id: Int) async throws { _ = try await send("/cvs/\(id)/default", method: "POST") }
    func deleteCv(_ id: Int) async throws { _ = try await send("/cvs/\(id)", method: "DELETE") }
    func updateCv(_ id: Int, markdown: String) async throws {
        _ = try await send("/cvs/\(id)", method: "PATCH", body: ["markdown": markdown])
    }
    /// Raw PDF body; the server extracts the text and stores it as Markdown.
    func upload(pdf: Data, name: String) async throws -> Int {
        var req = try request("/cvs/upload?name=\(Self.q(name))", method: "POST", long: true)
        req.setValue("application/pdf", forHTTPHeaderField: "Content-Type")
        req.httpBody = pdf
        let (data, res) = try await session.data(for: req)
        let status = (res as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else { throw Self.error(status: status, data: data) }
        struct R: Decodable { let id: Int }
        return try Self.decoder.decode(R.self, from: data).id
    }
    func review(cv id: Int) async throws -> CvReview {
        try await get("/cvs/\(id)/review", method: "POST", body: ["confirmed_facts": ""], long: true)
    }
    func revise(cv id: Int, _ body: RevisionBody) async throws -> Cv {
        try await (get("/cvs/\(id)/revision", method: "POST", body: body) as CvResponse).cv
    }
    /// Server version from the OpenAPI schema (info.version).
    func serverVersion() async throws -> String {
        struct R: Decodable { struct Info: Decodable { let version: String? }; let info: Info? }
        return try await (get("/openapi.json") as R).info?.version ?? "?"
    }
    func match(cv id: Int, job url: String, refresh: Bool = false) async throws -> MatchReport {
        try await get("/cvs/\(id)/match?job_url=\(Self.q(url))\(refresh ? "&refresh=1" : "")", long: true)
    }
    func proposal(cv id: Int, job url: String, attested: [String]) async throws -> TailorProposal {
        try await get("/cvs/\(id)/tailor-proposal", method: "POST", body: ProposalBody(job_url: url, attested: attested), long: true)
    }
    func tailor(_ body: TailorBody) async throws -> TailorResult {
        try await get("/cvs/tailor", method: "POST", body: body, long: true)
    }
}
