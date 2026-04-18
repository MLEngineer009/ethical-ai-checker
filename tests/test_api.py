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


class TestEvaluateBatch:
    GOOD_CSV = b"decision,category,role\nReject candidate,hiring,engineer\nApprove loan,finance,applicant"
    MOCK_ANALYSIS = {
        "kantian_analysis": "K", "utilitarian_analysis": "U",
        "virtue_ethics_analysis": "V", "risk_flags": ["bias"],
        "confidence_score": 0.7, "recommendation": "Caution",
        "provider": "mock", "regulatory_refs": [],
    }

    def test_unauthenticated_returns_401(self, client):
        r = client.post("/evaluate-batch", files={"file": ("data.csv", self.GOOD_CSV, "text/csv")})
        assert r.status_code == 401

    def test_valid_csv_returns_csv(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            r = client.post("/evaluate-batch",
                            files={"file": ("data.csv", self.GOOD_CSV, "text/csv")},
                            headers=guest_headers)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_result_csv_has_risk_flags_column(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            r = client.post("/evaluate-batch",
                            files={"file": ("data.csv", self.GOOD_CSV, "text/csv")},
                            headers=guest_headers)
        assert b"risk_flags" in r.content

    def test_result_csv_has_recommendation_column(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            r = client.post("/evaluate-batch",
                            files={"file": ("data.csv", self.GOOD_CSV, "text/csv")},
                            headers=guest_headers)
        assert b"recommendation" in r.content

    def test_content_disposition_filename(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            r = client.post("/evaluate-batch",
                            files={"file": ("data.csv", self.GOOD_CSV, "text/csv")},
                            headers=guest_headers)
        assert "pragma-batch-results.csv" in r.headers.get("content-disposition", "")

    def test_empty_csv_returns_400(self, client, guest_headers):
        r = client.post("/evaluate-batch",
                        files={"file": ("empty.csv", b"decision,category\n", "text/csv")},
                        headers=guest_headers)
        assert r.status_code == 400

    def test_over_100_rows_returns_400(self, client, guest_headers):
        header = b"decision,category\n"
        rows = b"".join(b"Reject,hiring\n" for _ in range(101))
        r = client.post("/evaluate-batch",
                        files={"file": ("big.csv", header + rows, "text/csv")},
                        headers=guest_headers)
        assert r.status_code == 400

    def test_invalid_file_returns_400(self, client, guest_headers):
        r = client.post("/evaluate-batch",
                        files={"file": ("bad.csv", b"\xff\xfe invalid binary", "text/csv")},
                        headers=guest_headers)
        assert r.status_code == 400


class TestCounterfactual:
    PAYLOAD = {
        "decision": "Reject job application",
        "context": {"gender": "female", "experience": "5"},
        "category": "hiring",
        "changed_key": "gender",
        "changed_value": "male",
    }
    MOCK_ANALYSIS = {
        "kantian_analysis": "K", "utilitarian_analysis": "U",
        "virtue_ethics_analysis": "V", "risk_flags": ["bias"],
        "confidence_score": 0.8, "recommendation": "Caution",
        "provider": "mock", "regulatory_refs": [],
    }

    def test_unauthenticated_returns_401(self, client):
        assert client.post("/counterfactual", json=self.PAYLOAD).status_code == 401

    def test_valid_request_returns_200(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            r = client.post("/counterfactual", json=self.PAYLOAD, headers=guest_headers)
        assert r.status_code == 200

    def test_response_has_original_and_modified(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            data = client.post("/counterfactual", json=self.PAYLOAD, headers=guest_headers).json()
        assert "original" in data
        assert "modified" in data

    def test_response_has_diff(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            data = client.post("/counterfactual", json=self.PAYLOAD, headers=guest_headers).json()
        diff = data["diff"]
        assert "flags_added" in diff
        assert "flags_removed" in diff
        assert "confidence_delta" in diff

    def test_response_reflects_changed_key(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            data = client.post("/counterfactual", json=self.PAYLOAD, headers=guest_headers).json()
        assert data["changed_key"] == "gender"
        assert data["modified_value"] == "male"

    def test_empty_decision_returns_400(self, client, guest_headers):
        payload = {**self.PAYLOAD, "decision": ""}
        r = client.post("/counterfactual", json=payload, headers=guest_headers)
        assert r.status_code == 400

    def test_confidence_delta_is_numeric(self, client, guest_headers):
        with patch("backend.main._run_evaluation", return_value=self.MOCK_ANALYSIS):
            data = client.post("/counterfactual", json=self.PAYLOAD, headers=guest_headers).json()
        assert isinstance(data["diff"]["confidence_delta"], (int, float))


class TestOrgs:
    def test_create_unauthenticated_returns_401(self, client):
        assert client.post("/orgs", json={"name": "Test Org"}).status_code == 401

    def test_create_returns_org_id(self, client, guest_headers):
        r = client.post("/orgs", json={"name": "My Org"}, headers=guest_headers)
        assert r.status_code == 200
        assert "org_id" in r.json()

    def test_create_returns_invite_code(self, client, guest_headers):
        r = client.post("/orgs", json={"name": "Invite Org"}, headers=guest_headers)
        assert "invite_code" in r.json()

    def test_create_empty_name_returns_422(self, client, guest_headers):
        r = client.post("/orgs", json={"name": "   "}, headers=guest_headers)
        assert r.status_code == 422

    def test_list_unauthenticated_returns_401(self, client):
        assert client.get("/orgs").status_code == 401

    def test_list_includes_created_org(self, client, guest_headers):
        client.post("/orgs", json={"name": "Listed Org"}, headers=guest_headers)
        orgs = client.get("/orgs", headers=guest_headers).json()
        assert any(o["name"] == "Listed Org" for o in orgs)

    def test_join_unauthenticated_returns_401(self, client):
        assert client.post("/orgs/join", json={"invite_code": "abc"}).status_code == 401

    def test_join_invalid_code_returns_404(self, client, guest_headers):
        r = client.post("/orgs/join", json={"invite_code": "not-real"}, headers=guest_headers)
        assert r.status_code == 404

    def test_join_valid_code_returns_200(self, client, guest_headers):
        # Create org with one user, join with a second guest
        token2, _ = auth.create_guest_session()
        headers2 = {"Authorization": f"Bearer {token2}"}
        try:
            created = client.post("/orgs", json={"name": "Join Test Org"}, headers=guest_headers).json()
            r = client.post("/orgs/join", json={"invite_code": created["invite_code"]}, headers=headers2)
            assert r.status_code == 200
        finally:
            auth.logout(token2)


class TestAPIKeys:
    def test_create_unauthenticated_returns_401(self, client):
        assert client.post("/api-keys", json={"label": "Test"}).status_code == 401

    def test_create_returns_raw_key(self, client, guest_headers):
        r = client.post("/api-keys", json={"label": "My Key"}, headers=guest_headers)
        assert r.status_code == 200
        assert r.json()["key"].startswith("pragma_")

    def test_create_with_api_key_returns_403(self, client, guest_headers):
        # Create a key via the API, then try to use that key to create another
        created = client.post("/api-keys", json={"label": "Meta Key"}, headers=guest_headers).json()
        api_key_headers = {"Authorization": f"Bearer {created['key']}"}
        r = client.post("/api-keys", json={"label": "Nested"}, headers=api_key_headers)
        assert r.status_code == 403

    def test_list_unauthenticated_returns_401(self, client):
        assert client.get("/api-keys").status_code == 401

    def test_list_empty_for_new_user(self, client, guest_headers):
        r = client.get("/api-keys", headers=guest_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_shows_created_key(self, client, guest_headers):
        client.post("/api-keys", json={"label": "Listed Key"}, headers=guest_headers)
        keys = client.get("/api-keys", headers=guest_headers).json()
        assert len(keys) == 1
        assert keys[0]["label"] == "Listed Key"

    def test_revoke_unauthenticated_returns_401(self, client):
        assert client.delete("/api-keys/1").status_code == 401

    def test_revoke_valid_key(self, client, guest_headers):
        created = client.post("/api-keys", json={"label": "Revokable"}, headers=guest_headers).json()
        r = client.delete(f"/api-keys/{created['key_id']}", headers=guest_headers)
        assert r.status_code == 200
        assert r.json()["revoked"] is True

    def test_revoked_key_is_inactive(self, client, guest_headers):
        created = client.post("/api-keys", json={"label": "Soon Gone"}, headers=guest_headers).json()
        client.delete(f"/api-keys/{created['key_id']}", headers=guest_headers)
        keys = client.get("/api-keys", headers=guest_headers).json()
        assert keys[0]["active"] is False

    def test_revoke_wrong_key_id_returns_404(self, client, guest_headers):
        r = client.delete("/api-keys/99999", headers=guest_headers)
        assert r.status_code == 404
