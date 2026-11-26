import Foundation
import Observation
import UIKit

/// Shared state: the job lists with their analysis/feedback/application maps (keyed by job_url),
/// channels, CVs and the backend status. The views derive feed, sections and states from here.
@Observable
final class Store {
    var api: APIClient
    var status: Status?
    var channels: [Channel] = []
    var active = JobsEnvelope()
    var archive: JobsEnvelope?
    var tracked = JobsEnvelope()
    var channelURLs: [Int: Set<String>] = [:]
    var details: [String: JobDetail] = [:]
    var cvs: [CvSummary] = []
    var loaded = false
    var loading = false
    var error: APIError?
    var refreshing: Set<Int> = []
    /// «Aggiornamento in corso · done canali su total» while refreshing every channel.
    var refreshAllProgress: (done: Int, total: Int)?
    /// Reason of the last failed refresh per channel (from /logs).
    var channelErrors: [Int: String] = [:]
    var sites: [String] = []
    var toast: Toast?
    /// Requests still running: the toast stays up until they end.
    var inFlight = 0
    private var lastLoad: Date?

    struct Toast: Identifiable {
        let id = UUID()
        let text: String
        var isError = false
        var undo: (() -> Void)?
    }

    init(api: APIClient = Settings.client) { self.api = api }

    func show(_ text: String, error: Bool = false, undo: (() -> Void)? = nil) {
        toast = Toast(text: text, isError: error, undo: undo)
        UIAccessibility.post(notification: .announcement, argument: text)
    }

    func fail(_ error: Error) { show((error as? LocalizedError)?.errorDescription ?? error.localizedDescription, error: true) }

    // MARK: loading

    func loadAll() async {
        guard api.isConfigured else { error = .noSettings; loaded = true; return }
        loading = true
        defer { loading = false; loaded = true; lastLoad = .now }
        do {
            async let s = api.status()
            async let c = api.channels()
            async let j = api.jobs()
            async let t = api.applications()
            async let v = api.cvs()
            (status, channels, active, tracked, cvs) = try await (s, c, j, t, v)
            error = nil
            await loadChannelErrors()
            channelURLs = [:]
            if archive != nil { await loadArchive() }
        } catch {
            self.error = error as? APIError ?? APIError(kind: .other, message: error.localizedDescription)
        }
    }

    /// Back in the foreground: reload if the data is older than a minute.
    func reloadIfStale() async {
        guard let lastLoad, Date.now.timeIntervalSince(lastLoad) > 60, !loading else { return }
        await loadAll()
    }

    func loadArchive() async {
        do { archive = try await api.jobs(archived: true) } catch { fail(error) }
    }

    func loadStatus() async { if let s = try? await api.status() { status = s } }

    func loadChannel(_ id: Int) async {
        do {
            let env = try await api.channelJobs(id)
            channelURLs[id] = Set(env.jobs.map(\.job_url))
            active.analysis.merge(env.analysis) { _, new in new }
        } catch { fail(error) }
    }

    func detail(_ url: String) async throws -> JobDetail {
        let d = try await api.job(url)
        details[url] = d
        return d
    }

    // MARK: lookups

    func analysis(_ url: String) -> Analysis? {
        details[url]?.analysis ?? active.analysis[url] ?? tracked.analysis[url] ?? archive?.analysis[url]
    }

    func verdict(_ url: String) -> Verdict? { active.feedback[url] ?? tracked.feedback[url] ?? archive?.feedback[url] }

    func application(_ url: String) -> Application? { tracked.applications[url] ?? active.applications[url] }

    func job(_ url: String) -> Job? {
        let base = active.jobs.first { $0.job_url == url } ?? tracked.jobs.first { $0.job_url == url } ?? archive?.jobs.first { $0.job_url == url }
        guard let detail = details[url]?.job else { return base }
        return base.map { $0.merged(with: detail) } ?? detail
    }

    func state(_ job: Job) -> JobState {
        switch verdict(job.job_url) {
        case .like: return .saved
        case .dislike: return .dismissed
        case nil: return job.archived_at != nil ? .archived : .open
        }
    }

    var feedDays: Int { status?.feed_days ?? 7 }

    /// Still to review: no verdict, not tracked as an application, optionally in one channel.
    func feed(channel: Int?) -> [Job] {
        active.jobs.filter { j in
            guard active.feedback[j.job_url] == nil, active.applications[j.job_url] == nil else { return false }
            if let channel { return channelURLs[channel]?.contains(j.job_url) ?? false }
            return true
        }
    }

    /// Feed grouped by decision, in the web app's order (Lascia last).
    func sections(channel: Int?) -> [(decision: Decision, jobs: [Job])] {
        let jobs = feed(channel: channel)
        return [Decision.candidati, .valuta, .nonnoto, .lascia].compactMap { d in
            let list = jobs.filter { Decision(analysis($0.job_url)) == d }
            return list.isEmpty ? nil : (d, list)
        }
    }

    var saved: [Job] { active.jobs.filter { active.feedback[$0.job_url] == .like } }
    var dismissed: [Job] { active.jobs.filter { active.feedback[$0.job_url] == .dislike } }

    var applicationRows: [(job: Job, app: Application)] {
        tracked.jobs.compactMap { j in
            let app = tracked.applications[j.job_url] ?? j.duplicate_urls?.lazy.compactMap { self.tracked.applications[$0] }.first
            return app.map { (j, $0) }
        }
    }

    func search(_ text: String) -> [Job] {
        let q = text.trimmingCharacters(in: .whitespaces).lowercased()
        guard !q.isEmpty else { return [] }
        var seen = Set<String>()
        return (active.jobs + tracked.jobs + (archive?.jobs ?? [])).filter { j in
            guard seen.insert(j.job_url).inserted else { return false }
            let hay = [j.title, j.company, j.location, j.skills].compactMap { $0 } + (analysis(j.job_url)?.tags ?? [])
            return hay.contains { $0.lowercased().contains(q) }
        }
    }

    // MARK: actions

    /// Preferito / scarta / togli il verdetto, with «Annulla» that puts back the previous one.
    func setVerdict(_ job: Job, _ v: Verdict?, undoable: Bool = true) {
        let before = verdict(job.job_url)
        apply(job.job_url, v)
        inFlight += 1
        Task {
            defer { inFlight -= 1 }
            do {
                try await api.feedback(job, v)
                if let c = try? await api.channels() { channels = c }
            } catch {
                apply(job.job_url, before)
                show("Salvataggio non riuscito: \((error as? LocalizedError)?.errorDescription ?? "")", error: true)
            }
        }
        guard undoable else { return }
        let text = v == .like ? "Aggiunta ai preferiti" : v == .dislike ? "Offerta scartata" : before == .like ? "Tolta dai preferiti" : "Rimessa tra le offerte"
        show(text) { [weak self] in self?.setVerdict(job, before, undoable: false) }
    }

    private func apply(_ url: String, _ v: Verdict?) {
        active.feedback[url] = v
        if tracked.feedback[url] != nil || v != nil { tracked.feedback[url] = v }
        archive?.feedback[url] = v
    }

    /// Archivio: back to the feed (server restores the copies too).
    func restore(_ job: Job) async {
        do {
            try await api.restore(job.job_url)
            show("Offerta rimessa nel feed")
            await loadAll()
        } catch { fail(error) }
    }

    /// «Prepara candidatura»: tracked as «Da candidare», like the web app's application editor.
    func prepare(_ job: Job) async {
        if let app = application(job.job_url) {
            show("Già tra le candidature: \(app.status.label)")
            return
        }
        do {
            try await api.save(Application(job_url: job.job_url, status: .to_apply))
            tracked = try await api.applications()
            active.applications = tracked.applications
            show("Aggiunta alle candidature")
        } catch { fail(error) }
    }

    func refresh(channel: Channel) async {
        refreshing.insert(channel.id)
        defer { refreshing.remove(channel.id) }
        do {
            try await api.refresh(channel: channel.id)
            show("«\(channel.title)» aggiornato")
            await loadAll()
        } catch {
            fail(error)
            if let c = try? await api.channels() { channels = c }
        }
    }

    func loadChannelErrors() async {
        guard channels.contains(where: \.failed), let logs = try? await api.logs() else { channelErrors = [:]; return }
        var out: [Int: String] = [:]
        for l in logs where l.kind == "refresh" { // newest first: keep the latest per channel
            guard let id = l.channel_id, out[id] == nil, channels.first(where: { $0.id == id })?.failed == true else { continue }
            out[id] = l.error ?? "Errore della fonte"
        }
        channelErrors = out
    }

    var failedChannels: [Channel] { channels.filter(\.failed) }

    /// Pull-to-refresh on Canali: one channel at a time (the server serializes scraping anyway).
    func refreshAll(_ list: [Channel]? = nil) async {
        let list = list ?? channels
        guard !list.isEmpty, refreshAllProgress == nil else { return }
        refreshAllProgress = (0, list.count)
        var failed = 0
        for c in list {
            refreshing.insert(c.id)
            do { try await api.refresh(channel: c.id) } catch { failed += 1 }
            refreshing.remove(c.id)
            refreshAllProgress?.done += 1
        }
        refreshAllProgress = nil
        await loadAll()
        show(failed == 0 ? "Canali aggiornati" : "\(failed) canali non aggiornati: vedi il motivo nella card", error: failed > 0)
    }

    func loadSites() async {
        guard sites.isEmpty else { return }
        sites = (try? await api.sites()) ?? Fmt.siteLabels.keys.sorted()
    }

    /// One channel per selected source (a backend channel has a single site).
    func createChannels(_ body: ChannelBody, sites: [String]) async -> Bool {
        var found = 0
        for site in sites {
            var b = body
            b.site = site
            if sites.count > 1 && !b.name.isEmpty { b.name += " · \(Fmt.site(site))" }
            do { found += try await api.createChannel(b).new_count ?? 0 } catch {
                fail(error)
                await loadAll()
                return false
            }
        }
        show(sites.count == 1 ? "Canale creato: \(found) offerte trovate" : "\(sites.count) canali creati: \(found) offerte trovate")
        await loadAll()
        return true
    }

    func updateChannel(_ id: Int, _ body: ChannelBody) async -> Bool {
        do {
            try await api.updateChannel(id, body)
            show("Canale aggiornato: i filtri valgono dal prossimo aggiornamento")
            channels = try await api.channels()
            return true
        } catch { fail(error); return false }
    }

    func deleteChannel(_ c: Channel) async {
        do {
            try await api.deleteChannel(c.id)
            channels.removeAll { $0.id == c.id }
            show("Canale «\(c.title)» eliminato")
            await loadAll()
        } catch { fail(error) }
    }

    func setDefault(_ cv: CvSummary) async {
        do { try await api.setDefault(cv: cv.id); show("«\(cv.name)» è il CV predefinito"); await reloadCvs() } catch { fail(error) }
    }

    func deleteCv(_ cv: CvSummary) async {
        do { try await api.deleteCv(cv.id); show("CV eliminato"); await reloadCvs() } catch { fail(error) }
    }

    func upload(_ url: URL) async {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        do {
            let data = try Data(contentsOf: url)
            guard data.count <= 5 * 1024 * 1024 else { show("PDF troppo grande (max 5 MB)", error: true); return }
            _ = try await api.upload(pdf: data, name: url.deletingPathExtension().lastPathComponent)
            show("CV caricato: il testo è diventato Markdown")
            await reloadCvs()
        } catch { fail(error) }
    }

    func reloadCvs() async {
        do { cvs = try await api.cvs() } catch { fail(error) }
    }
}
