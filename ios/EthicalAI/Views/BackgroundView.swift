import SwiftUI

struct BackgroundView: View {
    @State private var animate = false

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.06, green: 0.05, blue: 0.16),
                    Color(red: 0.19, green: 0.17, blue: 0.39),
                    Color(red: 0.14, green: 0.14, blue: 0.24),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            // Orb 1 — purple
            Circle()
                .fill(Color(red: 0.49, green: 0.23, blue: 0.93).opacity(0.28))
                .frame(width: 460, height: 460)
                .blur(radius: 80)
                .offset(
                    x: animate ? -120 : -140,
                    y: animate ? -260 : -240
                )

            // Orb 2 — blue
            Circle()
                .fill(Color(red: 0.15, green: 0.39, blue: 0.92).opacity(0.22))
                .frame(width: 380, height: 380)
                .blur(radius: 70)
                .offset(
                    x: animate ? 160 : 140,
                    y: animate ? 320 : 340
                )

            // Orb 3 — pink
            Circle()
                .fill(Color(red: 0.86, green: 0.15, blue: 0.47).opacity(0.18))
                .frame(width: 280, height: 280)
                .blur(radius: 60)
                .offset(
                    x: animate ? 80 : 60,
                    y: animate ? 20 : 40
                )
        }
        .ignoresSafeArea()
        .onAppear {
            withAnimation(.easeInOut(duration: 8).repeatForever(autoreverses: true)) {
                animate = true
            }
        }
    }
}
