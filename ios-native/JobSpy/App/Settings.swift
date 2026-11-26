import Foundation
import Security

/// Server URL in UserDefaults, API key in the Keychain (never in Info.plist or the binary in Release).
/// In Debug both can be prefilled from Config/Secrets.xcconfig (gitignored).
enum Settings {
    private static let urlKey = "serverURL"
    private static let service = "dev.intecha.jobspy"
    private static let account = "mobile-api-key"

    static var url: String {
        get {
            if let saved = UserDefaults.standard.string(forKey: urlKey) { return saved }
            #if DEBUG
            return Bundle.main.object(forInfoDictionaryKey: "JobSpyAPIURL") as? String ?? ""
            #else
            return ""
            #endif
        }
        set { UserDefaults.standard.set(newValue.trimmingCharacters(in: .whitespacesAndNewlines), forKey: urlKey) }
    }

    static var key: String {
        get {
            if let saved = Keychain.read(service: service, account: account) { return saved }
            #if DEBUG
            return Bundle.main.object(forInfoDictionaryKey: "JobSpyAPIKey") as? String ?? ""
            #else
            return ""
            #endif
        }
        set { Keychain.write(newValue.trimmingCharacters(in: .whitespacesAndNewlines), service: service, account: account) }
    }

    static var client: APIClient { APIClient(base: url, key: key) }
}

enum Keychain {
    static func read(service: String, account: String) -> String? {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                    kSecAttrAccount as String: account, kSecReturnData as String: true]
        var out: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    @discardableResult
    static func write(_ value: String, service: String, account: String) -> Bool {
        let base: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                   kSecAttrAccount as String: account]
        SecItemDelete(base as CFDictionary)
        guard !value.isEmpty else { return true }
        var add = base
        add[kSecValueData as String] = Data(value.utf8)
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        return SecItemAdd(add as CFDictionary, nil) == errSecSuccess
    }
}
