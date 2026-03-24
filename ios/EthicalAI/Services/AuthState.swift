import Foundation
import Combine

class AuthState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var userName: String = ""
    @Published var userPicture: String = ""
    @Published var isGuest: Bool = false

    private(set) var token: String? {
        get { UserDefaults.standard.string(forKey: "auth_token") }
        set {
            if let v = newValue { UserDefaults.standard.set(v, forKey: "auth_token") }
            else { UserDefaults.standard.removeObject(forKey: "auth_token") }
        }
    }

    init() {
        restoreSession()
    }

    func signIn(token: String, name: String, picture: String, guest: Bool = false) {
        self.token       = token
        self.userName    = name
        self.userPicture = picture
        self.isGuest     = guest
        // Persist non-guest sessions
        if !guest {
            UserDefaults.standard.set(name,    forKey: "user_name")
            UserDefaults.standard.set(picture, forKey: "user_picture")
        }
        isAuthenticated = true
    }

    func signOut() {
        token = nil
        userName    = ""
        userPicture = ""
        isGuest     = false
        UserDefaults.standard.removeObject(forKey: "user_name")
        UserDefaults.standard.removeObject(forKey: "user_picture")
        isAuthenticated = false
    }

    private func restoreSession() {
        // Guest sessions are ephemeral — never restored
        guard let savedToken = token,
              let savedName  = UserDefaults.standard.string(forKey: "user_name") else { return }
        let savedPic = UserDefaults.standard.string(forKey: "user_picture") ?? ""
        Task {
            do {
                // Validate token with /me
                let _ = try await APIService.shared.me(token: savedToken)
                await MainActor.run {
                    self.token       = savedToken
                    self.userName    = savedName
                    self.userPicture = savedPic
                    self.isGuest     = false
                    self.isAuthenticated = true
                }
            } catch {
                await MainActor.run { self.signOut() }
            }
        }
    }
}
