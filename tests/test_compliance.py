"""Tests for EU AI Act data lineage and compliance certificate features."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.compliance_engine import compute_compliance
from tests.conftest import isolated_db

client = TestClient(app)


def auth_headers(client):
    r = client.post("/auth/guest")
    return {"Authorization": f"Bearer {r.json()['token']}"}


SYSTEM_PAYLOAD = {
    "system_name": "Loan Approval Engine",
    "company_name": "Acme Financial",
    "risk_tier": "high",
    "use_case": "Credit scoring for personal loans",
    "model_version": "v2.1.0",
    "training_data_sources": ["Equifax credit data", "Internal loan history 2015-2023"],
    "intended_purpose": "Automate initial loan eligibility screening",
    "geographic_scope": "EU",
}


# ── AI System Registration ────────────────────────────────────────────────────

class TestAISystemRegistration:
    def test_register_system_success(self, isolated_db):
        headers = auth_headers(client)
        r = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "system_id" in data
        assert data["system_name"] == "Loan Approval Engine"
        assert data["company_name"] == "Acme Financial"

    def test_list_systems_returns_registered(self, isolated_db):
        headers = auth_headers(client)
        client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers)
        r = client.get("/ai-systems", headers=headers)
        assert r.status_code == 200
        systems = r.json()
        assert len(systems) == 1
        assert systems[0]["risk_tier"] == "high"
        assert systems[0]["model_version"] == "v2.1.0"

    def test_register_invalid_risk_tier(self, isolated_db):
        headers = auth_headers(client)
        bad = {**SYSTEM_PAYLOAD, "risk_tier": "extreme"}
        r = client.post("/ai-systems", json=bad, headers=headers)
        assert r.status_code == 400

    def test_register_missing_system_name(self, isolated_db):
        headers = auth_headers(client)
        bad = {**SYSTEM_PAYLOAD, "system_name": ""}
        r = client.post("/ai-systems", json=bad, headers=headers)
        assert r.status_code == 400

    def test_register_requires_auth(self):
        r = client.post("/ai-systems", json=SYSTEM_PAYLOAD)
        assert r.status_code in (401, 403)

    def test_list_isolated_per_user(self, isolated_db):
        h1 = auth_headers(client)
        h2 = auth_headers(client)
        client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=h1)
        r = client.get("/ai-systems", headers=h2)
        assert r.json() == []


# ── Compliance Checklist ──────────────────────────────────────────────────────

class TestComplianceChecklist:
    def test_compliance_endpoint_returns_articles(self, isolated_db):
        headers = auth_headers(client)
        reg = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers).json()
        sid = reg["system_id"]
        r = client.get(f"/ai-systems/{sid}/compliance", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "articles" in data
        assert "art_9" in data["articles"]
        assert "art_10" in data["articles"]
        assert "art_11" in data["articles"]
        assert "art_12" in data["articles"]
        assert "art_13" in data["articles"]
        assert "art_14" in data["articles"]

    def test_compliance_overall_score_range(self, isolated_db):
        headers = auth_headers(client)
        reg = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers).json()
        r = client.get(f"/ai-systems/{reg['system_id']}/compliance", headers=headers)
        data = r.json()
        assert 0.0 <= data["overall_score"] <= 1.0

    def test_compliance_verdict_present(self, isolated_db):
        headers = auth_headers(client)
        reg = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers).json()
        r = client.get(f"/ai-systems/{reg['system_id']}/compliance", headers=headers)
        data = r.json()
        assert data["verdict"] in ("ready", "partial", "not_ready")

    def test_compliance_404_for_wrong_user(self, isolated_db):
        h1 = auth_headers(client)
        h2 = auth_headers(client)
        reg = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=h1).json()
        r = client.get(f"/ai-systems/{reg['system_id']}/compliance", headers=h2)
        assert r.status_code == 404

    def test_art10_passes_with_data_sources(self):
        system = {**SYSTEM_PAYLOAD, "system_id": 1,
                  "training_data_sources": ["Equifax", "Internal data"]}
        stats = {"total": 0, "hitl_overrides": 0, "proxy_vars_caught": 0,
                 "has_regulatory_refs": False, "has_risk_flags": False, "categories": []}
        result = compute_compliance(system, stats)
        assert result["articles"]["art_10"]["status"] == "pass"

    def test_art10_fails_without_data_sources(self):
        system = {**SYSTEM_PAYLOAD, "system_id": 1, "training_data_sources": []}
        stats = {"total": 0, "hitl_overrides": 0, "proxy_vars_caught": 0,
                 "has_regulatory_refs": False, "has_risk_flags": False, "categories": []}
        result = compute_compliance(system, stats)
        assert result["articles"]["art_10"]["status"] == "fail"

    def test_art12_passes_with_audit_entries(self):
        system = {**SYSTEM_PAYLOAD, "system_id": 1}
        stats = {"total": 5, "hitl_overrides": 0, "proxy_vars_caught": 0,
                 "has_regulatory_refs": False, "has_risk_flags": False, "categories": []}
        result = compute_compliance(system, stats)
        assert result["articles"]["art_12"]["status"] == "pass"

    def test_art14_passes_with_hitl_override(self):
        system = {**SYSTEM_PAYLOAD, "system_id": 1}
        stats = {"total": 5, "hitl_overrides": 2, "proxy_vars_caught": 0,
                 "has_regulatory_refs": False, "has_risk_flags": True, "categories": []}
        result = compute_compliance(system, stats)
        assert result["articles"]["art_14"]["status"] == "pass"

    def test_art14_partial_without_hitl(self):
        system = {**SYSTEM_PAYLOAD, "system_id": 1}
        stats = {"total": 3, "hitl_overrides": 0, "proxy_vars_caught": 0,
                 "has_regulatory_refs": False, "has_risk_flags": True, "categories": []}
        result = compute_compliance(system, stats)
        assert result["articles"]["art_14"]["status"] == "partial"

    def test_full_compliance_high_score(self):
        system = {**SYSTEM_PAYLOAD, "system_id": 1,
                  "intended_purpose": "Screening", "geographic_scope": "EU"}
        stats = {"total": 15, "hitl_overrides": 3, "proxy_vars_caught": 2,
                 "has_regulatory_refs": True, "has_risk_flags": True, "categories": ["finance"]}
        result = compute_compliance(system, stats)
        assert result["overall_score"] >= 0.75
        assert result["verdict"] in ("ready", "partial")


# ── Certificate Generation ────────────────────────────────────────────────────

class TestCertificateGeneration:
    def test_certificate_returns_pdf(self, isolated_db):
        headers = auth_headers(client)
        reg = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers).json()
        r = client.post(f"/ai-systems/{reg['system_id']}/certificate", headers=headers)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert len(r.content) > 1000  # non-trivial PDF

    def test_certificate_filename_contains_pragma(self, isolated_db):
        headers = auth_headers(client)
        reg = client.post("/ai-systems", json=SYSTEM_PAYLOAD, headers=headers).json()
        r = client.post(f"/ai-systems/{reg['system_id']}/certificate", headers=headers)
        assert "pragma" in r.headers.get("content-disposition", "").lower()

    def test_certificate_requires_auth(self):
        r = client.post("/ai-systems/1/certificate")
        assert r.status_code in (401, 403)

    def test_certificate_404_wrong_system(self, isolated_db):
        headers = auth_headers(client)
        r = client.post("/ai-systems/99999/certificate", headers=headers)
        assert r.status_code == 404
