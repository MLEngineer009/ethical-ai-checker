import Foundation

// MARK: - Auth

struct AuthResponse: Codable {
    let token: String
    let name: String?
    let picture: String?
    let isGuest: Bool?

    enum CodingKeys: String, CodingKey {
        case token, name, picture
        case isGuest = "is_guest"
    }
}

struct GoogleAuthRequest: Codable {
    let credential: String
}

// MARK: - Decision

struct ContextField: Identifiable {
    var id = UUID()
    var key: String = ""
    var value: String = ""
}

struct DecisionRequest: Codable {
    let decision: String
    let context: [String: String]
}

struct EthicalAnalysis: Codable {
    let kantianAnalysis: String
    let utilitarianAnalysis: String
    let virtueEthicsAnalysis: String
    let riskFlags: [String]
    let confidenceScore: Double
    let recommendation: String
    let provider: String

    enum CodingKeys: String, CodingKey {
        case kantianAnalysis    = "kantian_analysis"
        case utilitarianAnalysis = "utilitarian_analysis"
        case virtueEthicsAnalysis = "virtue_ethics_analysis"
        case riskFlags          = "risk_flags"
        case confidenceScore    = "confidence_score"
        case recommendation
        case provider
    }
}

struct ReportRequest: Codable {
    let decision: String
    let context: [String: String]
    let analysis: EthicalAnalysis
}

// MARK: - Stats

struct RequestLog: Codable, Identifiable {
    var id: String { timestamp }
    let timestamp: String
    let contextKeys: [String]
    let decisionWords: Int
    let provider: String
    let confidence: Double
    let riskCount: Int
    let riskCategories: [String]

    enum CodingKeys: String, CodingKey {
        case timestamp
        case contextKeys    = "context_keys"
        case decisionWords  = "decision_words"
        case provider, confidence
        case riskCount      = "risk_count"
        case riskCategories = "risk_categories"
    }
}

struct UserStats: Codable {
    let totalRequests: Int
    let history: [RequestLog]

    enum CodingKeys: String, CodingKey {
        case totalRequests = "total_requests"
        case history
    }
}
