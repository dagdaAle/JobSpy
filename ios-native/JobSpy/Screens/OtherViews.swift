import SwiftUI

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

