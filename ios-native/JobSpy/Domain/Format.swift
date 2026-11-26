import Foundation

/// Port of webapp/frontend/src/lib/format.ts. Calendar reasoning ("oggi", "ieri") is in Europe/Rome.
nonisolated enum Fmt {
    static let rome = TimeZone(identifier: "Europe/Rome")!
    static var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = rome
        return c
    }

    private static let sqlite: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return f
    }()

    /// Backend timestamps: bare "YYYY-MM-DD HH:MM:SS" is UTC (SQLite); ISO 8601 with or without fractions.
    static func date(_ value: String?) -> Date? {
        guard let value, !value.isEmpty else { return nil }
        if let d = sqlite.date(from: value) { return d }
        if let d = try? Date(value, strategy: .iso8601) { return d }
        if let d = try? Date(value, strategy: Date.ISO8601FormatStyle(includingFractionalSeconds: true)) { return d }
        return day(value)
    }

    /// A calendar day "YYYY-MM-DD" at midnight in Europe/Rome.
    static func day(_ value: String?) -> Date? {
        guard let value, value.count >= 10 else { return nil }
        let parts = value.prefix(10).split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        return calendar.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2]))
    }

    static func isDateOnly(_ value: String) -> Bool { value.count == 10 && value.filter { $0 == "-" }.count == 2 }

    /// Today as "YYYY-MM-DD" in Europe/Rome.
    static func today(_ now: Date = .now) -> String {
        let c = calendar.dateComponents([.year, .month, .day], from: now)
        return String(format: "%04d-%02d-%02d", c.year!, c.month!, c.day!)
    }

    /// "oggi", "ieri", "3 giorni fa"; minutes/hours only when the value has a time.
    static func ago(_ value: String?, now: Date = .now) -> String {
        guard let value, !value.isEmpty else { return "" }
        if isDateOnly(value) {
            guard let d = day(value) else { return value }
            let days = calendar.dateComponents([.day], from: d, to: calendar.startOfDay(for: now)).day ?? 0
            return days <= 0 ? "oggi" : days == 1 ? "ieri" : "\(days) giorni fa"
        }
        guard let d = date(value) else { return value }
        let mins = Int(now.timeIntervalSince(d) / 60)
        if mins < 1 { return "adesso" }
        if mins < 60 { return "\(mins) min fa" }
        let hrs = mins / 60
        if hrs < 24 { return "\(hrs) \(hrs == 1 ? "ora" : "ore") fa" }
        let days = hrs / 24
        return days == 1 ? "ieri" : "\(days) giorni fa"
    }

    /// Whole days before a job without a verdict leaves the feed (can be <= 0).
    static func daysLeftInFeed(_ firstSeen: String?, feedDays: Int, now: Date = .now) -> Int? {
        guard let d = date(firstSeen) else { return nil }
        return Int((d.addingTimeInterval(Double(feedDays) * 86_400).timeIntervalSince(now) / 86_400).rounded(.up))
    }

    /// Calendar days from today to a "YYYY-MM-DD" (negative = past).
    static func daysUntil(_ value: String?, now: Date = .now) -> Int? {
        guard let d = day(value) else { return nil }
        return calendar.dateComponents([.day], from: calendar.startOfDay(for: now), to: d).day
    }

    /// "16/12/2026" for a calendar day, "—" when missing.
    static func dayLabel(_ value: String?) -> String {
        guard let d = day(value) else { return "—" }
        return d.formatted(Date.FormatStyle(date: .numeric, time: .omitted, locale: Locale(identifier: "it_IT"), timeZone: rome))
    }

    /// Compact salary label, e.g. "40–48k €".
    static func salary(_ job: Job) -> String? {
        let lo = job.salary_min?.value ?? 0, hi = job.salary_max?.value ?? 0
        if lo == 0 && hi == 0 { return nil }
        let sym = job.salary_currency == "USD" ? "$" : job.salary_currency == "GBP" ? "£" : "€"
        func k(_ n: Double) -> String { n >= 1000 ? "\(Int((n / 1000).rounded()))k" : "\(Int(n.rounded()))" }
        if lo != 0 && hi != 0 && lo != hi { return "\(k(lo).replacingOccurrences(of: "k", with: ""))–\(k(hi)) \(sym)" }
        return "\(k(lo != 0 ? lo : hi)) \(sym)"
    }

    /// The comma/JSON-ish skills string as a tidy list.
    static func skills(_ raw: String?) -> [String] {
        guard let raw = raw?.trimmingCharacters(in: .whitespaces), !raw.isEmpty else { return [] }
        if let data = raw.data(using: .utf8), let arr = try? JSONSerialization.jsonObject(with: data) as? [Any] {
            return arr.map { "\($0)" }
        }
        return raw.split(whereSeparator: { $0 == "," || $0 == ";" }).map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
    }

    static let siteLabels: [String: String] = [
        "linkedin": "LinkedIn", "indeed": "Indeed", "glassdoor": "Glassdoor", "google": "Google", "remotive": "Remotive",
        "remoteok": "RemoteOK", "weworkremotely": "We Work Remotely", "workingnomads": "Working Nomads",
        "subito": "Subito Lavoro", "inpa": "inPA · Pubblica Amministrazione", "freehire": "freehire",
    ]

    static func site(_ site: String?) -> String {
        guard let site, !site.isEmpty else { return "" }
        return siteLabels[site.lowercased()] ?? site.prefix(1).uppercased() + site.dropFirst()
    }

    /// Two letters from the first two words: "Azienda Esempio Srl" -> "AE".
    static func monogram(_ name: String?) -> String {
        let cleaned = (name ?? "").unicodeScalars.map { CharacterSet.letters.union(.decimalDigits).contains($0) ? Character($0) : " " }
        let words = String(cleaned).split(separator: " ")
        let s = words.prefix(2).compactMap(\.first).map(String.init).joined()
        return s.isEmpty ? "?" : s.uppercased()
    }

    static let remoteScope: [String: String] = [
        "italy": "Remoto dall’Italia", "eu": "Remoto UE", "worldwide": "Remoto ovunque", "restricted": "Remoto solo da altri paesi",
    ]
    static let seniority: [String: String] = ["junior": "Junior", "mid": "Mid", "senior": "Senior", "lead": "Lead"]
}
