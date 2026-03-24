// Update BASE_URL to your Mac's LAN IP when testing on a real device
// e.g. "http://192.168.1.100:8000"
// For simulator: "http://localhost:8000" works fine
export const BASE_URL = "http://localhost:8000";

export interface EthicalAnalysis {
  kantian_analysis: string;
  utilitarian_analysis: string;
  virtue_ethics_analysis: string;
  risk_flags: string[];
  confidence_score: number;
  recommendation: string;
  provider: string;
}

export interface AuthResponse {
  token: string;
  name?: string;
  picture?: string;
  is_guest?: boolean;
}

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: object; token?: string } = {}
): Promise<T> {
  const { method = "GET", body, token } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) throw new APIError(401, "Session expired. Please sign in again.");
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new APIError(res.status, data.detail || `Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  guestAuth: () => request<AuthResponse>("/auth/guest", { method: "POST" }),

  googleAuth: (credential: string) =>
    request<AuthResponse>("/auth/google", { method: "POST", body: { credential } }),

  logout: (token: string) =>
    request("/logout", { method: "POST", token }),

  me: (token: string) =>
    request<{ name: string; picture: string }>("/me", { token }),

  evaluate: (decision: string, context: Record<string, string>, token: string) =>
    request<EthicalAnalysis>("/evaluate-decision", {
      method: "POST",
      body: { decision, context },
      token,
    }),

  generateReport: async (
    decision: string,
    context: Record<string, string>,
    analysis: EthicalAnalysis,
    token: string
  ): Promise<Blob> => {
    const res = await fetch(`${BASE_URL}/generate-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ decision, context, analysis }),
    });
    if (!res.ok) throw new APIError(res.status, "Report generation failed");
    return res.blob();
  },
};
