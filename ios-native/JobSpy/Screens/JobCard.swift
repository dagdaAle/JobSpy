import SwiftUI

/// The card (DecisionCard.tsx + JobCard.tsx): white frame r20, inner panel r14 tinted by the decision;
/// «Non noto» = white panel with a dashed border. The whole card opens the detail.
struct JobCard: View {
    let job: Job
    @Environment(Store.self) private var store

    var body: some View {
        let analysis = store.analysis(job.job_url)
        let decision = Decision(analysis)
        let state = store.state(job)
        let salary = JobText.salary(job, analysis)
        let left = state == .open ? Fmt.daysLeftInFeed(job.feed_since ?? job.first_seen_at, feedDays: store.feedDays) : nil
        let app = store.application(job.job_url)

        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top) {
                    FlowLayout(spacing: 6) {
                        InfoChip(text: [Fmt.ago(job.date_posted), JobText.sources(job)].filter { !$0.isEmpty }.joined(separator: " · "), icon: "clock")
                        if job.isNew { InfoChip(text: "Nuova") }
                        if let left, left <= 2 { InfoChip(text: left <= 0 ? "esce oggi" : left == 1 ? "esce domani" : "esce tra \(left) g") }
                        if job.source_closed_at != nil { InfoChip(text: "Chiusa alla fonte", fg: Theme.destructive, bg: Theme.destructiveSoft) }
                    }
                    Spacer(minLength: 4)
                    BookmarkButton(job: job, dashed: decision.dashed)
                }
                DecisionBadge(decision: decision, label: JobText.badgeLabel(decision, analysis))
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        if let c = job.company, !c.isEmpty {
                            Text(c).font(.footnote.weight(.medium)).foregroundStyle(Theme.mutedForeground).lineLimit(1)
                        }
                        Text(job.displayTitle).font(.headline).foregroundStyle(Theme.foreground).lineLimit(3)
                    }
                    Spacer(minLength: 0)
                    Text(Fmt.monogram(job.company))
                        .font(.footnote.weight(.semibold)).foregroundStyle(Theme.mutedForeground)
                        .frame(width: 40, height: 40).background(Theme.card, in: .circle)
                        .overlay { if decision.dashed { Circle().stroke(Theme.border) } }
                        .accessibilityHidden(true)
                }
                if let r = JobText.reason(analysis) {
                    Text(r).font(.footnote).foregroundStyle(Theme.foreground).lineLimit(2)
                }
                let tags = Array((analysis?.tags ?? []).prefix(4))
                if !tags.isEmpty || JobText.place(job, analysis) == nil {
                    FlowLayout(spacing: 6) {
                        ForEach(tags, id: \.self) { TagView(text: $0) }
                        if JobText.place(job, analysis) == nil { TagView(text: "Sede non nota", unknown: true) }
                    }
                }
                if let app {
                    Label(app.status.label, systemImage: "paperplane").font(.caption.weight(.medium)).foregroundStyle(Theme.mutedForeground)
                }
            }
            .padding(.horizontal, 14).padding(.top, 12).padding(.bottom, 14)
            .background(decision.tint, in: .rect(cornerRadius: 14))
            .overlay { if decision.dashed { RoundedRectangle(cornerRadius: 14).stroke(Theme.unknownBorder, style: Theme.dash) } }

            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    if let salary {
                        HStack(alignment: .firstTextBaseline, spacing: 4) {
                            Text(salary).font(.system(.callout, design: .monospaced).weight(.semibold))
                            if Fmt.salary(job) != nil { Text("RAL").font(.caption).foregroundStyle(Theme.mutedForeground) }
                        }
                    } else {
                        Text("RAL non indicata").font(.callout.italic()).foregroundStyle(Theme.unknownForeground)
                    }
                    Text(JobText.place(job, analysis) ?? "Sede non indicata").font(.caption).foregroundStyle(Theme.mutedForeground).lineLimit(1)
                }
                Spacer()
                Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(Theme.mutedForeground)
            }
            .padding(.horizontal, 10).padding(.top, 10).padding(.bottom, 6)
        }
        .padding(6)
        .background(Theme.card, in: .rect(cornerRadius: 20))
        .overlay { RoundedRectangle(cornerRadius: 20).stroke(decision.dashed ? Theme.unknownBorder : Theme.border, style: decision.dashed ? Theme.dash : StrokeStyle(lineWidth: 1)) }
        .opacity(state == .dismissed ? 0.7 : 1)
        .contentShape(.rect(cornerRadius: 20))
        .accessibilityElement(children: .combine)
        .accessibilityHint("Apre il dettaglio")
    }
}

/// Bookmark on the card: 32 visual, 44 touch. Filled when saved; undo for dismissed/archived lives in the swipe.
struct BookmarkButton: View {
    let job: Job
    var dashed = false
    @Environment(Store.self) private var store

    var body: some View {
        let saved = store.state(job) == .saved
        Button {
            store.setVerdict(job, saved ? nil : .like)
        } label: {
            Image(systemName: saved ? "bookmark.fill" : "bookmark")
                .font(.footnote.weight(.semibold)).foregroundStyle(Theme.foreground)
                .frame(width: 32, height: 32).background(Theme.card, in: .circle)
                .overlay { if dashed { Circle().stroke(Theme.border) } }
                .frame(width: 44, height: 44)
                .contentShape(.circle)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(saved ? "Togli dai preferiti" : "Aggiungi ai preferiti")
        .accessibilityAddTraits(saved ? .isSelected : [])
    }
}
