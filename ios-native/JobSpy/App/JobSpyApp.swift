import SwiftUI

/// Launch arguments for screenshots (xcrun simctl launch … -uiTab 2 -uiJob <url> …), see README.
enum UIArgs {
    static let d = UserDefaults.standard
    static var tab: Int { d.integer(forKey: "uiTab") }
    static var job: String? { d.string(forKey: "uiJob") }
    static var detailTab: String? { d.string(forKey: "uiDetailTab") }
    static var sheet: String? { d.string(forKey: "uiSheet") }
    static var saved: Int { d.integer(forKey: "uiSaved") }
    static var screen: String? { d.string(forKey: "uiScreen") }
    static var search: String? { d.string(forKey: "uiSearch") }
}

@main
struct JobSpyApp: App {
    @State private var store = Store()
    @State private var tab = UIArgs.tab
    @Environment(\.scenePhase) private var phase

    var body: some Scene {
        WindowGroup {
            TabView(selection: $tab) {
                Tab("Feed", systemImage: "rectangle.stack", value: 0) { NavigationStack { FeedView() } }
                    .badge(store.feed(channel: nil).filter(\.isNew).count)
                Tab("Preferiti", systemImage: "bookmark", value: 1) { NavigationStack { SavedView() } }
                Tab("Candidature", systemImage: "paperplane", value: 2) { NavigationStack { ApplicationsView() } }
                    .badge(store.applicationRows.filter { $0.app.isDue() }.count)
                Tab("CV", systemImage: "doc.text", value: 3) { NavigationStack { CvListView() } }
                Tab("Cerca", systemImage: "magnifyingglass", value: 4, role: .search) { NavigationStack { SearchView() } }
            }
            .tint(Theme.primary)
            .environment(store)
            .overlay(alignment: .bottom) {
                if let t = store.toast {
                    ToastView(toast: t) { if store.toast?.id == t.id { store.toast = nil } }
                        .padding(.bottom, 56)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .animation(.snappy, value: store.toast?.id)
            .task { await store.loadAll() }
            .onChange(of: phase) { _, p in if p == .active { Task { await store.reloadIfStale() } } }
        }
    }
}
