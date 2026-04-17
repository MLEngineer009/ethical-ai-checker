// Update BASE_URL to your Mac's LAN IP when testing on a real device
// e.g. "http://192.168.1.100:8000"
// For simulator: "http://localhost:8000" works fine
import { API_BASE_URL } from "../config";
export const BASE_URL = API_BASE_URL;

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

export interface Question {
  key: string;
  label: string;
  type: "text" | "select" | "multiselect" | "toggle";
  options?: string[];
  placeholder?: string;
  required: boolean;
}

export const api = {
  getQuestions: (category: string) =>
    request<{ version: string; category: string; questions: Question[] }>(`/questions?category=${category}`),

  guestAuth: () => request<AuthResponse>("/auth/guest", { method: "POST" }),

  googleAuth: (credential: string) =>
    request<AuthResponse>("/auth/google", { method: "POST", body: { credential } }),

  logout: (token: string) =>
    request("/logout", { method: "POST", token }),

  me: (token: string) =>
    request<{ name: string; picture: string }>("/me", { token }),

  getStats: (token: string) =>
    request<{ total_requests: number; history: any[] }>("/my-stats", { token }),

  counterfactual: (
    decision: string,
    context: Record<string, string>,
    category: string,
    changedKey: string,
    changedValue: string,
    token: string,
  ) =>
    request<{
      original: EthicalAnalysis;
      modified: EthicalAnalysis;
      changed_key: string;
      original_value: string;
      modified_value: string;
      diff: { flags_added: string[]; flags_removed: string[]; confidence_delta: number };
    }>("/counterfactual", {
      method: "POST",
      token,
      body: { decision, context, category, changed_key: changedKey, changed_value: changedValue },
    }),

  evaluate: (decision: string, context: Record<string, string>, token: string, category = "other") =>
    request<EthicalAnalysis>("/evaluate-decision", {
      method: "POST",
      body: { decision, context, category },
      token,
    }),

  generateReport: async (
    decision: string,
    context: Record<string, string>,
    analysis: EthicalAnalysis,
    token: string
  ): Promise<ArrayBuffer> => {
    const res = await fetch(`${BASE_URL}/generate-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ decision, context, analysis }),
    });
    if (!res.ok) throw new APIError(res.status, "Report generation failed");
    return res.arrayBuffer();
  },
};
