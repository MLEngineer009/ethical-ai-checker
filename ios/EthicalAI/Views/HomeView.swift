import SwiftUI

struct HomeView: View {
    @EnvironmentObject var authState: AuthState
    @State private var decision = ""
    @State private var contextFields: [ContextField] = [
        ContextField(key: "gender", value: ""),
        ContextField(key: "experience", value: ""),
        ContextField(key: "", value: ""),
    ]
    @State private var isEvaluating = false
    @State private var analysis: EthicalAnalysis?
    @State private var errorMessage: String?
    @State private var showResults = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {

                    // User bar
                    UserBarView()

                    // Header
                    VStack(spacing: 6) {
                        Text("⚖️")
                            .font(.system(size: 42))
                            .shadow(color: Color(red: 0.65, green: 0.55, blue: 0.98).opacity(0.6), radius: 16)
                        Text("Ethical AI")
                            .font(.system(size: 28, weight: .bold))
                            .foregroundStyle(accentGradient)
                        Text("AI-powered ethical reasoning & risk detection")
                            .font(.system(size: 13))
                            .foregroundColor(.white.opacity(0.5))
                    }
                    .padding(.top, 8)

                    // Decision input
                    GlassCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Label("Decision", systemImage: "text.alignleft")
                                .font(.system(size: 11, weight: .semibold))
                                .tracking(1.1)
                                .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))

                            TextEditor(text: $decision)
                                .font(.system(size: 15))
                                .foregroundColor(.white)
                                .frame(minHeight: 90)
                                .scrollContentBackground(.hidden)
                                .background(Color.white.opacity(0.06))
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 10)
                                        .stroke(.white.opacity(0.14))
                                )
                                .overlay(alignment: .topLeading) {
                                    if decision.isEmpty {
                                        Text("Describe the decision being evaluated…")
                                            .font(.system(size: 15))
                                            .foregroundColor(.white.opacity(0.3))
                                            .padding(.horizontal, 8)
                                            .padding(.top, 8)
                                            .allowsHitTesting(false)
                                    }
                                }
                        }
                    }

                    // Context input
                    GlassCard {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Label("Context", systemImage: "list.bullet")
                                    .font(.system(size: 11, weight: .semibold))
                                    .tracking(1.1)
                                    .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))
                                Spacer()
                                Button {
                                    contextFields.append(ContextField())
                                } label: {
                                    HStack(spacing: 4) {
                                        Image(systemName: "plus")
                                        Text("Add Field")
                                    }
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 6)
                                    .background(Color(red: 0.65, green: 0.55, blue: 0.98).opacity(0.12))
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 8)
                                            .stroke(Color(red: 0.65, green: 0.55, blue: 0.98).opacity(0.3), style: StrokeStyle(lineWidth: 1, dash: [4]))
                                    )
                                }
                            }

                            ForEach($contextFields) { $field in
                                HStack(spacing: 8) {
                                    ContextTextField(text: $field.key, placeholder: "Field name", isKey: true)
                                    ContextTextField(text: $field.value, placeholder: "Value", isKey: false)
                                    if contextFields.count > 1 {
                                        Button {
                                            contextFields.removeAll { $0.id == field.id }
                                        } label: {
                                            Image(systemName: "minus.circle.fill")
                                                .foregroundColor(.white.opacity(0.25))
                                                .font(.system(size: 18))
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Error
                    if let err = errorMessage {
                        HStack(spacing: 8) {
                            Image(systemName: "exclamationmark.circle.fill")
                            Text(err)
                                .font(.system(size: 14, weight: .medium))
                        }
                        .foregroundColor(Color(red: 0.99, green: 0.64, blue: 0.64))
                        .frame(maxWidth: .infinity)
                        .padding(14)
                        .background(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.15))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.35)))
                    }

                    // Evaluate button
                    Button(action: evaluate) {
                        HStack(spacing: 8) {
                            if isEvaluating {
                                ProgressView().tint(.white).scaleEffect(0.85)
                                Text("Analysing…")
                            } else {
                                Image(systemName: "brain.head.profile")
                                Text("Evaluate Decision")
                            }
                        }
                        .font(.system(size: 16, weight: .semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .foregroundColor(.white)
                        .background(
                            LinearGradient(
                                colors: [Color(red: 0.49, green: 0.23, blue: 0.93), Color(red: 0.31, green: 0.28, blue: 0.90)],
                                startPoint: .leading, endPoint: .trailing
                            )
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                        .shadow(color: Color(red: 0.49, green: 0.23, blue: 0.93).opacity(0.45), radius: 12, y: 4)
                        .opacity(isEvaluating ? 0.6 : 1)
                    }
                    .disabled(isEvaluating)

                    Spacer(minLength: 40)
                }
                .padding(.horizontal, 20)
                .padding(.top, 60)
            }
        }
        .sheet(isPresented: $showResults) {
            if let analysis {
                ResultsView(analysis: analysis, decision: decision, context: buildContext())
            }
        }
    }

    // MARK: - Helpers

    var accentGradient: LinearGradient {
        LinearGradient(
            colors: [
                Color(red: 0.88, green: 0.84, blue: 1.0),
                Color(red: 0.65, green: 0.55, blue: 0.98),
                Color(red: 0.51, green: 0.55, blue: 0.97),
            ],
            startPoint: .topLeading, endPoint: .bottomTrailing
        )
    }

    func buildContext() -> [String: String] {
        var ctx: [String: String] = [:]
        for field in contextFields {
            let k = field.key.trimmingCharacters(in: .whitespaces)
            let v = field.value.trimmingCharacters(in: .whitespaces)
            if !k.isEmpty && !v.isEmpty { ctx[k] = v }
        }
        return ctx
    }

    func evaluate() {
        let trimmed = decision.trimmingCharacters(in: .whitespacesAndNewlines)
        let context = buildContext()
        guard !trimmed.isEmpty else { errorMessage = "Please enter a decision."; return }
        guard !context.isEmpty else { errorMessage = "Please fill in at least one context field."; return }
        guard let token = authState.token else { return }

        errorMessage = nil
        isEvaluating = true

        Task {
            do {
                let result = try await APIService.shared.evaluate(decision: trimmed, context: context, token: token)
                await MainActor.run {
                    self.analysis = result
                    self.isEvaluating = false
                    self.showResults = true
                }
            } catch APIError.unauthorized {
                await MainActor.run {
                    self.isEvaluating = false
                    self.authState.signOut()
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = error.localizedDescription
                    self.isEvaluating = false
                }
            }
        }
    }
}

// MARK: - Supporting views

struct GlassCard<Content: View>: View {
    @ViewBuilder let content: Content
    var body: some View {
        content
            .padding(22)
            .background(.white.opacity(0.1))
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).stroke(.white.opacity(0.2)))
            .shadow(color: .black.opacity(0.25), radius: 12, y: 4)
    }
}

struct ContextTextField: View {
    @Binding var text: String
    let placeholder: String
    let isKey: Bool

    var body: some View {
        TextField(placeholder, text: $text)
            .font(.system(size: 14, weight: isKey ? .semibold : .regular))
            .foregroundColor(isKey ? Color(red: 0.65, green: 0.55, blue: 0.98) : .white)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(.white.opacity(0.07))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(.white.opacity(0.14)))
            .autocorrectionDisabled()
            .textInputAutocapitalization(.never)
    }
}

struct UserBarView: View {
    @EnvironmentObject var authState: AuthState

    var body: some View {
        HStack {
            HStack(spacing: 8) {
                AsyncImage(url: URL(string: authState.userPicture)) { img in
                    img.resizable().scaledToFill()
                } placeholder: {
                    Image(systemName: "person.circle.fill").foregroundColor(.white.opacity(0.4))
                }
                .frame(width: 26, height: 26)
                .clipShape(Circle())

                Text(authState.userName)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))

                if authState.isGuest {
                    Text("Guest")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(0.8)
                        .foregroundColor(Color(red: 0.98, green: 0.75, blue: 0.14))
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(Color(red: 0.98, green: 0.75, blue: 0.14).opacity(0.12))
                        .clipShape(Capsule())
                        .overlay(Capsule().stroke(Color(red: 0.98, green: 0.75, blue: 0.14).opacity(0.25)))
                }
            }

            Spacer()

            Button("Sign Out") {
                authState.signOut()
            }
            .font(.system(size: 12, weight: .semibold))
            .foregroundColor(Color(red: 0.99, green: 0.64, blue: 0.64))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.25)))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.white.opacity(0.08))
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(.white.opacity(0.18)))
    }
}
