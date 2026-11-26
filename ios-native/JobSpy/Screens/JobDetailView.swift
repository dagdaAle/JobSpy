import SwiftUI

/// I2 · Dettaglio offerta: tinted head, three mono numbers, «Valutazione | CV per questa offerta», action bar.
struct JobDetailView: View {
    let url: String
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    @State private var tab = UIArgs.detailTab == "cv" ? 1 : 0
    @State private var loading = true
    @State private var error: String?

    var body: some View {
        Group {
            if let job = store.job(url) {
                content(job)
            } else if loading {
                ProgressView("Carico l’offerta…")
            } else {
                EmptyState(icon: "exclamationmark.triangle", title: "Offerta non trovata", text: error ?? "",
                           action: ("Riprova", { Task { await load() } }))
            }
        }
        .background(Theme.background)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do { _ = try await store.detail(url); error = nil } catch {
            self.error = (error as? LocalizedError)?.errorDescription
            if store.job(url) != nil { store.fail(error) }
        }
    }

    @ViewBuilder
    private func content(_ job: Job) -> some View {
        let analysis = store.analysis(url)
        let decision = Decision(analysis)
        let state = store.state(job)
        let link = URL(string: job.job_url_direct ?? job.job_url).flatMap { ["http", "https"].contains($0.scheme) ? $0 : nil }
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                head(job, analysis, decision)
                VStack(alignment: .leading, spacing: 16) {
                    Picker("Sezione", selection: $tab) {
                        Text("Valutazione").tag(0)
                        Text("CV per questa offerta").tag(1)
                    }
                    .pickerStyle(.segmented)
                    if tab == 0 {
                        evaluation(job, analysis)
                    } else {
                        CvMatchView(job: job)
                    }
                }
                .padding(16)
            }
        }
        .toolbar {
            if let link {
                ToolbarItem(placement: .topBarTrailing) { ShareLink(item: link) { Image(systemName: "square.and.arrow.up") }.accessibilityLabel("Condividi") }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button { store.setVerdict(job, state == .saved ? nil : .like) } label: {
                    Image(systemName: state == .saved ? "bookmark.fill" : "bookmark")
                }
                .accessibilityLabel(state == .saved ? "Togli dai preferiti" : "Aggiungi ai preferiti")
            }
        }
        .safeAreaInset(edge: .bottom) { actions(job, state, link) }
    }

    private func head(_ job: Job, _ analysis: Analysis?, _ decision: Decision) -> some View {
        let dups = job.duplicates ?? 1
        let mode = JobText.workMode(job, analysis)
        return VStack(alignment: .leading, spacing: 10) {
            DecisionBadge(decision: decision, label: JobText.badgeLabel(decision, analysis))
            Text([job.company, job.location, mode].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.footnote).foregroundStyle(Theme.mutedForeground)
            Text(job.displayTitle).font(.title2.weight(.semibold)).foregroundStyle(Theme.foreground).accessibilityAddTraits(.isHeader)
            if let r = JobText.reason(analysis) { Text(r).font(.subheadline).foregroundStyle(Theme.foreground) }
            HStack(alignment: .top, spacing: 24) {
                number(JobText.salary(job, analysis), label: "RAL", unknown: "non indicata")
                number(analysis?.relevance_score.map { "\($0)%" }, label: "punteggio AI", unknown: "non calcolato")
                number(Fmt.ago(job.date_posted).nilIfEmpty, label: "su \(Fmt.site(job.site))\(dups > 1 ? " e altri \(dups - 1)" : "")", unknown: "data non nota")
            }
            .padding(.top, 4)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(decision.tint)
        .overlay(alignment: .bottom) { if decision.dashed { Rectangle().fill(Theme.unknownBorder).frame(height: 1) } }
    }

    private func number(_ value: String?, label: String, unknown: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let value { Text(value).font(.system(.title3, design: .monospaced).weight(.semibold)) }
            else { Text(unknown).font(.callout.italic()).foregroundStyle(Theme.unknownForeground) }
            Text(label).font(.caption).foregroundStyle(Theme.mutedForeground)
        }
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private func evaluation(_ job: Job, _ analysis: Analysis?) -> some View {
        Text("Perché · le componenti").sectionLabel()
        ForEach(Components.all(job, analysis)) { ComponentCard(component: $0) }

        let skills = Fmt.skills(job.skills)
        if !skills.isEmpty {
            Text("Competenze richieste").sectionLabel().padding(.top, 4)
            FlowLayout { ForEach(skills, id: \.self) { TagView(text: $0) } }
        }
        let extra = Components.extra(job, analysis)
        if !extra.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(extra, id: \.0) { k, v in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(k).font(.caption).foregroundStyle(Theme.mutedForeground)
                        Text(v).font(.subheadline)
                    }
                    .accessibilityElement(children: .combine)
                }
            }
            .panel()
        }
        if let src = job.source { SourceSection(source: src) }
        Text("Descrizione").sectionLabel().padding(.top, 4)
        if store.details[url] == nil && loading {
            ProgressView().frame(maxWidth: .infinity)
        } else {
            Text(job.description?.nilIfEmpty ?? "Nessuna descrizione disponibile per questo annuncio.")
                .font(.subheadline).foregroundStyle(Theme.mutedForeground).textSelection(.enabled)
        }
    }

    private func actions(_ job: Job, _ state: JobState, _ link: URL?) -> some View {
        HStack(spacing: 12) {
            switch state {
            case .open:
                Button { store.setVerdict(job, .dislike); dismiss() } label: { Label("Scarta", systemImage: "xmark").frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(.bordered)
            case .saved:
                Button { store.setVerdict(job, nil) } label: { Label("Togli dai preferiti", systemImage: "bookmark.slash").frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(.bordered)
            case .dismissed:
                Button { store.setVerdict(job, nil); dismiss() } label: { Label("Rimetti tra le offerte", systemImage: "arrow.uturn.backward").frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(.bordered)
            case .archived:
                Button { Task { await store.restore(job); dismiss() } } label: { Label("Rimetti nel feed", systemImage: "arrow.uturn.backward").frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(.bordered)
            }
            if store.application(job.job_url) == nil {
                Button { Task { await store.prepare(job) } } label: { Text("Prepara candidatura").frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground)
            } else if let link {
                Button { openURL(link) } label: { Label("Apri annuncio", systemImage: "arrow.up.right").frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground)
            }
        }
        .buttonBorderShape(.capsule)
        .padding(.horizontal, 16).padding(.vertical, 10)
        .background(.bar)
    }
}

/// One of the five components; unknown = dashed card with dashed bar and «dati insufficienti».
struct ComponentCard: View {
    let component: Component

    var body: some View {
        let c = component
        let color = c.tone?.color ?? (c.unknown ? Theme.unknownForeground : Theme.mutedForeground)
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label { Text(c.title).foregroundStyle(Theme.foreground) } icon: { Image(systemName: c.icon).foregroundStyle(c.tone == nil ? Theme.foreground : color) }
                    .font(.subheadline.weight(.semibold))
                Spacer()
                if let v = c.verdict { Text(v).font(.caption.weight(.semibold)).foregroundStyle(color) }
            }
            if c.unknown { MeterBar(value: nil) } else if let bar = c.bar { MeterBar(value: bar) }
            if let t = c.text, !t.isEmpty {
                Text(t).font(.footnote).foregroundStyle(c.unknown ? Theme.unknownForeground : Theme.mutedForeground)
            }
            if !c.tags.isEmpty {
                FlowLayout {
                    if let l = c.tagsLabel { Text(l).font(.footnote).foregroundStyle(Theme.mutedForeground) }
                    ForEach(c.tags, id: \.self) { TagView(text: $0) }
                }
            }
            ForEach(c.rows, id: \.key) { row in
                HStack {
                    Text(row.key).foregroundStyle(Theme.mutedForeground)
                    Spacer()
                    if let v = row.value {
                        Text(v).fontWeight(.medium).fontDesign(row.mono ? .monospaced : .default).multilineTextAlignment(.trailing)
                    } else {
                        Text("non indicato").italic().foregroundStyle(Theme.unknownForeground)
                    }
                }
                .font(.footnote)
                .accessibilityElement(children: .combine)
            }
        }
        .panel(dashed: c.unknown)
        .accessibilityElement(children: .combine)
    }
}

/// What freehire knows: closed/suspect state and requirements.
struct SourceSection: View {
    let source: JobSource

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Dalla fonte (freehire\(source.origin.map { " · \($0)" } ?? ""))").sectionLabel()
            FlowLayout {
                if source.closed_at != nil { InfoChip(text: "Chiusa alla fonte", fg: Theme.destructive, bg: Theme.destructiveSoft) }
                if source.suspect == true {
                    InfoChip(text: "Sospetta: \(source.reality?.fake_freshness == true ? "falsa nuova" : "ripubblicata \(source.reality?.mass_posting_count.map(String.init) ?? "più") volte")",
                             fg: Theme.valutaForeground, bg: Theme.valuta)
                }
            }
            ForEach(Array((source.requirements ?? []).enumerated()), id: \.offset) { _, r in
                Text("• \(r.text)\(r.priority == "preferred" ? " (preferito)" : "")").font(.subheadline)
            }
        }
    }
}

extension String {
    var nilIfEmpty: String? { isEmpty ? nil : self }
}
