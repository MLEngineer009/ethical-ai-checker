import SwiftUI
import GoogleSignIn

struct AuthView: View {
    @EnvironmentObject var authState: AuthState
    @State private var isLoading = false
    @State private var errorMessage: String?

    // Replace with your actual Google Client ID
    private let googleClientID = "YOUR_GOOGLE_CLIENT_ID_HERE"

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                Spacer().frame(height: 100)

                // Icon + title
                VStack(spacing: 12) {
                    Text("⚖️")
                        .font(.system(size: 64))
                        .shadow(color: Color(red: 0.65, green: 0.55, blue: 0.98).opacity(0.6), radius: 20)

                    Text("Ethical AI")
                        .font(.system(size: 34, weight: .bold, design: .default))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.88, green: 0.84, blue: 1.0),
                                    Color(red: 0.65, green: 0.55, blue: 0.98),
                                    Color(red: 0.51, green: 0.55, blue: 0.97),
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )

                    Text("AI-powered ethical reasoning & risk detection")
                        .font(.system(size: 14))
                        .foregroundColor(.white.opacity(0.55))
                        .multilineTextAlignment(.center)
                }
                .padding(.bottom, 48)

                // Glass card
                VStack(spacing: 20) {
                    Text("SIGN IN TO CONTINUE")
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(1.2)
                        .foregroundColor(.white.opacity(0.45))

                    // Error
                    if let err = errorMessage {
                        HStack {
                            Image(systemName: "exclamationmark.circle.fill")
                            Text(err)
                                .font(.system(size: 13, weight: .medium))
                        }
                        .foregroundColor(Color(red: 0.99, green: 0.64, blue: 0.64))
                        .padding(12)
                        .background(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.15))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.35))
                        )
                    }

                    // Google Sign-In button
                    Button(action: signInWithGoogle) {
                        HStack(spacing: 10) {
                            if isLoading {
                                ProgressView()
                                    .tint(.white)
                                    .scaleEffect(0.85)
                            } else {
                                Image(systemName: "person.crop.circle.badge.checkmark")
                                    .font(.system(size: 18))
                            }
                            Text(isLoading ? "Signing in…" : "Continue with Google")
                                .font(.system(size: 16, weight: .semibold))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.49, green: 0.23, blue: 0.93),
                                    Color(red: 0.31, green: 0.28, blue: 0.90),
                                ],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .foregroundColor(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                        .shadow(color: Color(red: 0.49, green: 0.23, blue: 0.93).opacity(0.45), radius: 12, y: 4)
                    }
                    .disabled(isLoading)

                    // Divider
                    HStack(spacing: 12) {
                        Rectangle().fill(.white.opacity(0.12)).frame(height: 1)
                        Text("OR").font(.system(size: 11, weight: .medium)).foregroundColor(.white.opacity(0.35))
                        Rectangle().fill(.white.opacity(0.12)).frame(height: 1)
                    }

                    // Guest button
                    Button(action: continueAsGuest) {
                        Text("Continue as Guest")
                            .font(.system(size: 15, weight: .medium))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .foregroundColor(.white.opacity(0.6))
                            .background(.white.opacity(0.07))
                            .clipShape(RoundedRectangle(cornerRadius: 14))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(.white.opacity(0.15))
                            )
                    }
                    .disabled(isLoading)

                    // Privacy note
                    Text("Your personal data is never stored.\nOnly anonymised usage metadata is logged.")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.3))
                        .multilineTextAlignment(.center)
                        .padding(.top, 4)
                }
                .padding(28)
                .background(.white.opacity(0.1))
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 24))
                .overlay(
                    RoundedRectangle(cornerRadius: 24)
                        .stroke(.white.opacity(0.2))
                )
                .shadow(color: .black.opacity(0.3), radius: 24, y: 8)
                .padding(.horizontal, 24)

                Spacer().frame(height: 60)
            }
        }
    }

    // MARK: - Actions

    private func signInWithGoogle() {
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let root = windowScene.windows.first?.rootViewController else { return }

        GIDSignIn.sharedInstance.configuration = GIDConfiguration(clientID: googleClientID)

        isLoading = true
        errorMessage = nil

        GIDSignIn.sharedInstance.signIn(withPresenting: root) { result, error in
            Task {
                if let error {
                    await MainActor.run {
                        self.errorMessage = error.localizedDescription
                        self.isLoading = false
                    }
                    return
                }
                guard let idToken = result?.user.idToken?.tokenString else {
                    await MainActor.run {
                        self.errorMessage = "Could not get Google ID token."
                        self.isLoading = false
                    }
                    return
                }
                do {
                    let auth = try await APIService.shared.googleAuth(credential: idToken)
                    await MainActor.run {
                        self.authState.signIn(
                            token: auth.token,
                            name: auth.name ?? "User",
                            picture: auth.picture ?? "",
                            guest: false
                        )
                        self.isLoading = false
                    }
                } catch {
                    await MainActor.run {
                        self.errorMessage = error.localizedDescription
                        self.isLoading = false
                    }
                }
            }
        }
    }

    private func continueAsGuest() {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                let auth = try await APIService.shared.guestAuth()
                await MainActor.run {
                    self.authState.signIn(token: auth.token, name: "Guest", picture: "", guest: true)
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = error.localizedDescription
                    self.isLoading = false
                }
            }
        }
    }
}
