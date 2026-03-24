import SwiftUI

struct ResultsView: View {
    let analysis: EthicalAnalysis
    let decision: String
    let context: [String: String]

    @EnvironmentObject var authState: AuthState
    @Environment(\.dismiss) var dismiss

    @State private var expandedFramework: String? = nil
    @State private var animateConfidence = false
    @State private var isGeneratingPDF = false
    @State private var pdfData: Data?
    @State private var showShareSheet = false
    @State private var errorMessage: String?

    private let frameworks: [(id: String, label: String, color: Color, text: String)] = []

    var body: some View {
        NavigationStack {
            ZStack {
                BackgroundView()
                ScrollView {
                    VStack(spacing: 14) {

                        // Header row
                        HStack {
                            Text("Analysis")
                                .font(.system(size: 22, weight: .bold))
                                .foregroundColor(.white)
                            Spacer()
                            ProviderBadge(provider: analysis.provider)
                        }
                        .padding(.top, 8)

                        // Framework cards (accordion)
                        frameworkCard(
                            id: "kantian",
                            label: "Kantian Ethics",
                            icon: "scale.3d",
                            color: Color(red: 0.65, green: 0.55, blue: 0.98),
                            text: analysis.kantianAnalysis
                        )
                        frameworkCard(
                            id: "utilitarian",
                            label: "Utilitarianism",
                            icon: "chart.bar.fill",
                            color: Color(red: 0.51, green: 0.55, blue: 0.97),
                            text: analysis.utilitarianAnalysis
                        )
                        frameworkCard(
                            id: "virtue",
                            label: "Virtue Ethics",
                            icon: "heart.fill",
                            color: Color(red: 0.75, green: 0.52, blue: 0.99),
                            text: analysis.virtueEthicsAnalysis
                        )

                        // Risk flags
                        GlassCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Label("Risk Detection", systemImage: "exclamationmark.triangle.fill")
                                    .font(.system(size: 11, weight: .semibold))
                                    .tracking(1.1)
                                    .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))

                                if analysis.riskFlags.isEmpty {
                                    Label("No significant risks detected", systemImage: "checkmark.circle.fill")
                                        .font(.system(size: 14))
                                        .foregroundColor(Color(red: 0.2, green: 0.83, blue: 0.6))
                                } else {
                                    FlowLayout(spacing: 8) {
                                        ForEach(analysis.riskFlags, id: \.self) { flag in
                                            Text(flag.replacingOccurrences(of: "_", with: " ").uppercased())
                                                .font(.system(size: 10, weight: .bold))
                                                .tracking(0.7)
                                                .foregroundColor(Color(red: 0.99, green: 0.64, blue: 0.64))
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 5)
                                                .background(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.14))
                                                .clipShape(Capsule())
                                                .overlay(Capsule().stroke(Color(red: 0.97, green: 0.44, blue: 0.44).opacity(0.25)))
                                        }
                                    }
                                }
                            }
                        }

                        // Confidence
                        GlassCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("CONFIDENCE SCORE")
                                    .font(.system(size: 11, weight: .semibold))
                                    .tracking(1.1)
                                    .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))

                                HStack(spacing: 14) {
                                    Text("\(Int(analysis.confidenceScore * 100))%")
                                        .font(.system(size: 32, weight: .bold))
                                        .foregroundStyle(
                                            LinearGradient(
                                                colors: [Color(red: 0.65, green: 0.55, blue: 0.98), Color(red: 0.51, green: 0.55, blue: 0.97)],
                                                startPoint: .leading, endPoint: .trailing
                                            )
                                        )

                                    GeometryReader { geo in
                                        ZStack(alignment: .leading) {
                                            RoundedRectangle(cornerRadius: 99)
                                                .fill(.white.opacity(0.1))
                                                .frame(height: 8)
                                            RoundedRectangle(cornerRadius: 99)
                                                .fill(
                                                    LinearGradient(
                                                        colors: [Color(red: 0.49, green: 0.23, blue: 0.93), Color(red: 0.51, green: 0.55, blue: 0.97)],
                                                        startPoint: .leading, endPoint: .trailing
                                                    )
                                                )
                                                .frame(
                                                    width: animateConfidence ? geo.size.width * analysis.confidenceScore : 0,
                                                    height: 8
                                                )
                                                .shadow(color: Color(red: 0.51, green: 0.55, blue: 0.97).opacity(0.6), radius: 4)
                                        }
                                    }
                                    .frame(height: 8)
                                }
                            }
                        }
                        .onAppear {
                            withAnimation(.easeOut(duration: 1.0).delay(0.3)) {
                                animateConfidence = true
                            }
                        }

                        // Recommendation
                        GlassCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Label("Recommendation", systemImage: "lightbulb.fill")
                                    .font(.system(size: 11, weight: .semibold))
                                    .tracking(1.1)
                                    .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))

                                Text(analysis.recommendation)
                                    .font(.system(size: 14))
                                    .foregroundColor(.white.opacity(0.85))
                                    .lineSpacing(5)
                            }
                        }

                        // Error
                        if let err = errorMessage {
                            Text(err)
                                .font(.system(size: 13))
                                .foregroundColor(Color(red: 0.99, green: 0.64, blue: 0.64))
                                .multilineTextAlignment(.center)
                        }

                        // Download PDF
                        Button(action: downloadPDF) {
                            HStack(spacing: 8) {
                                if isGeneratingPDF {
                                    ProgressView().tint(.white).scaleEffect(0.85)
                                    Text("Generating PDF…")
                                } else {
                                    Image(systemName: "arrow.down.doc.fill")
                                    Text("Download PDF Report")
                                }
                            }
                            .font(.system(size: 16, weight: .semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .foregroundColor(.white)
                            .background(
                                LinearGradient(
                                    colors: [Color(red: 0.02, green: 0.59, blue: 0.41), Color(red: 0.06, green: 0.72, blue: 0.51)],
                                    startPoint: .leading, endPoint: .trailing
                                )
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 14))
                            .shadow(color: Color(red: 0.06, green: 0.72, blue: 0.51).opacity(0.4), radius: 12, y: 4)
                            .opacity(isGeneratingPDF ? 0.6 : 1)
                        }
                        .disabled(isGeneratingPDF)

                        Spacer(minLength: 40)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 16)
                }
            }
            .navigationTitle("Results")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(Color(red: 0.65, green: 0.55, blue: 0.98))
                        .fontWeight(.semibold)
                }
            }
            .sheet(isPresented: $showShareSheet) {
                if let pdf = pdfData {
                    ShareSheet(items: [pdf])
                }
            }
        }
    }

    // MARK: - Framework accordion card

    @ViewBuilder
    func frameworkCard(id: String, label: String, icon: String, color: Color, text: String) -> some View {
        let isOpen = expandedFramework == id
        VStack(spacing: 0) {
            Button {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    expandedFramework = isOpen ? nil : id
                }
            } label: {
                HStack {
                    Label(label, systemImage: icon)
                        .font(.system(size: 11, weight: .bold))
                        .tracking(1.0)
                        .foregroundColor(color)
                    Spacer()
                    Image(systemName: "chevron.down")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.white.opacity(0.4))
                        .rotationEffect(.degrees(isOpen ? 180 : 0))
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 18)
            }
            .buttonStyle(.plain)

            if isOpen {
                Divider().background(.white.opacity(0.1)).padding(.horizontal, 16)
                Text(text)
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.82))
                    .lineSpacing(5)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .background(.white.opacity(0.1))
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 20))
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(.white.opacity(0.2)))
        .shadow(color: .black.opacity(0.2), radius: 10, y: 4)
    }

    // MARK: - PDF download

    func downloadPDF() {
        guard let token = authState.token else { return }
        isGeneratingPDF = true
        errorMessage = nil
        Task {
            do {
                let data = try await APIService.shared.generateReport(
                    decision: decision, context: context, analysis: analysis, token: token
                )
                await MainActor.run {
                    self.pdfData = data
                    self.isGeneratingPDF = false
                    self.showShareSheet = true
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = "Could not generate PDF: \(error.localizedDescription)"
                    self.isGeneratingPDF = false
                }
            }
        }
    }
}

// MARK: - Provider badge

struct ProviderBadge: View {
    let provider: String
    var color: Color {
        switch provider {
        case "claude":  return Color(red: 0.65, green: 0.55, blue: 0.98)
        case "openai":  return Color(red: 0.2, green: 0.83, blue: 0.6)
        default:        return .white.opacity(0.4)
        }
    }
    var body: some View {
        Text(provider.uppercased())
            .font(.system(size: 10, weight: .bold))
            .tracking(1)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
            .overlay(Capsule().stroke(color.opacity(0.3)))
    }
}

// MARK: - Flow layout (wrapping chips)

struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) -> CGSize {
        let width = proposal.width ?? .infinity
        var height: CGFloat = 0; var rowWidth: CGFloat = 0; var rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if rowWidth + size.width > width && rowWidth > 0 {
                height += rowHeight + spacing; rowWidth = 0; rowHeight = 0
            }
            rowWidth += size.width + spacing; rowHeight = max(rowHeight, size.height)
        }
        height += rowHeight
        return CGSize(width: width, height: height)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) {
        var x = bounds.minX; var y = bounds.minY; var rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX && x > bounds.minX {
                y += rowHeight + spacing; x = bounds.minX; rowHeight = 0
            }
            view.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing; rowHeight = max(rowHeight, size.height)
        }
    }
}

// MARK: - Share sheet

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}
