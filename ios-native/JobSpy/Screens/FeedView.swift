import SwiftUI

/// I1 · Feed Lavoro: large title, channel chips, cards grouped by decision, swipe left = Scarta.
struct FeedView: View {
    @Environment(Store.self) private var store
    @State private var channel: Int?
    @State private var showLascia = false
    /// Screenshot launch argument -uiJob: open that detail right away.
    @State private var deepLink: String? = UIArgs.tab == 0 ? UIArgs.job : nil

    var body: some View {
        let sections = store.sections(channel: channel)
        let lascia = sections.first { $0.decision == .lascia }
        List {
            Section {
                StatusBanners()
                ChannelChips(selected: $channel)
            }
            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
            .listRowSeparator(.hidden)
            .listRowBackground(Color.clear)

            ForEach(sections.filter { $0.decision != .lascia || showLascia }, id: \.decision) { s in
                Section {
                    ForEach(s.jobs) { job in JobRow(job: job) }
                } header: {
                    SectionHeader(title: s.decision.section, count: s.jobs.count)
                }
            }
            if let lascia, !showLascia {
                Button("Mostra \(lascia.jobs.count) da lasciare") { showLascia = true }
                    .frame(maxWidth: .infinity, minHeight: 44)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay { LoadState(empty: sections.isEmpty, emptyIcon: "tray", emptyTitle: "Niente da decidere",
                             emptyText: channel == nil ? "Hai valutato tutte le offerte. Le nuove arrivano col prossimo aggiornamento dei canali." : "Nessuna offerta da valutare in questo canale.") }
        .navigationTitle("Offerte")
        .toolbar { AreaMenu() }
        .navigationDestination(for: String.self) { url in JobDetailView(url: url) }
        .refreshable { await store.loadAll(); if let channel { await store.loadChannel(channel) } }
        .task(id: channel) { if let channel, store.channelURLs[channel] == nil { await store.loadChannel(channel) } }
        .navigationDestination(item: $deepLink) { JobDetailView(url: $0) }
    }
}

struct SectionHeader: View {
    let title: String
    var count: Int?

    var body: some View {
        HStack(spacing: 8) {
            Text(title).font(.headline).foregroundStyle(Theme.foreground)
            if let count {
                Text("\(count)").font(.system(.caption, design: .monospaced).weight(.semibold))
                    .padding(.horizontal, 8).padding(.vertical, 2)
                    .background(Theme.muted, in: .capsule).foregroundStyle(Theme.mutedForeground)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
        .textCase(nil)
    }
}

/// A card in a List: tap opens the detail, swipe left = Scarta (open jobs) or the restore action.
struct JobRow: View {
    let job: Job
    @Environment(Store.self) private var store

    var body: some View {
        let state = store.state(job)
        // Hidden link: the card draws its own chevron, the List must not add a second one.
        JobCard(job: job)
            .background { NavigationLink(value: job.job_url) { EmptyView() }.opacity(0) }
            .accessibilityAction(named: state == .open ? "Scarta" : "Rimetti tra le offerte") {
                if state == .archived { Task { await store.restore(job) } } else { store.setVerdict(job, state == .open ? .dislike : nil) }
            }
            .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
            .listRowSeparator(.hidden)
            .listRowBackground(Color.clear)
            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                switch state {
                case .open:
                    Button(role: .destructive) { store.setVerdict(job, .dislike) } label: { Label("Scarta", systemImage: "xmark") }
                case .saved:
                    Button { store.setVerdict(job, nil) } label: { Label("Togli", systemImage: "bookmark.slash") }
                case .dismissed:
                    Button { store.setVerdict(job, nil) } label: { Label("Rimetti", systemImage: "arrow.uturn.backward") }.tint(Theme.primary)
                case .archived:
                    Button { Task { await store.restore(job) } } label: { Label("Rimetti", systemImage: "arrow.uturn.backward") }.tint(Theme.primary)
                }
            }
    }
}

/// Channel chips: «Tutti» plus each channel with its count; a failed refresh has a red border.
struct ChannelChips: View {
    @Binding var selected: Int?
    @Environment(Store.self) private var store

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                chip("Tutti", count: store.feed(channel: nil).count, active: selected == nil, failed: false) { selected = nil }
                ForEach(store.channels) { c in
                    chip(c.title, count: c.total_count, active: selected == c.id, failed: c.failed, busy: store.refreshing.contains(c.id)) {
                        selected = selected == c.id ? nil : c.id
                    }
                }
            }
            .padding(.vertical, 4)
        }
        .scrollClipDisabled()
    }

    private func chip(_ title: String, count: Int?, active: Bool, failed: Bool, busy: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if busy { ProgressView().controlSize(.mini) }
                if failed { Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(Theme.destructive).imageScale(.small) }
                Text(title).lineLimit(1)
                if let count { Text("\(count)").font(.system(.caption, design: .monospaced)).opacity(0.75) }
            }
            .font(.subheadline.weight(.medium))
            .padding(.horizontal, 14).frame(minHeight: 36)
            .foregroundStyle(active ? Theme.primaryForeground : Theme.foreground)
            .background(active ? Theme.primary : Theme.card, in: .capsule)
            .overlay { Capsule().stroke(failed ? Theme.destructive : active ? .clear : Theme.border, lineWidth: 1) }
            .contentShape(.capsule)
            .frame(minHeight: 44)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(active ? .isSelected : [])
        .accessibilityLabel(failed ? "\(title), ultimo aggiornamento non riuscito" : title)
        .accessibilityValue(count.map { "\($0) da valutare" } ?? "")
    }
}

/// /status: AI not configured (amber) or analyses in progress (grey with spinner).
struct StatusBanners: View {
    @Environment(Store.self) private var store

    var body: some View {
        if let s = store.status {
            if s.analyzer_configured == false {
                Banner(kind: .warning, text: "AI non configurata: le offerte nuove restano «Non noto» finché sul server manca la chiave DeepSeek.")
            } else if let n = s.analysis_pending, n > 0 {
                Banner(kind: s.analysis_running == true ? .info : .warning,
                       text: s.analysis_running == true ? "Analisi in corso: \(n) offerte in coda." : "\(n) offerte in attesa di analisi.")
            }
        }
    }
}

/// Loading, error (with the way out) and empty states over a list.
struct LoadState: View {
    var empty: Bool
    var emptyIcon = "tray"
    var emptyTitle = "Niente qui"
    var emptyText = ""
    @Environment(Store.self) private var store
    @State private var settings = false

    var body: some View {
        Group {
            if !store.loaded {
                ProgressView("Carico le offerte…")
            } else if let e = store.error {
                EmptyState(icon: e.kind == .badKey ? "key" : "wifi.exclamationmark",
                           title: e.kind == .badKey ? "Accesso non configurato" : "Non riesco a caricare",
                           text: e.message,
                           action: e.kind == .badKey ? ("Apri Impostazioni", { settings = true }) : ("Riprova", { Task { await store.loadAll() } }))
            } else if empty {
                EmptyState(icon: emptyIcon, title: emptyTitle, text: emptyText)
            }
        }
        .sheet(isPresented: $settings) { NavigationStack { SettingsView() } }
    }
}

/// Area switcher (Lavoro; PA and Gare later) plus Canali and Impostazioni.
struct AreaMenu: ToolbarContent {
    @State private var sheet: String? = UIArgs.screen

    var body: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Menu {
                Section("Area") {
                    Button {} label: { Label("Lavoro", systemImage: "checkmark") }
                    Button {} label: { Label("Concorsi PA · presto", systemImage: "building.columns") }.disabled(true)
                    Button {} label: { Label("Gare P.IVA · presto", systemImage: "doc.text.magnifyingglass") }.disabled(true)
                }
                Button { sheet = "channels" } label: { Label("Canali", systemImage: "dot.radiowaves.left.and.right") }
                Button { sheet = "settings" } label: { Label("Impostazioni", systemImage: "gearshape") }
            } label: {
                Label("Lavoro", systemImage: "briefcase.fill").labelStyle(.titleAndIcon).foregroundStyle(Theme.areaLavoro)
            }
            .accessibilityLabel("Area Lavoro, menu")
            .sheet(item: Binding(get: { sheet.map(SheetID.init) }, set: { sheet = $0?.id })) { s in
                NavigationStack { if s.id == "channels" { ChannelsView() } else { SettingsView() } }
            }
        }
    }

    struct SheetID: Identifiable { let id: String }
}
