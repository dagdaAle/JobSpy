import SwiftUI

/// I7 · Canali: pushed from the Feed. A card per channel with «Aggiorna»; failed = red border, reason and «Riprova».
/// Swipe = Elimina, pull-to-refresh updates every channel, «+» opens I8, tap edits.
struct ChannelsView: View {
    @Environment(Store.self) private var store
    @State private var form: FormTarget?
    @State private var deleting: Channel?

    struct FormTarget: Identifiable { let channel: Channel?; var id: Int { channel?.id ?? -1 } }

    var body: some View {
        List {
            if let p = store.refreshAllProgress {
                LoadingSubtitle().listRowSeparator(.hidden).listRowBackground(Color.clear)
                    .accessibilityValue("\(p.done) di \(p.total)")
            }
            ForEach(store.channels) { c in
                ChannelCard(channel: c) { form = FormTarget(channel: c) }
                    .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                    .listRowSeparator(.hidden).listRowBackground(Color.clear)
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) { deleting = c } label: { Label("Elimina", systemImage: "trash") }
                    }
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .overlay { if store.loaded && store.channels.isEmpty { NoChannels { form = FormTarget(channel: nil) } } }
        .navigationTitle("Canali")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { form = FormTarget(channel: nil) } label: { Image(systemName: "plus") }.accessibilityLabel("Nuovo canale")
            }
        }
        .refreshable { await store.refreshAll() }
        .sheet(item: $form) { f in NavigationStack { ChannelFormView(channel: f.channel) } }
        .confirmationDialog("Eliminare «\(deleting?.title ?? "")»?", isPresented: Binding(get: { deleting != nil }, set: { if !$0 { deleting = nil } }), titleVisibility: .visible) {
            Button("Elimina canale", role: .destructive) { if let c = deleting { Task { await store.deleteChannel(c) } } }
        } message: {
            Text("Le offerte già trovate e i tuoi verdetti restano.")
        }
    }
}

struct ChannelCard: View {
    let channel: Channel
    let edit: () -> Void
    @Environment(Store.self) private var store

    var body: some View {
        let c = channel
        let busy = store.refreshing.contains(c.id)
        let new = c.new_count ?? 0
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "dot.radiowaves.left.and.right").font(.subheadline.weight(.semibold))
                .foregroundStyle(c.failed ? Theme.destructive : Theme.areaLavoro)
                .frame(width: 40, height: 40).background(c.failed ? Theme.destructiveSoft : Theme.areaLavoroSoft, in: .circle)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 4) {
                HStack(alignment: .firstTextBaseline) {
                    Text(c.title).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.foreground).lineLimit(2)
                    Spacer(minLength: 8)
                    Text("\(new) nuove").font(.system(.caption, design: .monospaced).weight(.semibold))
                        .foregroundStyle(new > 0 ? Theme.foreground : Theme.mutedForeground)
                }
                Text(Self.summary(c)).font(.caption).foregroundStyle(Theme.mutedForeground).lineLimit(2)
                HStack {
                    if c.failed {
                        Text(store.channelErrors[c.id] ?? "Ultimo aggiornamento non riuscito").font(.caption).foregroundStyle(Theme.destructive).lineLimit(2)
                    } else if let at = c.last_refresh_at {
                        Text("Aggiornato \(Fmt.ago(at))").font(.caption).foregroundStyle(Theme.mutedForeground)
                    } else {
                        Text("Mai aggiornato").font(.caption.italic()).foregroundStyle(Theme.unknownForeground)
                    }
                    Spacer()
                    Button { Task { await store.refresh(channel: c) } } label: {
                        if busy { ProgressView().controlSize(.small) } else { Text(c.failed ? "Riprova" : "Aggiorna") }
                    }
                    .font(.footnote.weight(.semibold))
                    .padding(.horizontal, 12).frame(minHeight: 32)
                    .foregroundStyle(c.failed ? Theme.destructiveSoft : Theme.foreground)
                    .background(c.failed ? Theme.destructive : Theme.muted, in: .capsule)
                    .frame(minHeight: 44)
                    .buttonStyle(.plain)
                    .disabled(busy || store.refreshAllProgress != nil)
                    .accessibilityLabel(c.failed ? "Riprova \(c.title)" : "Aggiorna \(c.title)")
                }
            }
        }
        .padding(14)
        .background(Theme.card, in: .rect(cornerRadius: 16))
        .overlay { RoundedRectangle(cornerRadius: 16).stroke(c.failed ? Theme.destructive : Theme.border) }
        .contentShape(.rect(cornerRadius: 16))
        .onTapGesture(perform: edit)
        .accessibilityAction(named: "Modifica", edit)
    }

    /// «python · Verona 25 km · 7 giorni»
    static func summary(_ c: Channel) -> String {
        let place = c.is_remote?.value == true ? "remoto" : [c.location?.nilIfEmpty, c.distance_km.map { "\($0) km" }].compactMap { $0 }.joined(separator: " ")
        let days = c.hours_old.map { "\(max(1, $0 / 24)) giorni" } ?? "tutte le date"
        return [Fmt.site(c.site), c.search_term?.nilIfEmpty, place.nilIfEmpty, days].compactMap { $0 }.joined(separator: " · ")
    }
}

/// I8 · Nuovo canale (sheet), also used to edit. Sources are a multi-selection on create
/// (one backend channel per source) and a single choice on edit.
struct ChannelFormView: View {
    let channel: Channel?
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var body_ = ChannelBody()
    @State private var selected: [String] = ["linkedin"]
    @State private var days = 7
    @State private var include = ""
    @State private var exclude = ""
    @State private var saving = false
    @State private var companyQuery = ""
    @State private var companies: [FreehireCompany] = []

    var body: some View {
        Form {
            Section("Canale") {
                TextField("Nome (facoltativo)", text: $body_.name)
                TextField("Cosa cerchi, es. sviluppatore python", text: $body_.search_term)
                    .textInputAutocapitalization(.never)
            }
            Section {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) { ForEach(store.sites, id: \.self) { sourceChip($0) } }.padding(.vertical, 4)
                }
            } header: { Text("Fonti") } footer: {
                if channel == nil && selected.count > 1 { Text("Verrà creato un canale per fonte.") }
            }
            if selected.contains("freehire") {
                Section {
                    HStack {
                        TextField("Segui un’azienda (facoltativo)", text: $companyQuery).onSubmit(findCompanies)
                        Button("Cerca", action: findCompanies).disabled(companyQuery.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                    ForEach(companies) { co in
                        Button { body_.company_slug = body_.company_slug == co.slug ? "" : co.slug } label: {
                            HStack {
                                Text(co.name ?? co.slug).foregroundStyle(Theme.foreground)
                                Spacer()
                                if let n = co.job_count { Text("\(n)").font(.caption.monospaced()).foregroundStyle(Theme.mutedForeground) }
                                if body_.company_slug == co.slug { Image(systemName: "checkmark") }
                            }
                        }
                        .accessibilityAddTraits(body_.company_slug == co.slug ? .isSelected : [])
                    }
                    if !body_.company_slug.isEmpty && companies.isEmpty { LabeledContent("Azienda seguita", value: body_.company_slug) }
                } header: { Text("freehire") }
            }
            Section("Dove") {
                TextField("Luogo", text: $body_.location)
                Stepper(value: $body_.distance_km, in: 5...200, step: 5) {
                    LabeledContent("Raggio") { Text("\(body_.distance_km) km").monospaced() }
                }
                Stepper(value: $days, in: 0...60) {
                    LabeledContent("Ultimi giorni") { Text(days == 0 ? "tutti" : "\(days)").monospaced() }
                }
                Toggle("Solo remoto", isOn: $body_.is_remote).tint(Theme.primary)
            }
            Section {
                TextField("Includi parole, separate da virgole", text: $include, axis: .vertical).textInputAutocapitalization(.never)
                TextField("Escludi parole, separate da virgole", text: $exclude, axis: .vertical).textInputAutocapitalization(.never)
            } header: { Text("Parole") } footer: {
                Text("Spento «Solo remoto» tiene anche ibrido e sede entro il raggio. I filtri valgono dal prossimo aggiornamento.")
            }
        }
        .navigationTitle(channel == nil ? "Nuovo canale" : "Modifica canale")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) { Button("Annulla") { dismiss() }.foregroundStyle(Theme.mutedForeground) }
            ToolbarItem(placement: .confirmationAction) {
                Button { Task { await save() } } label: {
                    if saving { ProgressView() } else { Text(channel == nil ? "Crea" : "Salva").fontWeight(.semibold) }
                }
                .buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule)
                .disabled(!valid || saving)
            }
        }
        .interactiveDismissDisabled(saving)
        .task {
            await store.loadSites()
            if let channel {
                body_ = ChannelBody(channel)
                selected = [body_.site]
                days = body_.hours_old.map { $0 / 24 } ?? 0
                include = body_.include_keywords.joined(separator: ", ")
                exclude = body_.exclude_keywords.joined(separator: ", ")
            }
        }
    }

    private var valid: Bool { !body_.search_term.trimmingCharacters(in: .whitespaces).isEmpty && !selected.isEmpty }

    private func sourceChip(_ site: String) -> some View {
        let on = selected.contains(site)
        return Button {
            if channel != nil { selected = [site] }
            else if on { selected.removeAll { $0 == site } } else { selected.append(site) }
        } label: {
            HStack(spacing: 4) {
                if on { Image(systemName: "checkmark").font(.caption.weight(.bold)) }
                Text(Fmt.site(site).components(separatedBy: " · ").first ?? site)
            }
            .font(.subheadline.weight(.medium))
            .padding(.horizontal, 12).frame(minHeight: 34)
            .foregroundStyle(on ? Theme.primaryForeground : Theme.foreground)
            .background(on ? Theme.primary : Theme.card, in: .capsule)
            .overlay { Capsule().stroke(on ? .clear : Theme.border) }
            .frame(minHeight: 44)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    private func findCompanies() {
        let q = companyQuery.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return }
        Task { do { companies = try await store.api.freehireCompanies(q) } catch { store.fail(error) } }
    }

    static func list(_ s: String) -> [String] {
        s.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
    }

    private func save() async {
        saving = true
        defer { saving = false }
        var b = body_
        b.search_term = b.search_term.trimmingCharacters(in: .whitespaces)
        b.name = b.name.trimmingCharacters(in: .whitespaces)
        b.hours_old = days > 0 ? days * 24 : nil
        b.include_keywords = Self.list(include)
        b.exclude_keywords = Self.list(exclude)
        if !selected.contains("freehire") { b.company_slug = "" }
        let ok: Bool
        if let channel {
            b.site = selected.first ?? b.site
            ok = await store.updateChannel(channel.id, b)
        } else {
            ok = await store.createChannels(b, sites: selected)
        }
        if ok { dismiss() }
    }
}
