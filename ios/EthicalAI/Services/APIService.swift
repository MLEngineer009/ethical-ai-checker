import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case serverError(String)
    case unauthorized
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidURL:       return "Invalid URL"
        case .serverError(let m): return m
        case .unauthorized:     return "Session expired. Please sign in again."
        case .unknown:          return "Something went wrong. Please try again."
        }
    }
}

class APIService {
    static let shared = APIService()

    // Update this to your Mac's IP when testing on a real device
    // e.g. "http://192.168.1.100:8000"
    let baseURL = "http://localhost:8000"

    private let session = URLSession.shared

    // MARK: - Generic request

    private func request<T: Decodable>(
        _ path: String,
        method: String = "GET",
        body: Encodable? = nil,
        token: String? = nil
    ) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let t = token { req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization") }
        if let body { req.httpBody = try JSONEncoder().encode(body) }

        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw APIError.unknown }

        if http.statusCode == 401 { throw APIError.unauthorized }
        if http.statusCode >= 400 {
            let msg = (try? JSONDecoder().decode([String: String].self, from: data))?["detail"] ?? "Error \(http.statusCode)"
            throw APIError.serverError(msg)
        }

        let decoder = JSONDecoder()
        return try decoder.decode(T.self, from: data)
    }

    // MARK: - Auth

    func googleAuth(credential: String) async throws -> AuthResponse {
        try await request("/auth/google", method: "POST", body: GoogleAuthRequest(credential: credential))
    }

    func guestAuth() async throws -> AuthResponse {
        try await request("/auth/guest", method: "POST")
    }

    func logout(token: String) async throws {
        let _: [String: Bool] = try await request("/logout", method: "POST", token: token)
    }

    func me(token: String) async throws -> [String: String] {
        try await request("/me", token: token)
    }

    // MARK: - Decision

    func evaluate(decision: String, context: [String: String], token: String) async throws -> EthicalAnalysis {
        let body = DecisionRequest(decision: decision, context: context)
        return try await request("/evaluate-decision", method: "POST", body: body, token: token)
    }

    func generateReport(decision: String, context: [String: String], analysis: EthicalAnalysis, token: String) async throws -> Data {
        guard let url = URL(string: baseURL + "/generate-report") else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let body = ["decision": decision, "context": context, "analysis": analysis] as [String: Any]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw APIError.unknown }
        if http.statusCode >= 400 { throw APIError.serverError("Report generation failed") }
        return data
    }

    // MARK: - Stats

    func myStats(token: String) async throws -> UserStats {
        try await request("/my-stats", token: token)
    }
}
