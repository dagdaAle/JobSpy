import SwiftUI

/// Pushes from the Feed stack.
enum FeedRoute: Hashable { case channels }

/// I1 · Feed Lavoro: large title, channel chips, cards grouped by decision, swipe left = Scarta.
/// States (I11a/b): no channels, AI and source banners, skeleton while loading.
struct FeedView: View {
    @Environment(Store.self) private var store
    @State private var channel: Int?
    @State private var showLascia = false
    @State private var newChannel = UIArgs.screen == "newChannel"
    /// Screenshot launch arguments: -uiJob opens that detail, -uiScreen channels the channel list.
    @State private var deepLink: String? = UIArgs.tab == 0 ? UIArgs.job : nil
    @State private var route: FeedRoute? = UIArgs.screen == "channels" ? .channels : nil

    var body: some View {
        let sections = store.sections(channel: channel)
        let lascia = sections.first { $0.decision == .lascia }
        let loading = !store.loaded || UIArgs.loading
        List {
            Section {
                if loading || store.refreshAllProgress != nil { LoadingSubtitle() }
                StatusBanners()
                if !store.channels.isEmpty || loading { ChannelChips(selected: $channel) }
            }
            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
            .listRowSeparator(.hidden)
            .listRowBackground(Color.clear)

            if loading {
                ForEach(0..<3, id: \.self) { _ in SkeletonCard() }
                    .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                    .listRowSeparator(.hidden).listRowBackground(Color.clear)
            } else {
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
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay {
            if !loading && store.error == nil && store.channels.isEmpty {
                NoChannels { newChannel = true }
            } else if !loading {
                LoadState(empty: sections.isEmpty, emptyIcon: "tray", emptyTitle: "Niente da decidere",
                          emptyText: channel == nil ? "Hai valutato tutte le offerte. Le nuove arrivano col prossimo aggiornamento dei canali." : "Nessuna offerta da valutare in questo canale.")
            }
        }
        .navigationTitle("Offerte")
        .toolbar { AreaMenu(); AvatarButton() }
        .navigationDestination(for: String.self) { url in JobDetailView(url: url) }
        .navigationDestination(for: FeedRoute.self) { _ in ChannelsView() }
        .navigationDestination(item: $route) { _ in ChannelsView() }
        .navigationDestination(item: $deepLink) { JobDetailView(url: $0) }
        .refreshable { await store.loadAll(); if let channel { await store.loadChannel(channel) } }
        .task(id: channel) { if let channel, store.channelURLs[channel] == nil { await store.loadChannel(channel) } }
        .sheet(isPresented: $newChannel) { NavigationStack { ChannelFormView(channel: nil) } }
    }
}

/// I11b: «Aggiornamento in corso · 2 canali su 3» under the title, no full-screen spinner.
struct LoadingSubtitle: View {
    @Environment(Store.self) private var store
    var body: some View {
        HStack(spacing: 8) {
            ProgressView().controlSize(.small)
            if let p = store.refreshAllProgress {
                Text("Aggiornamento in corso · \(p.done + 1 > p.total ? p.total : p.done + 1) canali su \(p.total)")
            } else if UIArgs.loading {
                Text("Aggiornamento in corso · 2 canali su 3")
            } else {
                Text("Carico le offerte…")
            }
        }
        .font(.subheadline).foregroundStyle(Theme.mutedForeground)
        .accessibilityElement(children: .combine)
    }
}

/// Skeleton card: muted panel with border-coloured bars.
struct SkeletonCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 10) {
                bar(120, 22); bar(90, 22); bar(140, 12); bar(220, 18); bar(260, 12); bar(200, 12)
            }
            .padding(14).frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.muted, in: .rect(cornerRadius: 14))
            HStack { bar(90, 16); Spacer() }.padding(.horizontal, 8).padding(.bottom, 6)
        }
        .padding(6)
        .background(Theme.card, in: .rect(cornerRadius: 20))
        .overlay { RoundedRectangle(cornerRadius: 20).stroke(Theme.border) }
        .accessibilityHidden(true)
    }
    private func bar(_ w: CGFloat, _ h: CGFloat) -> some View {
        Capsule().fill(Theme.border).frame(width: w, height: h)
    }
}

/// I11a: feed without channels.
struct NoChannels: View {
    let create: () -> Void
    @State private var help = false

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "dot.radiowaves.left.and.right").font(.system(size: 34, weight: .medium))
                .foregroundStyle(Theme.areaLavoro)
                .frame(width: 88, height: 88).background(Theme.areaLavoroSoft, in: .circle)
                .accessibilityHidden(true)
            Text("Nessun canale").font(.title3.weight(.semibold)).accessibilityAddTraits(.isHeader)
            Text("Un canale è una ricerca salvata: JobSpy la ripete ogni mattina e ti porta qui le offerte nuove.")
                .font(.subheadline).foregroundStyle(Theme.mutedForeground).multilineTextAlignment(.center)
            Button(action: create) { Label("Nuovo canale", systemImage: "plus").frame(minHeight: 44).padding(.horizontal, 8) }
                .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule)
            Button("Come funziona un canale") { help = true }.font(.subheadline).frame(minHeight: 44)
        }
        .padding(32)
        .alert("Come funziona un canale", isPresented: $help) {
            Button("Ho capito", role: .cancel) {}
        } message: {
            Text("Scegli le fonti, cosa cercare e dove. Alle 9 JobSpy cerca su ogni fonte, toglie i doppioni e fa valutare le offerte nuove all'AI. Le trovi nel Feed, divise per decisione.")
        }
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
                NavigationLink(value: FeedRoute.channels) {
                    Image(systemName: "slider.horizontal.3").font(.subheadline.weight(.semibold))
                        .foregroundStyle(Theme.foreground)
                        .frame(width: 44, height: 36).background(Theme.card, in: .capsule)
                        .overlay { Capsule().stroke(Theme.border) }
                        .frame(minHeight: 44)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Canali")
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

/// I11b banners: AI not configured (amber, to Settings) and failed sources (red, «Riprova»).
struct StatusBanners: View {
    @Environment(Store.self) private var store
    @State private var settings = false

    var body: some View {
        if let s = store.status {
            if s.analyzer_configured == false {
                Button { settings = true } label: {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: "sparkles")
                        VStack(alignment: .leading, spacing: 2) {
                            Text("AI non configurata").fontWeight(.semibold)
                            Text("Le offerte nuove restano «Non noto» finché sul server manca la chiave DeepSeek.").font(.footnote)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        Image(systemName: "chevron.right").font(.footnote.weight(.semibold))
                    }
                    .font(.subheadline).multilineTextAlignment(.leading)
                    .padding(.horizontal, 14).padding(.vertical, 10)
                    .foregroundStyle(Theme.deadlineSoonForeground)
                    .background(Theme.deadlineSoon, in: .rect(cornerRadius: 14))
                }
                .buttonStyle(.plain)
                .accessibilityHint("Apre le Impostazioni")
                .sheet(isPresented: $settings) { NavigationStack { SettingsView() } }
            } else if let n = s.analysis_pending, n > 0, s.analysis_running == true {
                Banner(kind: .info, text: "Analisi in corso: \(n) offerte in coda.")
            }
        }
        let failed = store.failedChannels
        if !failed.isEmpty {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "exclamationmark.triangle")
                VStack(alignment: .leading, spacing: 2) {
                    Text(failed.count == 1 ? "Errore della fonte · \(failed[0].title)" : "\(failed.count) canali non aggiornati").fontWeight(.semibold)
                    Text(failed.count == 1 ? (store.channelErrors[failed[0].id] ?? "Ultimo aggiornamento non riuscito") : failed.map(\.title).joined(separator: ", "))
                        .font(.footnote).foregroundStyle(Theme.foreground)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Button("Riprova") { Task { await store.refreshAll(failed) } }
                    .font(.subheadline.weight(.semibold)).frame(minHeight: 44)
                    .disabled(store.refreshAllProgress != nil)
            }
            .font(.subheadline).foregroundStyle(Theme.destructive)
            .padding(.horizontal, 14).padding(.vertical, 10)
            .background(Theme.destructiveSoft, in: .rect(cornerRadius: 14))
            .overlay { RoundedRectangle(cornerRadius: 14).stroke(Theme.destructive) }
            .accessibilityElement(children: .contain)
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

/// Area switcher (Lavoro; PA and Gare later), shown with its name like I1.
struct AreaMenu: ToolbarContent {
    var body: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Menu {
                Section("Area") {
                    Button {} label: { Label("Lavoro", systemImage: "checkmark") }
                    Button {} label: { Label("Concorsi PA · presto", systemImage: "building.columns") }.disabled(true)
                    Button {} label: { Label("Gare P.IVA · presto", systemImage: "doc.text.magnifyingglass") }.disabled(true)
                }
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "briefcase.fill").foregroundStyle(Theme.areaLavoro)
                    Text("Lavoro").fontWeight(.semibold).foregroundStyle(Theme.foreground)
                    Image(systemName: "chevron.down").font(.caption.weight(.bold)).foregroundStyle(Theme.mutedForeground)
                }
                .padding(.horizontal, 6)
                .fixedSize()
            }
            .accessibilityLabel("Area Lavoro, cambia area")
        }
    }
}

/// Avatar in the area colour: opens Settings as a sheet (I10).
struct AvatarButton: ToolbarContent {
    @State private var open = UIArgs.screen == "settings"

    var body: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button { open = true } label: {
                Image(systemName: "person.fill").font(.footnote).foregroundStyle(Theme.background)
                    .frame(width: 32, height: 32).background(Theme.areaLavoro, in: .circle)
            }
            .accessibilityLabel("Impostazioni")
            .sheet(isPresented: $open) { NavigationStack { SettingsView() } }
        }
    }
}
