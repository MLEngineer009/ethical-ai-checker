"""Integration tests for FastAPI endpoints — LLM calls are mocked."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend import auth
from backend.main import app


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def guest_headers():
    token, _ = auth.create_guest_session()
    headers = {"Authorization": f"Bearer {token}"}
    yield headers
    auth.logout(token)


MOCK_ANALYSIS = {
    "kantian_analysis": "K analysis",
    "utilitarian_analysis": "U analysis",
    "virtue_ethics_analysis": "V analysis",
    "risk_flags": ["bias"],
    "confidence_score": 0.8,
    "recommendation": "Proceed with caution",
    "provider": "mock",
}

DECISION_PAYLOAD = {
    "decision": "Reject job candidate",
    "context": {"gender": "female", "experience": 5},
}


class TestQuestions:
    def test_all_returns_version(self, client):
        data = client.get("/questions").json()
        assert "version" in data
        assert "questions" in data

    def test_all_returns_all_categories(self, client):
        data = client.get("/questions").json()["questions"]
        for cat in ["hiring", "workplace", "finance", "healthcare", "policy", "personal", "other"]:
            assert cat in data

    def test_category_filter(self, client):
        data = client.get("/questions?category=hiring").json()
        assert data["category"] == "hiring"
        assert isinstance(data["questions"], list)
        assert len(data["questions"]) > 0

    def test_hiring_has_required_fields(self, client):
        qs = client.get("/questions?category=hiring").json()["questions"]
        keys = {q["key"] for q in qs}
        assert "role" in keys
        assert "criteria" in keys
        assert "demographics_in_data" in keys

    def test_question_schema(self, client):
        qs = client.get("/questions?category=hiring").json()["questions"]
        for q in qs:
            assert "key" in q
            assert "label" in q
            assert "type" in q
            assert q["type"] in ("text", "select", "multiselect", "toggle")

    def test_unknown_category_returns_404(self, client):
        assert client.get("/questions?category=nonsense").status_code == 404

    def test_other_returns_empty_list(self, client):
        data = client.get("/questions?category=other").json()
        assert data["questions"] == []


class TestHealthCheck:
    def test_returns_200(self, client):
        assert client.get("/health-check").status_code == 200

    def test_status_is_healthy(self, client):
        assert client.get("/health-check").json()["status"] == "healthy"

    def test_model_key_present(self, client):
        data = client.get("/health-check").json()
        assert "model" in data
        assert "pragma" in data["model"]
        assert "claude" in data["model"]
        assert "openai" in data["model"]

    def test_root_endpoint(self, client):
        assert client.get("/").status_code in (200,)


class TestGuestAuth:
    def test_returns_200(self, client):
        assert client.post("/auth/guest").status_code == 200

    def test_returns_token(self, client):
        assert "token" in client.post("/auth/guest").json()

    def test_returns_guest_name(self, client):
        assert client.post("/auth/guest").json()["name"] == "Guest"

    def test_is_guest_true(self, client):
        assert client.post("/auth/guest").json()["is_guest"] is True

    def test_tokens_differ_across_calls(self, client):
        t1 = client.post("/auth/guest").json()["token"]
        t2 = client.post("/auth/guest").json()["token"]
        assert t1 != t2


class TestGoogleAuth:
    def test_invalid_credential_returns_401(self, client):
        assert client.post("/auth/google", json={"credential": "bad-token"}).status_code == 401

    def test_valid_credential_returns_token(self, client):
        mock_info = {"sub": "g-123", "name": "Alice", "picture": "https://pic.com/a.jpg"}
        with patch("backend.auth.verify_google_token", return_value=mock_info):
            r = client.post("/auth/google", json={"credential": "valid-token"})
        assert r.status_code == 200
        assert r.json()["name"] == "Alice"


class TestLogout:
    def test_with_valid_token(self, client, guest_headers):
        r = client.post("/logout", headers=guest_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_without_token(self, client):
        assert client.post("/logout").status_code == 200


class TestMe:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/me").status_code == 401

    def test_authenticated_returns_guest_name(self, client, guest_headers):
        r = client.get("/me", headers=guest_headers)
        assert r.status_code == 200
        assert r.json()["name"] == "Guest"

    def test_invalid_token_returns_401(self, client):
        r = client.get("/me", headers={"Authorization": "Bearer not-real"})
        assert r.status_code == 401


class TestMyStats:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/my-stats").status_code == 401

    def test_authenticated_returns_stats(self, client, guest_headers):
        r = client.get("/my-stats", headers=guest_headers)
        assert r.status_code == 200
        assert "total_requests" in r.json()

    def test_fresh_user_has_zero_requests(self, client, guest_headers):
        assert client.get("/my-stats", headers=guest_headers).json()["total_requests"] == 0


class TestEvaluateDecision:
    def test_unauthenticated_returns_401(self, client):
        assert client.post("/evaluate-decision", json=DECISION_PAYLOAD).status_code == 401

    def test_empty_decision_returns_400(self, client, guest_headers):
        r = client.post("/evaluate-decision",
                        json={"decision": "", "context": {"x": 1}},
                        headers=guest_headers)
        assert r.status_code == 400

    def test_whitespace_decision_returns_400(self, client, guest_headers):
        r = client.post("/evaluate-decision",
                        json={"decision": "   ", "context": {"x": 1}},
                        headers=guest_headers)
        assert r.status_code == 400

    def test_empty_context_returns_400(self, client, guest_headers):
        r = client.post("/evaluate-decision",
                        json={"decision": "Reject", "context": {}},
                        headers=guest_headers)
        assert r.status_code == 400

    def test_valid_request_returns_200(self, client, guest_headers):
        with patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            r = client.post("/evaluate-decision", json=DECISION_PAYLOAD, headers=guest_headers)
        assert r.status_code == 200

    def test_response_has_all_fields(self, client, guest_headers):
        with patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            data = client.post("/evaluate-decision", json=DECISION_PAYLOAD, headers=guest_headers).json()
        for key in ("kantian_analysis", "utilitarian_analysis", "virtue_ethics_analysis",
                    "risk_flags", "confidence_score", "recommendation", "provider"):
            assert key in data

    def test_heuristic_bias_flag_merged(self, client, guest_headers):
        no_flags = {**MOCK_ANALYSIS, "risk_flags": []}
        with patch("backend.main.orchestrator.evaluate", return_value=no_flags):
            data = client.post("/evaluate-decision", json=DECISION_PAYLOAD, headers=guest_headers).json()
        assert "bias" in data["risk_flags"]

    def test_confidence_in_range(self, client, guest_headers):
        with patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            score = client.post("/evaluate-decision", json=DECISION_PAYLOAD, headers=guest_headers).json()["confidence_score"]
        assert 0 <= score <= 1

    def test_out_of_range_confidence_defaults_to_half(self, client, guest_headers):
        bad = {**MOCK_ANALYSIS, "confidence_score": 99}
        with patch("backend.main.orchestrator.evaluate", return_value=bad):
            score = client.post("/evaluate-decision", json=DECISION_PAYLOAD, headers=guest_headers).json()["confidence_score"]
        assert score == 0.5


class TestGenerateReport:
    PAYLOAD = {"decision": "Reject", "context": {"gender": "female"}, "analysis": MOCK_ANALYSIS}

    def test_unauthenticated_returns_401(self, client):
        assert client.post("/generate-report", json=self.PAYLOAD).status_code == 401

    def test_returns_pdf(self, client, guest_headers):
        with patch("backend.main.generate_pdf", return_value=b"%PDF-fake"):
            r = client.post("/generate-report", json=self.PAYLOAD, headers=guest_headers)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_content_disposition(self, client, guest_headers):
        with patch("backend.main.generate_pdf", return_value=b"%PDF-fake"):
            r = client.post("/generate-report", json=self.PAYLOAD, headers=guest_headers)
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_generation_error_returns_500(self, client, guest_headers):
        with patch("backend.main.generate_pdf", side_effect=RuntimeError("fail")):
            r = client.post("/generate-report", json=self.PAYLOAD, headers=guest_headers)
        assert r.status_code == 500


class TestFeedback:
    PAYLOAD = {
        "rating": 1,
        "category": "hiring",
        "provider": "pragma",
        "model_version": "v1",
        "confidence": 0.85,
        "risk_flags": ["bias"],
    }

    def test_unauthenticated_returns_401(self, client):
        assert client.post("/feedback", json=self.PAYLOAD).status_code == 401

    def test_thumbs_up_returns_ok(self, client, guest_headers):
        r = client.post("/feedback", json=self.PAYLOAD, headers=guest_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_thumbs_down_accepted(self, client, guest_headers):
        payload = {**self.PAYLOAD, "rating": -1}
        r = client.post("/feedback", json=payload, headers=guest_headers)
        assert r.status_code == 200

    def test_invalid_rating_returns_400(self, client, guest_headers):
        payload = {**self.PAYLOAD, "rating": 0}
        r = client.post("/feedback", json=payload, headers=guest_headers)
        assert r.status_code == 400

    def test_invalid_category_defaults_to_other(self, client, guest_headers):
        payload = {**self.PAYLOAD, "category": "not-a-category"}
        r = client.post("/feedback", json=payload, headers=guest_headers)
        assert r.status_code == 200  # accepted, coerced to "other"
