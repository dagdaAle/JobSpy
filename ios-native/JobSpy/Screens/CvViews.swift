import SwiftUI
import UniformTypeIdentifiers

/// I9a · CV elenco: groups BASE / ADATTATI, star on the default (change it with a long press), swipe = Elimina,
/// «Carica PDF» top right (the server turns the text into Markdown).
struct CvListView: View {
    @Environment(Store.self) private var store
    @State private var importing = false
    @State private var uploading = false
    @State private var deleting: CvSummary?
    @State private var deepLink: Int? = UIArgs.tab == 3 && UIArgs.cv > 0 ? UIArgs.cv : nil

    var body: some View {
        let base = store.cvs.filter(\.isBase), tailored = store.cvs.filter { !$0.isBase }
        List {
            if uploading {
                HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Carico il PDF e ne estraggo il testo…") }
                    .font(.subheadline).foregroundStyle(Theme.mutedForeground)
            }
            if !base.isEmpty { Section("Base") { ForEach(base) { row($0) } } }
            if !tailored.isEmpty { Section("Adattati") { ForEach(tailored) { row($0) } } }
        }
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay { LoadState(empty: store.cvs.isEmpty, emptyIcon: "doc.text", emptyTitle: "Nessun CV", emptyText: "Carica il tuo CV in PDF: il testo diventa Markdown sul server.") }
        .navigationTitle("CV")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { importing = true } label: { Label("Carica PDF", systemImage: "arrow.up.doc").labelStyle(.titleAndIcon) }
                    .disabled(uploading)
            }
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.pdf]) { result in
            switch result {
            case .success(let url): Task { uploading = true; await store.upload(url); uploading = false }
            case .failure(let e): store.fail(e)
            }
        }
        .navigationDestination(for: Int.self) { CvDetailView(id: $0) }
        .navigationDestination(item: $deepLink) { CvDetailView(id: $0) }
        .refreshable { await store.reloadCvs() }
        .confirmationDialog("Eliminare «\(deleting?.name ?? "")»?", isPresented: Binding(get: { deleting != nil }, set: { if !$0 { deleting = nil } }), titleVisibility: .visible) {
            Button("Elimina CV", role: .destructive) { if let cv = deleting { Task { await store.deleteCv(cv) } } }
        }
    }

    private func row(_ cv: CvSummary) -> some View {
        let parent = cv.parent_id.flatMap { id in store.cvs.first { $0.id == id }?.name }
        return NavigationLink(value: cv.id) {
            HStack(spacing: 12) {
                Image(systemName: cv.isBase ? "doc.text" : "wand.and.stars").font(.subheadline)
                    .foregroundStyle(cv.isBase ? Theme.foreground : Theme.areaLavoro)
                    .frame(width: 36, height: 36).background(cv.isBase ? Theme.muted : Theme.areaLavoroSoft, in: .circle)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 4) {
                        Text(cv.name).font(.subheadline.weight(.medium)).lineLimit(2)
                        if cv.isDefault { Image(systemName: "star.fill").font(.caption).foregroundStyle(Theme.foreground).accessibilityHidden(true) }
                    }
                    Text(subtitle(cv, parent)).font(.caption).foregroundStyle(Theme.mutedForeground).lineLimit(1)
                }
            }
            .accessibilityElement(children: .combine)
        }
        .contextMenu {
            if cv.isBase && !cv.isDefault {
                Button { Task { await store.setDefault(cv) } } label: { Label("Rendi predefinito", systemImage: "star") }
            }
            Button(role: .destructive) { deleting = cv } label: { Label("Elimina", systemImage: "trash") }
        }
        .swipeActions { Button(role: .destructive) { deleting = cv } label: { Label("Elimina", systemImage: "trash") } }
    }

    private func subtitle(_ cv: CvSummary, _ parent: String?) -> String {
        if cv.isBase {
            return [cv.isDefault ? "predefinito" : nil, "aggiornato \(Fmt.ago(cv.updated_at))"].compactMap { $0 }.joined(separator: " · ")
        }
        return ["da \(parent ?? "CV base")", Fmt.ago(cv.updated_at)].joined(separator: " · ")
    }
}

/// I9b · CV aperto: «Anteprima | Markdown», chips (kind, default, words, pages), action bar «Modifica» / «Revisione AI».
struct CvDetailView: View {
    let id: Int
    @Environment(Store.self) private var store
    @State private var cv: Cv?
    @State private var pages: Int?
    @State private var error: String?
    @State private var tab = 0
    @State private var editing = false
    @State private var reviewing = UIArgs.sheet == "review"

    var body: some View {
        ScrollView {
            if let cv {
                VStack(alignment: .leading, spacing: 14) {
                    Picker("Vista", selection: $tab) { Text("Anteprima").tag(0); Text("Markdown").tag(1) }.pickerStyle(.segmented)
                    FlowLayout {
                        InfoChip(text: cv.kind == "tailored" ? "Adattato" : "Base", bg: Theme.muted)
                        if cv.is_default?.value == true { InfoChip(text: "Predefinito", icon: "star.fill", bg: Theme.muted) }
                        InfoChip(text: "\(Self.words(cv.markdown)) parole", bg: Theme.muted).monospaced()
                        if let pages { InfoChip(text: "\(pages) \(pages == 1 ? "pagina" : "pagine")", bg: Theme.muted).monospaced() }
                    }
                    if tab == 0 {
                        MarkdownPreview(text: cv.markdown ?? "").panel()
                    } else {
                        Text(cv.markdown ?? "").font(.system(.footnote, design: .monospaced)).textSelection(.enabled).panel()
                    }
                }
                .padding(16)
            } else if let error {
                EmptyState(icon: "exclamationmark.triangle", title: "Non riesco a caricare il CV", text: error, action: ("Riprova", { Task { await load() } }))
            } else {
                ProgressView().padding(40)
            }
        }
        .background(Theme.background)
        .navigationTitle(cv?.name ?? "CV")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let summary = store.cvs.first(where: { $0.id == id }), summary.isBase {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { Task { await store.setDefault(summary); await load() } } label: {
                        Image(systemName: summary.isDefault ? "star.fill" : "star")
                    }
                    .disabled(summary.isDefault)
                    .accessibilityLabel(summary.isDefault ? "CV predefinito" : "Rendi predefinito")
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    if let cv, let md = cv.markdown { ShareLink(item: md, subject: Text(cv.name)) { Label("Condividi il testo", systemImage: "square.and.arrow.up") } }
                    Button { Task { await load() } } label: { Label("Ricarica", systemImage: "arrow.clockwise") }
                } label: { Image(systemName: "ellipsis") }
                .accessibilityLabel("Altre azioni")
            }
        }
        .safeAreaInset(edge: .bottom) {
            if cv != nil {
                HStack(spacing: 12) {
                    Button { editing = true } label: { Label("Modifica", systemImage: "pencil").frame(maxWidth: .infinity, minHeight: 44) }
                        .buttonStyle(.bordered)
                    Button { reviewing = true } label: { Label("Revisione AI", systemImage: "sparkles").frame(maxWidth: .infinity, minHeight: 44) }
                        .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground)
                }
                .buttonBorderShape(.capsule)
                .padding(.horizontal, 16).padding(.vertical, 10).background(.bar)
            }
        }
        .sheet(isPresented: $editing) { NavigationStack { CvEditView(cv: cv!) { await load() } } }
        .sheet(isPresented: $reviewing) { NavigationStack { CvReviewView(id: id) { _ in Task { await store.reloadCvs() } } } }
        .task { await load() }
    }

    private func load() async {
        do {
            cv = try await store.api.cv(id)
            error = nil
            pages = try? await store.api.pages(cv: id) // optional: the PDF renderer can fail on odd Markdown
        } catch { self.error = CvMatchModel.text(error) }
    }

    static func words(_ s: String?) -> Int { (s ?? "").split(whereSeparator: \.isWhitespace).count }
}

/// Minimal Markdown renderer for CVs: headings, bullets, paragraphs with inline emphasis and links.
struct MarkdownPreview: View {
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(Array(text.components(separatedBy: "\n").enumerated()), id: \.offset) { _, raw in
                let line = raw.trimmingCharacters(in: .whitespaces)
                if line.hasPrefix("# ") {
                    Text(inline(String(line.dropFirst(2)))).font(.title3.weight(.semibold)).accessibilityAddTraits(.isHeader)
                } else if line.hasPrefix("## ") {
                    Text(inline(String(line.dropFirst(3)))).font(.caption.weight(.semibold)).textCase(.uppercase)
                        .foregroundStyle(Theme.mutedForeground).padding(.top, 8).accessibilityAddTraits(.isHeader)
                } else if line.hasPrefix("### ") {
                    Text(inline(String(line.dropFirst(4)))).font(.subheadline.weight(.semibold)).padding(.top, 4)
                } else if line.hasPrefix("- ") || line.hasPrefix("* ") {
                    HStack(alignment: .firstTextBaseline, spacing: 6) { Text("•"); Text(inline(String(line.dropFirst(2)))) }.font(.footnote)
                } else if !line.isEmpty {
                    Text(inline(line)).font(.footnote)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .textSelection(.enabled)
    }

    private func inline(_ s: String) -> AttributedString {
        (try? AttributedString(markdown: s, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(s)
    }
}

/// «Modifica»: plain Markdown editor (no board yet), PATCH /cvs/{id}.
struct CvEditView: View {
    let cv: Cv
    let saved: () async -> Void
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var text = ""
    @State private var saving = false

    var body: some View {
        TextEditor(text: $text)
            .font(.system(.footnote, design: .monospaced))
            .padding(.horizontal, 12)
            .navigationTitle("Modifica CV")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annulla") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task {
                            saving = true
                            defer { saving = false }
                            do { try await store.api.updateCv(cv.id, markdown: text); store.show("CV salvato"); await saved(); dismiss() }
                            catch { store.fail(error) }
                        }
                    } label: { if saving { ProgressView() } else { Text("Salva").fontWeight(.semibold) } }
                    .disabled(saving || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || text == cv.markdown)
                }
            }
            .interactiveDismissDisabled(text != cv.markdown)
            .onAppear { text = cv.markdown ?? "" }
    }
}

/// «Revisione AI» (result not designed yet): observations, questions and patches with a checkbox,
/// «Crea revisione · N» = POST /cvs/{id}/revision (a new CV; the original stays).
struct CvReviewView: View {
    let id: Int
    let created: (Int) -> Void
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var review: CvReview?
    @State private var chosen: Set<Int> = []
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        List {
            if let r = review {
                if let o = r.observations, !o.isEmpty { Section("Osservazioni") { ForEach(o, id: \.self) { Text($0).font(.subheadline) } } }
                if let q = r.questions, !q.isEmpty { Section("Domande per te") { ForEach(q, id: \.self) { Text($0).font(.subheadline) } } }
                if r.patches.isEmpty { Section { Text("Nessuna correzione proposta.").foregroundStyle(Theme.mutedForeground) } }
                ForEach(Array(r.patches.enumerated()), id: \.offset) { i, p in
                    Section { PatchRow(patch: p, on: Binding(get: { chosen.contains(i) }, set: { if $0 { chosen.insert(i) } else { chosen.remove(i) } })) }
                }
            } else if let error {
                Section { Label(error, systemImage: "exclamationmark.triangle").foregroundStyle(Theme.destructive); Button("Riprova") { Task { await load() } } }
            } else {
                Section {
                    HStack(spacing: 10) { ProgressView(); Text("Rileggo il CV… può servire un minuto.") }.foregroundStyle(Theme.mutedForeground)
                }
            }
        }
        .navigationTitle("Revisione AI")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Chiudi") { dismiss() } } }
        .safeAreaInset(edge: .bottom) {
            if let r = review, !r.patches.isEmpty {
                Button { Task { await apply(r) } } label: {
                    Group { if busy { ProgressView() } else { Text("Crea revisione · \(chosen.count)") } }.frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule)
                .disabled(busy || chosen.isEmpty)
                .padding(.horizontal, 16).padding(.vertical, 8).background(.bar)
            }
        }
        .task { await load() }
    }

    private func load() async {
        error = nil
        do { let r = try await store.api.review(cv: id); review = r; chosen = Set(r.patches.indices) }
        catch { self.error = CvMatchModel.text(error) }
    }

    private func apply(_ r: CvReview) async {
        busy = true
        defer { busy = false }
        let patches = r.patches.indices.filter(chosen.contains).map { TailorBody.Patch(before: r.patches[$0].before, after: r.patches[$0].after, reason: r.patches[$0].reason) }
        do {
            let cv = try await store.api.revise(cv: id, RevisionBody(source_hash: r.source_hash, patches: patches))
            store.show("Revisione salvata come «\(cv.name)»")
            created(cv.id)
            dismiss()
        } catch let e as APIError where e.kind == .conflict {
            error = "Il CV è cambiato: rifai la revisione"; review = nil
        } catch { store.fail(error) }
    }
}
