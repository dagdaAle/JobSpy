import SwiftUI

/// I10 · Impostazioni (sheet from the avatar): server URL in mono, masked key with «Cambia» (Keychain),
/// «Verifica connessione» with a status row, theme, info.
struct SettingsView: View {
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @AppStorage("theme") private var theme = AppTheme.system
    @State private var url = Settings.url
    @State private var newKey = ""
    @State private var changingKey = Settings.key.isEmpty
    @State private var check: Check?
    @State private var serverVersion: String?
    @State private var testing = false

    enum Check { case ok(String), failed(String) }

    var body: some View {
        Form {
            Section("Server") {
                TextField("https://jobspy.example.com", text: $url)
                    .font(.body.monospaced())
                    .keyboardType(.URL).textContentType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                    .onSubmit { Settings.url = url; store.api = Settings.client }
                if changingKey {
                    SecureField("Chiave API", text: $newKey).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .onSubmit(saveKey)
                } else {
                    LabeledContent("Chiave API") {
                        HStack {
                            Text("••••••••").monospaced().foregroundStyle(Theme.mutedForeground).accessibilityLabel("salvata")
                            Button("Cambia") { changingKey = true }
                        }
                    }
                }
            }
            Section {
                Button { Task { await verify() } } label: {
                    HStack {
                        Text("Verifica connessione").foregroundStyle(Theme.areaLavoro)
                        Spacer()
                        if testing { ProgressView() }
                    }
                }
                .disabled(testing)
                switch check {
                case .ok(let s): Label(s, systemImage: "checkmark.circle.fill").foregroundStyle(Theme.candidatiForeground)
                case .failed(let s): Label(s, systemImage: "exclamationmark.triangle.fill").foregroundStyle(Theme.destructive)
                case nil: EmptyView()
                }
            } footer: {
                Text("La chiave è la MOBILE_API_KEY del server e resta nel Portachiavi del telefono, mai in chiaro.")
            }
            Section("Tema") {
                Picker("Tema", selection: $theme) { ForEach(AppTheme.allCases, id: \.self) { Text($0.rawValue).tag($0) } }
                    .pickerStyle(.segmented).labelsHidden()
            }
            Section("Info") {
                LabeledContent("Versione app") { Text(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "").monospaced() }
                LabeledContent("Versione server") { Text(serverVersion ?? "—").monospaced() }
                Link(destination: URL(string: "https://github.com/dagdaAle/JobSpy")!) {
                    HStack { Text("Codice sorgente"); Spacer(); Image(systemName: "arrow.up.right.square") }
                }
            }
        }
        .navigationTitle("Impostazioni")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Fine") { save(); dismiss() }.fontWeight(.semibold)
                    .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule)
            }
        }
        .task { if store.api.isConfigured { await verify() } }
    }

    private func saveKey() {
        guard !newKey.isEmpty else { return }
        Settings.key = newKey
        newKey = ""
        changingKey = false
        store.api = Settings.client
    }

    private func save() {
        Settings.url = url
        saveKey()
        store.api = Settings.client
        if store.error != nil { Task { await store.loadAll() } }
    }

    private func verify() async {
        #if !DEBUG
        guard url.lowercased().hasPrefix("https://") else { check = .failed("Serve un indirizzo https"); return }
        #endif
        save()
        testing = true
        defer { testing = false }
        let start = Date.now
        do {
            let s = try await store.api.status()
            let ms = Int(Date.now.timeIntervalSince(start) * 1000)
            serverVersion = try? await store.api.serverVersion()
            check = .ok(["Connesso", serverVersion.map { "v\($0)" }, "\(ms) ms", s.analyzer_configured == false ? "AI non configurata" : nil]
                .compactMap { $0 }.joined(separator: " · "))
            if store.error != nil { await store.loadAll() }
        } catch { check = .failed(CvMatchModel.text(error)) }
    }
}

/// I12 · Preferiti: large title, «Preferiti · N | Scartati · N | Archivio · N», feed cards.
struct SavedView: View {
    @Environment(Store.self) private var store
    @State private var view = UIArgs.saved

    var body: some View {
        let lists = [store.saved, store.dismissed, store.archive?.jobs ?? []]
        let jobs = lists[view]
        List {
            Picker("Vista", selection: $view) {
                Text("Preferiti · \(lists[0].count)").tag(0)
                Text("Scartati · \(lists[1].count)").tag(1)
                Text(store.archive == nil ? "Archivio" : "Archivio · \(lists[2].count)").tag(2)
            }
            .pickerStyle(.segmented)
            .listRowSeparator(.hidden).listRowBackground(Color.clear)
            ForEach(jobs) { JobRow(job: $0) }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay {
            if view == 2 && store.archive == nil && store.error == nil { ProgressView() }
            else { LoadState(empty: jobs.isEmpty, emptyIcon: ["bookmark", "xmark.bin", "archivebox"][view],
                             emptyTitle: ["Nessun preferito", "Nessuna offerta scartata", "Archivio vuoto"][view],
                             emptyText: ["Tocca il segnalibro su una card per metterla da parte.",
                                         "Le offerte scartate restano qui: scorri per rimetterle tra le offerte.",
                                         "Le offerte senza verdetto escono dal feed dopo \(store.feedDays) giorni e finiscono qui."][view]) }
        }
        .navigationTitle("Preferiti")
        .navigationDestination(for: String.self) { JobDetailView(url: $0) }
        .refreshable { await store.loadAll(); await store.loadArchive() }
        .task { if store.archive == nil { await store.loadArchive() } }
    }
}
