import Observation
import SwiftUI

/// State of «CV per questa offerta» (port of CvMatchPanel.tsx); contract in specs/004-cv-match/contract.md.
@Observable
final class CvMatchModel {
    enum Busy { case loading, refresh, propose, save }
    let api: APIClient
    let jobURL: String
    var cvId: Int
    var match: MatchReport?
    var attested: [String] = []
    var proposal: TailorProposal?
    var chosen: Set<Int> = []
    var busy: Busy?
    var error: String?
    var saved: (before: Int, after: Int, cvId: Int)?

    init(api: APIClient, jobURL: String, cvId: Int) { self.api = api; self.jobURL = jobURL; self.cvId = cvId }

    var found: [MatchKeyword] { match?.keywords.filter(\.found) ?? [] }
    var missing: [MatchKeyword] { match?.keywords.filter { !$0.found } ?? [] }

    func load(refresh: Bool = false) async {
        busy = refresh ? .refresh : .loading
        error = nil
        defer { busy = nil }
        do {
            if refresh { proposal = nil }
            match = try await api.match(cv: cvId, job: jobURL, refresh: refresh)
        } catch { self.error = Self.text(error) }
    }

    func toggle(_ term: String) {
        proposal = nil
        if let i = attested.firstIndex(of: term) { attested.remove(at: i) }
        else if attested.count < MatchWeights.maxAttested { attested.append(term) }
    }

    /// Returns true when a proposal is ready to show.
    func propose() async -> Bool {
        busy = .propose
        error = nil
        saved = nil
        defer { busy = nil }
        do {
            let p = try await api.proposal(cv: cvId, job: jobURL, attested: attested)
            proposal = p
            chosen = Set(p.patches.indices)
            return true
        } catch { self.error = Self.text(error); return false }
    }

    /// Saves the chosen patches as a tailored copy. 409 = the base CV changed: the proposal is dropped.
    func save() async -> Bool {
        guard let p = proposal else { return false }
        busy = .save
        error = nil
        defer { busy = nil }
        let patches = p.patches.indices.filter(chosen.contains).map { TailorBody.Patch(before: p.patches[$0].before, after: p.patches[$0].after, reason: p.patches[$0].reason) }
        do {
            let r = try await api.tailor(TailorBody(job_url: jobURL, base_cv_id: cvId, attested: attested, patches: patches, source_hash: p.source_hash))
            proposal = nil
            saved = (r.score_before ?? p.score_before, r.score_after ?? p.score_after, r.cv.id)
            return true
        } catch let e as APIError where e.kind == .conflict {
            proposal = nil
            error = "Il CV è cambiato: rigenera la proposta"
            return false
        } catch { self.error = Self.text(error); return false }
    }

    static func text(_ e: Error) -> String { (e as? LocalizedError)?.errorDescription ?? "Operazione non riuscita" }
}

/// I3 · CV match · analisi.
struct CvMatchView: View {
    let job: Job
    @Environment(Store.self) private var store
    @State private var model: CvMatchModel?
    @State private var sheet: SheetKind?

    enum SheetKind: String, Identifiable { case keywords, patches; var id: String { rawValue } }

    private var bases: [CvSummary] { store.cvs.filter(\.isBase) }

    var body: some View {
        Group {
            if store.loaded && bases.isEmpty {
                EmptyState(icon: "doc.badge.plus", title: "Nessun CV", text: "Carica prima un CV dalla web app (pagina CV).")
            } else if let model {
                content(model)
            } else {
                ProgressView()
            }
        }
        .task(id: bases.map(\.id)) { if model == nil, let first = bases.first(where: \.isDefault) ?? bases.first { await select(first.id) } }
        .sheet(item: $sheet) { kind in
            if let model {
                NavigationStack {
                    if kind == .keywords { KeywordsSheet(model: model, openPatches: { sheet = .patches }) }
                    else { PatchesSheet(model: model) }
                }
                .presentationDetents([.large])
            }
        }
    }

    private func select(_ id: Int) async {
        let m = CvMatchModel(api: store.api, jobURL: job.job_url, cvId: id)
        model = m
        await m.load()
        // Screenshot launch arguments: -uiSheet keywords|patches
        if UIArgs.sheet == "keywords" { sheet = .keywords }
        if UIArgs.sheet == "patches" {
            for k in m.missing { m.toggle(k.term) }
            if await m.propose() { sheet = .patches }
        }
    }

    @ViewBuilder
    private func content(_ m: CvMatchModel) -> some View {
        if bases.count > 1 {
            Menu {
                ForEach(bases) { cv in
                    Button { Task { await select(cv.id) } } label: { if cv.id == m.cvId { Label(cv.name, systemImage: "checkmark") } else { Text(cv.name) } }
                }
            } label: {
                Label(bases.first { $0.id == m.cvId }?.name ?? "CV", systemImage: "doc.text").frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
            }
            .accessibilityLabel("CV di partenza")
        }
        if m.busy == .loading {
            VStack(alignment: .leading, spacing: 10) {
                Label("Analizzo l’annuncio… la prima volta servono alcuni secondi.", systemImage: "hourglass")
                    .font(.subheadline).foregroundStyle(Theme.mutedForeground)
                ProgressView()
            }
            .panel()
            .accessibilityElement(children: .combine)
        } else if let r = m.match {
            analysis(m, r)
            keywords(m)
        } else if let e = m.error {
            VStack(alignment: .leading, spacing: 10) {
                Label(e, systemImage: "exclamationmark.shield").font(.subheadline.weight(.medium)).foregroundStyle(Theme.destructive)
                Button("Riprova") { Task { await m.load() } }.buttonStyle(.bordered).frame(minHeight: 44)
            }
            .panel(dashed: true)
        }
        if let s = m.saved {
            Label("CV adattato salvato: \(s.before) → \(s.after)", systemImage: "checkmark.circle")
                .font(.subheadline).foregroundStyle(Theme.foreground)
                .accessibilityAddTraits(.updatesFrequently)
        }
    }

    private func analysis(_ m: CvMatchModel, _ r: MatchReport) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 14) {
                ScoreRing(value: r.overall)
                VStack(alignment: .leading, spacing: 4) {
                    Text([r.job.role, r.job.company].compactMap { $0?.nilIfEmpty }.joined(separator: " · ")).font(.subheadline.weight(.semibold))
                    Text("Stima di JobSpy, non il punteggio di un ATS reale.").font(.caption).foregroundStyle(Theme.mutedForeground)
                    Button {
                        Task { await m.load(refresh: true) }
                    } label: {
                        Label(m.busy == .refresh ? "Rileggo…" : "Rileggi l’annuncio", systemImage: "arrow.clockwise").font(.footnote)
                    }
                    .disabled(m.busy != nil).frame(minHeight: 44)
                }
            }
            ForEach(MatchWeights.rows, id: \.label) { row in
                let v = r.components[keyPath: row.key]
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(row.label).font(.subheadline)
                        Text("\(row.weight)%").font(.caption).foregroundStyle(Theme.mutedForeground)
                        Spacer()
                        if let v { Text("\(v)").font(.system(.caption, design: .monospaced).weight(.semibold)) }
                        else { Text("non valutabile").font(.caption.italic()).foregroundStyle(Theme.unknownForeground) }
                    }
                    MeterBar(value: v.map { Double($0) / 100 })
                }
                .accessibilityElement(children: .combine)
            }
        }
        .panel()
    }

    private func keywords(_ m: CvMatchModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Parole chiave dell’annuncio").font(.subheadline.weight(.semibold)).accessibilityAddTraits(.isHeader)
            if !m.found.isEmpty {
                Text("Già nel CV (\(m.found.count))").font(.caption).foregroundStyle(Theme.mutedForeground)
                FlowLayout {
                    ForEach(m.found) { k in InfoChip(text: k.term, icon: "checkmark", fg: Theme.candidatiForeground, bg: Theme.candidati) }
                }
            }
            if !m.missing.isEmpty {
                Text("Mancanti (\(m.missing.count))").font(.caption).foregroundStyle(Theme.mutedForeground)
                FlowLayout {
                    ForEach(m.missing) { k in
                        let on = m.attested.contains(k.term)
                        TagView(text: on ? "\(k.term) · ce l’ho" : k.term, unknown: !on)
                    }
                }
            }
            if m.match?.keywords.isEmpty == true {
                Text("Nessuna parola chiave estratta dall’annuncio.").font(.subheadline).foregroundStyle(Theme.mutedForeground)
            }
            if let e = m.error { Text(e).font(.footnote).foregroundStyle(Theme.destructive) }
            HStack {
                if !m.missing.isEmpty {
                    Button("Scegli le parole chiave") { sheet = .keywords }.buttonStyle(.bordered).frame(minHeight: 44)
                }
                Button {
                    Task { if await m.propose() { sheet = .patches } }
                } label: {
                    if m.busy == .propose { ProgressView() } else { Label("Adatta CV", systemImage: "wand.and.stars") }
                }
                .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).frame(minHeight: 44).disabled(m.busy != nil)
            }
            .buttonBorderShape(.capsule)
        }
        .panel()
    }
}

/// I4 · parole chiave: «ce l'ho» toggles for the missing ones, grouped by kind.
struct KeywordsSheet: View {
    @Bindable var model: CvMatchModel
    let openPatches: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        Form {
            Section {
                Text("Spunta «ce l’ho» solo se le hai davvero: solo queste possono entrare nel CV adattato.")
                    .font(.footnote).foregroundStyle(Theme.mutedForeground)
            }
            ForEach(["required", "preferred", "keyword"], id: \.self) { kind in
                let items = model.missing.filter { $0.kind == kind }
                if !items.isEmpty {
                    Section(MatchWeights.kindLabel(kind)) {
                        ForEach(items) { k in
                            Toggle(isOn: Binding(get: { model.attested.contains(k.term) }, set: { _ in model.toggle(k.term) })) {
                                VStack(alignment: .leading) {
                                    Text(k.term)
                                    Text("ce l’ho").font(.caption).foregroundStyle(Theme.mutedForeground)
                                }
                            }
                            .tint(Theme.primary)
                            .disabled(!model.attested.contains(k.term) && model.attested.count >= MatchWeights.maxAttested)
                        }
                    }
                }
            }
            if let e = model.error { Section { Text(e).foregroundStyle(Theme.destructive) } }
        }
        .navigationTitle("Parole chiave")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Chiudi") { dismiss() } } }
        .safeAreaInset(edge: .bottom) {
            Button {
                Task { if await model.propose() { openPatches() } }
            } label: {
                Group {
                    if model.busy == .propose { Label("Preparo le modifiche…", systemImage: "hourglass") }
                    else { Text("Adatta CV · \(model.attested.count) confermate") }
                }
                .frame(maxWidth: .infinity, minHeight: 48)
            }
            .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule)
            .disabled(model.busy != nil)
            .padding(.horizontal, 16).padding(.vertical, 8).background(.bar)
        }
    }
}

/// I5 · modifiche: before → after, rejected count, a checkbox per patch, «Salva CV adattato · N».
struct PatchesSheet: View {
    @Bindable var model: CvMatchModel
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List {
            if let p = model.proposal {
                Section {
                    HStack {
                        Text("Punteggio")
                        Spacer()
                        Text("\(p.score_before) → \(p.score_after)").font(.system(.title3, design: .monospaced).weight(.semibold))
                    }
                    .accessibilityElement(children: .combine)
                    Text("con tutte le modifiche").font(.caption).foregroundStyle(Theme.mutedForeground)
                    if p.rejected > 0 {
                        Label("\(p.rejected) \(p.rejected == 1 ? "modifica scartata" : "modifiche scartate") dai controlli", systemImage: "exclamationmark.triangle")
                            .font(.footnote).foregroundStyle(Theme.valutaForeground)
                    }
                }
                if p.patches.isEmpty {
                    Text("Nessuna modifica proposta supera i controlli.").foregroundStyle(Theme.mutedForeground)
                }
                ForEach(Array(p.patches.enumerated()), id: \.offset) { i, patch in
                    Section { PatchRow(patch: patch, on: Binding(get: { model.chosen.contains(i) }, set: { if $0 { model.chosen.insert(i) } else { model.chosen.remove(i) } })) }
                }
                Section { Text("Viene creata una copia: il CV di partenza resta com’è.").font(.footnote).foregroundStyle(Theme.mutedForeground) }
            } else if let e = model.error {
                Text(e).foregroundStyle(Theme.destructive)
            }
        }
        .navigationTitle("Modifiche proposte")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Chiudi") { dismiss() } } }
        .safeAreaInset(edge: .bottom) {
            if let p = model.proposal, !p.patches.isEmpty {
                Button {
                    Task {
                        if await model.save() {
                            store.show("CV adattato salvato")
                            await store.reloadCvs()
                            dismiss()
                        }
                    }
                } label: {
                    Group {
                        if model.busy == .save { ProgressView() } else { Text("Salva CV adattato · \(model.chosen.count)") }
                    }
                    .frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule)
                .disabled(model.busy != nil || model.chosen.isEmpty)
                .padding(.horizontal, 16).padding(.vertical, 8).background(.bar)
            }
        }
    }
}

struct PatchRow: View {
    let patch: TailorPatch
    @Binding var on: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button { on.toggle() } label: {
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: on ? "checkmark.square.fill" : "square").font(.title3).foregroundStyle(Theme.primary)
                    Text(patch.reason).font(.subheadline.weight(.medium)).foregroundStyle(Theme.foreground).multilineTextAlignment(.leading)
                }
                .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                .contentShape(.rect)
            }
            .buttonStyle(.plain)
            .accessibilityAddTraits(on ? .isSelected : [])
            .accessibilityHint("Includi questa modifica")
            if let k = patch.keywords, !k.isEmpty { FlowLayout { ForEach(k, id: \.self) { TagView(text: $0) } } }
            VStack(alignment: .leading, spacing: 4) {
                Text("Prima").font(.caption.weight(.medium)).foregroundStyle(Theme.mutedForeground)
                Text(patch.before).font(.footnote)
            }
            .padding(10).frame(maxWidth: .infinity, alignment: .leading).background(Theme.muted, in: .rect(cornerRadius: 6))
            VStack(alignment: .leading, spacing: 4) {
                Text("Dopo").font(.caption.weight(.medium)).foregroundStyle(Theme.mutedForeground)
                Text(patch.after).font(.footnote)
            }
            .padding(10).frame(maxWidth: .infinity, alignment: .leading).background(Theme.candidati.opacity(0.6), in: .rect(cornerRadius: 6))
        }
        .padding(.vertical, 4)
    }
}
