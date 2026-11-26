import SwiftUI

/// Penpot tokens (BRIEF-design.md): Asset Catalog colours with a dark variant.
/// Green is reserved for «Candidati»; red only for errors and certain blockers.
enum Theme {
    static let background = Color("Background")
    static let foreground = Color("Foreground")
    static let card = Color("Card")
    static let primary = Color("Primary")
    static let primaryForeground = Color("PrimaryForeground")
    static let muted = Color("Muted")
    static let mutedForeground = Color("MutedForeground")
    static let border = Color("Border")
    static let destructive = Color("Destructive")
    static let destructiveSoft = Color("DestructiveSoft")
    static let header = Color("Header")
    static let headerForeground = Color("HeaderForeground")
    static let unknown = Color("Unknown")
    static let unknownForeground = Color("UnknownForeground")
    static let unknownBorder = Color("UnknownBorder")
    static let areaLavoro = Color("AreaLavoro")
    static let areaLavoroSoft = Color("AreaLavoroSoft")
    static let deadlineSoon = Color("DeadlineSoon")
    static let deadlineSoonForeground = Color("DeadlineSoonForeground")
    static let valuta = Color("Valuta")
    static let valutaForeground = Color("ValutaForeground")
    static let candidati = Color("Candidati")
    static let candidatiForeground = Color("CandidatiForeground")

    static let dash = StrokeStyle(lineWidth: 1, dash: [4, 3])
}

extension Decision {
    var tint: Color {
        switch self {
        case .candidati: Color("Candidati")
        case .valuta: Color("Valuta")
        case .lascia: Color("Lascia")
        case .nonnoto: Color("Unknown")
        }
    }
    var text: Color {
        switch self {
        case .candidati: Color("CandidatiForeground")
        case .valuta: Color("ValutaForeground")
        case .lascia: Color("LasciaForeground")
        case .nonnoto: Color("UnknownForeground")
        }
    }
}

extension Component.Tone {
    var color: Color {
        switch self {
        case .ok: Theme.candidatiForeground
        case .warn: Theme.valutaForeground
        case .block: Theme.destructive
        }
    }
}

/// Decision badge: always icon + text, never colour alone.
struct DecisionBadge: View {
    let decision: Decision
    var label: String?
    var onTint = true

    var body: some View {
        Label(label ?? decision.label, systemImage: decision.icon)
            .font(.caption.weight(.semibold))
            .labelStyle(.titleAndIcon)
            .padding(.horizontal, 10).padding(.vertical, 4)
            .foregroundStyle(decision.text)
            .background(onTint ? Theme.card : decision.tint, in: .capsule)
            .overlay { if decision.dashed { Capsule().stroke(Theme.unknownBorder, style: Theme.dash) } }
    }
}

/// Small white chip on the card tint (age, sources).
struct InfoChip: View {
    let text: String
    var icon: String?
    var fg: Color = Theme.mutedForeground
    var bg: Color = Theme.card

    var body: some View {
        HStack(spacing: 4) {
            if let icon { Image(systemName: icon).imageScale(.small) }
            Text(text).lineLimit(1)
        }
        .font(.caption.weight(.medium))
        .padding(.horizontal, 10).padding(.vertical, 4)
        .foregroundStyle(fg)
        .background(bg, in: .capsule)
    }
}

/// Facet tag: thin outline r6; dashed when unknown.
struct TagView: View {
    let text: String
    var unknown = false

    var body: some View {
        Text(text)
            .font(.caption.weight(.medium))
            .padding(.horizontal, 8).padding(.vertical, 3)
            .foregroundStyle(unknown ? Theme.unknownForeground : Theme.foreground)
            .background(Theme.card, in: .rect(cornerRadius: 6))
            .overlay {
                RoundedRectangle(cornerRadius: 6).stroke(unknown ? Theme.unknownBorder : Theme.border, style: unknown ? Theme.dash : StrokeStyle(lineWidth: 1))
            }
    }
}

/// Wrapping row of chips/tags.
struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let rows = arrange(proposal.width ?? .infinity, subviews)
        return CGSize(width: proposal.width ?? rows.map(\.width).max() ?? 0, height: rows.last.map { $0.y + $0.height } ?? 0)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        for row in arrange(bounds.width, subviews) {
            var x = bounds.minX
            for i in row.items {
                let s = subviews[i].sizeThatFits(.unspecified)
                subviews[i].place(at: CGPoint(x: x, y: bounds.minY + row.y), proposal: ProposedViewSize(s))
                x += s.width + spacing
            }
        }
    }

    private struct Row { var items: [Int] = []; var width: CGFloat = 0; var height: CGFloat = 0; var y: CGFloat = 0 }

    private func arrange(_ maxWidth: CGFloat, _ subviews: Subviews) -> [Row] {
        var rows = [Row()]
        for (i, v) in subviews.enumerated() {
            let s = v.sizeThatFits(.unspecified)
            if !rows[rows.count - 1].items.isEmpty && rows[rows.count - 1].width + spacing + s.width > maxWidth {
                let y = rows[rows.count - 1].y + rows[rows.count - 1].height + spacing
                rows.append(Row(y: y))
            }
            var r = rows[rows.count - 1]
            r.width += (r.items.isEmpty ? 0 : spacing) + s.width
            r.height = max(r.height, s.height)
            r.items.append(i)
            rows[rows.count - 1] = r
        }
        return rows
    }
}

/// Progress bar; dashed and empty when the value is unknown.
struct MeterBar: View {
    let value: Double?

    var body: some View {
        Group {
            if let value {
                Capsule().fill(Theme.muted).overlay(alignment: .leading) {
                    GeometryReader { g in Capsule().fill(Theme.foreground).frame(width: g.size.width * min(max(value, 0), 1)) }
                }
            } else {
                Capsule().stroke(Theme.unknownBorder, style: Theme.dash)
            }
        }
        .frame(height: 8)
        .accessibilityHidden(true)
    }
}

/// Score ring 0–100 in black/grey (green stays for «Candidati»).
struct ScoreRing: View {
    let value: Int
    var size: CGFloat = 72

    var body: some View {
        ZStack {
            Circle().stroke(Theme.muted, lineWidth: 7)
            Circle().trim(from: 0, to: CGFloat(value) / 100)
                .stroke(Theme.foreground, style: StrokeStyle(lineWidth: 7, lineCap: .round))
                .rotationEffect(.degrees(-90))
            Text("\(value)").font(.system(.title2, design: .monospaced).weight(.semibold)).foregroundStyle(Theme.foreground)
        }
        .frame(width: size, height: size)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Punteggio \(value) su 100")
    }
}

/// Status banner (AI not configured, analyses running, errors).
struct Banner: View {
    enum Kind { case warning, info, error }
    let kind: Kind
    let text: String
    var action: (label: String, run: () -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            if kind == .info { ProgressView().controlSize(.small) } else {
                Image(systemName: kind == .error ? "exclamationmark.triangle" : "exclamationmark.circle")
            }
            Text(text).font(.subheadline).frame(maxWidth: .infinity, alignment: .leading)
            if let action {
                Button(action.label, action: action.run).font(.subheadline.weight(.semibold)).frame(minHeight: 44)
            }
        }
        .padding(.horizontal, 14).padding(.vertical, 10)
        .foregroundStyle(kind == .warning ? Theme.valutaForeground : kind == .error ? Theme.destructive : Theme.mutedForeground)
        .background(kind == .warning ? Theme.valuta : kind == .error ? Theme.destructiveSoft : Theme.muted, in: .rect(cornerRadius: 14))
        .accessibilityElement(children: .combine)
    }
}

/// Empty / error state: round icon, title, text, optional button.
struct EmptyState: View {
    let icon: String
    let title: String
    let text: String
    var action: (label: String, run: () -> Void)?

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon).font(.title3).foregroundStyle(Theme.mutedForeground)
                .frame(width: 48, height: 48).background(Theme.muted, in: .circle)
            Text(title).font(.headline).foregroundStyle(Theme.foreground)
            Text(text).font(.subheadline).foregroundStyle(Theme.mutedForeground).multilineTextAlignment(.center)
            if let action {
                Button(action.label, action: action.run).buttonStyle(.borderedProminent).foregroundStyle(Theme.primaryForeground).buttonBorderShape(.capsule).frame(minHeight: 44)
            }
        }
        .padding(24).frame(maxWidth: .infinity)
        .accessibilityElement(children: .contain)
    }
}

/// Bottom toast: red for errors, otherwise neutral with «Annulla». Announced to VoiceOver by the Store.
struct ToastView: View {
    let toast: Store.Toast
    let dismiss: () -> Void
    @Environment(Store.self) private var store

    var body: some View {
        HStack(spacing: 12) {
            if toast.isError { Image(systemName: "exclamationmark.triangle") }
            Text(toast.text).font(.subheadline)
            Spacer(minLength: 0)
            if let undo = toast.undo {
                Button("Annulla") { undo(); dismiss() }.font(.subheadline.bold()).frame(minHeight: 44)
            }
        }
        .padding(.horizontal, 16).frame(minHeight: 48)
        .foregroundStyle(toast.isError ? Color.white : Theme.background)
        .background(toast.isError ? Theme.destructive : Theme.foreground, in: .capsule)
        .padding(.horizontal, 16).padding(.bottom, 8)
        .task(id: toast.id) {
            try? await Task.sleep(for: .seconds(toast.undo == nil ? 4 : 6))
            // Not while a request is still running: its error would replace this toast anyway.
            while store.inFlight > 0 { try? await Task.sleep(for: .milliseconds(300)) }
            dismiss()
        }
    }
}

extension URL: @retroactive Identifiable { public var id: String { absoluteString } }

extension View {
    /// Card frame used by detail components: white, r16, thin border, dashed when unknown.
    func panel(dashed: Bool = false) -> some View {
        padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.card, in: .rect(cornerRadius: 16))
            .overlay {
                RoundedRectangle(cornerRadius: 16).stroke(dashed ? Theme.unknownBorder : Theme.border, style: dashed ? Theme.dash : StrokeStyle(lineWidth: 1))
            }
    }

    func sectionLabel() -> some View {
        font(.caption2.weight(.semibold)).textCase(.uppercase).foregroundStyle(Theme.mutedForeground).accessibilityAddTraits(.isHeader)
    }
}
