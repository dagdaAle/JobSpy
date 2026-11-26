import SwiftUI

/// Preferiti / Scartati / Archivio: the feed with another filter (no board of their own in Penpot).
struct SavedView: View {
    @Environment(Store.self) private var store
    @State private var view = UIArgs.saved

    var body: some View {
        let jobs = view == 0 ? store.saved : view == 1 ? store.dismissed : (store.archive?.jobs ?? [])
        List {
            Picker("Vista", selection: $view) {
                Text("Preferiti").tag(0)
                Text("Scartati").tag(1)
                Text("Archivio").tag(2)
            }
            .pickerStyle(.segmented)
            .listRowSeparator(.hidden).listRowBackground(Color.clear)
            Text(hint).font(.footnote).foregroundStyle(Theme.mutedForeground)
                .listRowSeparator(.hidden).listRowBackground(Color.clear)
            ForEach(jobs) { JobRow(job: $0) }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay {
            if view == 2 && store.archive == nil && store.error == nil { ProgressView() }
            else { LoadState(empty: jobs.isEmpty, emptyIcon: view == 0 ? "bookmark" : view == 1 ? "xmark.bin" : "archivebox",
                             emptyTitle: view == 0 ? "Nessun preferito" : view == 1 ? "Nessuna offerta scartata" : "Archivio vuoto",
                             emptyText: view == 0 ? "Tocca il segnalibro su una card per metterla da parte." : "") }
        }
        .navigationTitle(["Preferiti", "Scartate", "Archivio"][view])
        .navigationDestination(for: String.self) { JobDetailView(url: $0) }
        .refreshable { await store.loadAll(); if view == 2 { await store.loadArchive() } }
        .task(id: view) { if view == 2 && store.archive == nil { await store.loadArchive() } }
    }

    private var hint: String {
        switch view {
        case 0: "Le offerte che hai messo da parte. Restano qui anche dopo l’archiviazione automatica."
        case 1: "Le copie riconosciute dello stesso annuncio restano scartate. Scorri per rimetterle tra le offerte."
        default: "Offerte uscite dal feed. Scorri per rimetterle nel feed e valutarle di nuovo."
        }
    }
}

/// I6 · Candidature: grouped by status, amber follow-up warning on top.
struct ApplicationsView: View {
    @Environment(Store.self) private var store

    var body: some View {
        let rows = store.applicationRows
        let due = rows.filter { $0.app.isDue() }.count
        List {
            if due > 0 {
                Banner(kind: .warning, text: due == 1 ? "1 richiamo scaduto: è il momento di farti sentire." : "\(due) richiami scaduti: è il momento di farti sentire.")
                    .listRowSeparator(.hidden).listRowBackground(Color.clear)
            }
            ForEach(ApplicationGroups.order, id: \.title) { group in
                let items = rows.filter { group.statuses.contains($0.app.status) }
                    .sorted { ($0.app.follow_up_on ?? "9999") < ($1.app.follow_up_on ?? "9999") }
                if !items.isEmpty {
                    Section {
                        ForEach(items, id: \.job.job_url) { row in
                            NavigationLink(value: row.job.job_url) { ApplicationRow(job: row.job, app: row.app) }
                        }
                    } header: { SectionHeader(title: group.title, count: items.count) }
                }
            }
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay { LoadState(empty: rows.isEmpty, emptyIcon: "paperplane", emptyTitle: "Nessuna candidatura",
                             emptyText: "Dal dettaglio di un’offerta tocca «Prepara candidatura».") }
        .navigationTitle("Candidature")
        .navigationDestination(for: String.self) { JobDetailView(url: $0) }
        .refreshable { await store.loadAll() }
    }
}

struct ApplicationRow: View {
    let job: Job
    let app: Application

    var body: some View {
        let due = app.isDue()
        VStack(alignment: .leading, spacing: 4) {
            Text(job.displayTitle).font(.subheadline.weight(.semibold)).lineLimit(2)
            Text([job.company, job.location?.components(separatedBy: " · ").first].compactMap { $0?.nilIfEmpty }.joined(separator: " · "))
                .font(.footnote).foregroundStyle(Theme.mutedForeground).lineLimit(1)
            if !app.next_step.isEmpty { Text(app.next_step).font(.footnote) }
            HStack(spacing: 12) {
                if let a = app.applied_on { Label(Fmt.dayLabel(a), systemImage: "paperplane").accessibilityLabel("Inviata il \(Fmt.dayLabel(a))") }
                if let f = app.follow_up_on {
                    Label(Fmt.dayLabel(f), systemImage: due ? "exclamationmark.circle" : "calendar")
                        .foregroundStyle(due ? Theme.valutaForeground : Theme.mutedForeground)
                        .fontWeight(due ? .semibold : .regular)
                        .accessibilityLabel(due ? "Richiamo scaduto il \(Fmt.dayLabel(f))" : "Prossimo passo il \(Fmt.dayLabel(f))")
                }
            }
            .font(.caption).foregroundStyle(Theme.mutedForeground)
        }
        .padding(.vertical, 2)
        .accessibilityElement(children: .combine)
    }
}

/// CV tab: the library, read-only in v1 (editor and upload stay on the web).
struct CvListView: View {
    @Environment(Store.self) private var store

    var body: some View {
        let base = store.cvs.filter(\.isBase), tailored = store.cvs.filter { !$0.isBase }
        List {
            if !base.isEmpty { Section("CV base") { ForEach(base) { row($0) } } }
            if !tailored.isEmpty { Section("Adattati alle offerte") { ForEach(tailored) { row($0) } } }
            Section { Text("Modifica e caricamento dei CV restano nella web app.").font(.footnote).foregroundStyle(Theme.mutedForeground) }
        }
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay { LoadState(empty: store.cvs.isEmpty, emptyIcon: "doc.text", emptyTitle: "Nessun CV", emptyText: "Carica un CV dalla web app.") }
        .navigationTitle("CV")
        .navigationDestination(for: Int.self) { CvTextView(id: $0) }
        .refreshable { await store.reloadCvs() }
    }

    private func row(_ cv: CvSummary) -> some View {
        NavigationLink(value: cv.id) {
            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text(cv.name).font(.subheadline.weight(.medium)).lineLimit(2)
                    if cv.isDefault { Text("predefinito").font(.caption2.weight(.semibold)).padding(.horizontal, 6).padding(.vertical, 2).background(Theme.muted, in: .capsule) }
                }
                Text("Aggiornato \(Fmt.ago(cv.updated_at))\(cv.chars.map { " · \($0) caratteri" } ?? "")")
                    .font(.caption).foregroundStyle(Theme.mutedForeground)
            }
            .accessibilityElement(children: .combine)
        }
    }
}

struct CvTextView: View {
    let id: Int
    @Environment(Store.self) private var store
    @State private var cv: Cv?
    @State private var error: String?

    var body: some View {
        ScrollView {
            if let cv {
                Text(cv.markdown ?? "").font(.system(.footnote, design: .monospaced)).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(16)
            } else if let error {
                EmptyState(icon: "exclamationmark.triangle", title: "Non riesco a caricare il CV", text: error, action: ("Riprova", { Task { await load() } }))
            } else { ProgressView().padding(40) }
        }
        .background(Theme.background)
        .navigationTitle(cv?.name ?? "CV")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        do { cv = try await store.api.cv(id); error = nil } catch { self.error = CvMatchModel.text(error) }
    }
}

/// Channels: last refresh state and «Aggiorna» (scraping: long wait). Create/edit stay on the web in v1.
struct ChannelsView: View {
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List {
            ForEach(store.channels) { c in
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(c.title).font(.subheadline.weight(.semibold))
                        Text([Fmt.site(c.site), c.location?.nilIfEmpty, c.is_remote?.value == true ? "remoto" : nil].compactMap { $0 }.joined(separator: " · "))
                            .font(.caption).foregroundStyle(Theme.mutedForeground)
                        if c.failed {
                            Label("Ultimo aggiornamento non riuscito", systemImage: "exclamationmark.triangle").font(.caption).foregroundStyle(Theme.destructive)
                        } else if let at = c.last_refresh_at {
                            Text("Aggiornato \(Fmt.ago(at))").font(.caption).foregroundStyle(Theme.mutedForeground)
                        }
                    }
                    .accessibilityElement(children: .combine)
                    Spacer()
                    Text("\(c.total_count ?? 0)").font(.system(.subheadline, design: .monospaced).weight(.semibold))
                        .accessibilityLabel("\(c.total_count ?? 0) da valutare")
                    if store.refreshing.contains(c.id) {
                        ProgressView().frame(width: 44, height: 44).accessibilityLabel("Aggiornamento in corso")
                    } else {
                        Button { Task { await store.refresh(channel: c) } } label: {
                            Image(systemName: "arrow.clockwise").frame(width: 44, height: 44)
                        }
                        .buttonStyle(.borderless)
                        .accessibilityLabel("Aggiorna \(c.title)")
                    }
                }
            }
            Section {
                Text("L’aggiornamento cerca sulle fonti e può durare qualche minuto. Crea e modifica i canali dalla web app.")
                    .font(.footnote).foregroundStyle(Theme.mutedForeground)
            }
        }
        .overlay { LoadState(empty: store.channels.isEmpty, emptyIcon: "dot.radiowaves.left.and.right", emptyTitle: "Nessun canale", emptyText: "Crea un canale dalla web app.") }
        .navigationTitle("Canali")
        .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Fine") { dismiss() } } }
        .refreshable { await store.loadAll() }
    }
}

/// Search tab: title, company, place, skills and tags of the jobs already loaded.
struct SearchView: View {
    @Environment(Store.self) private var store
    @State private var text = UIArgs.search ?? ""

    var body: some View {
        let results = store.search(text)
        List { ForEach(results) { JobRow(job: $0) } }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .background(Theme.background)
            .overlay {
                if text.isEmpty { EmptyState(icon: "magnifyingglass", title: "Cerca tra le offerte", text: "Titolo, azienda, luogo o tag; anche preferiti, candidature e archivio.") }
                else if results.isEmpty { EmptyState(icon: "magnifyingglass", title: "Nessun risultato", text: "Nessuna offerta per «\(text)».") }
            }
            .navigationTitle("Cerca")
            .searchable(text: $text, prompt: "Titolo, azienda, luogo, tag")
            .navigationDestination(for: String.self) { JobDetailView(url: $0) }
            .task { if store.archive == nil { await store.loadArchive() } }
    }
}

/// Settings: server URL and key (Keychain), connection test.
struct SettingsView: View {
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var url = Settings.url
    @State private var key = Settings.key
    @State private var result: (ok: Bool, text: String)?
    @State private var testing = false

    var body: some View {
        Form {
            Section {
                TextField("https://jobspy.example.com", text: $url)
                    .keyboardType(.URL).textContentType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                SecureField("Chiave API", text: $key).textInputAutocapitalization(.never).autocorrectionDisabled()
            } header: { Text("Server") } footer: {
                Text("La chiave è la MOBILE_API_KEY del server e resta nel Portachiavi del telefono. Release: solo https.")
            }
            Section {
                Button { Task { await save() } } label: {
                    HStack { Text("Salva e prova"); Spacer(); if testing { ProgressView() } }
                }
                .disabled(testing)
                if let result {
                    Label(result.text, systemImage: result.ok ? "checkmark.circle" : "exclamationmark.triangle")
                        .foregroundStyle(result.ok ? Theme.candidatiForeground : Theme.destructive)
                }
            }
            Section("App") {
                LabeledContent("Versione", value: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "")
                LabeledContent("Area", value: "Lavoro (Concorsi PA e Gare in arrivo)")
            }
        }
        .navigationTitle("Impostazioni")
        .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Fine") { dismiss() } } }
    }

    private func save() async {
        #if !DEBUG
        guard url.lowercased().hasPrefix("https://") else { result = (false, "Serve un indirizzo https"); return }
        #endif
        testing = true
        defer { testing = false }
        Settings.url = url
        Settings.key = key
        store.api = Settings.client
        do {
            let s = try await store.api.status()
            result = (true, s.analyzer_configured == true ? "Connesso" : "Connesso · AI non configurata sul server")
            await store.loadAll()
        } catch { result = (false, CvMatchModel.text(error)) }
    }
}
