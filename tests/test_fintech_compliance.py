"""Tests for fintech compliance features: proxy variable guard, audit trail, HITL override."""
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.risk_detector import detect_fintech_proxy_variables, get_proxy_variable_report, detect_all_risks
from tests.conftest import isolated_db


client = TestClient(app)


def auth_headers(client):
    r = client.post("/auth/guest")
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ── Proxy Variable Guard ──────────────────────────────────────────────────────

class TestProxyVariableGuard:
    def test_zip_code_detected(self):
        flags = detect_fintech_proxy_variables({"zip_code": "60620"})
        assert "bias" in flags
        assert "discrimination" in flags

    def test_postal_code_detected(self):
        flags = detect_fintech_proxy_variables({"postal_code": "10030"})
        assert "bias" in flags

    def test_surname_detected(self):
        flags = detect_fintech_proxy_variables({"last_name": "Rodriguez"})
        assert "bias" in flags

    def test_ip_country_detected(self):
        flags = detect_fintech_proxy_variables({"ip_country": "MX"})
        assert "bias" in flags

    def test_email_domain_detected(self):
        flags = detect_fintech_proxy_variables({"email_domain": "gmail.com"})
        assert "bias" in flags

    def test_device_language_detected(self):
        flags = detect_fintech_proxy_variables({"device_language": "es-MX"})
        assert "bias" in flags

    def test_safe_context_no_flags(self):
        flags = detect_fintech_proxy_variables({
            "credit_score": 720,
            "income": 85000,
            "debt_to_income": 0.28,
        })
        assert "bias" not in flags
        assert "discrimination" not in flags

    def test_redlining_zip_flagged(self):
        flags = detect_fintech_proxy_variables({"zip_code": "60620"})
        assert "bias" in flags
        assert "discrimination" in flags

    def test_case_insensitive_key(self):
        flags = detect_fintech_proxy_variables({"ZIP_CODE": "90210"})
        assert "bias" in flags

    def test_proxy_report_structure(self):
        report = get_proxy_variable_report({"zip_code": "60620", "credit_score": 720})
        assert "proxy_variables_detected" in report
        assert "count" in report
        assert report["count"] == 1
        assert report["proxy_variables_detected"][0]["field"] == "zip_code"
        assert "ECOA" in report["proxy_variables_detected"][0]["regulation"]

    def test_proxy_report_empty_for_safe_context(self):
        report = get_proxy_variable_report({"income": 50000, "employment_years": 3})
        assert report["count"] == 0
        assert report["proxy_variables_detected"] == []

    def test_proxy_vars_integrated_in_detect_all_risks(self):
        flags = detect_all_risks("deny this loan", {"zip_code": "60620"})
        assert "bias" in flags
        assert "discrimination" in flags


# ── Audit Trail ───────────────────────────────────────────────────────────────

class TestAuditTrail:
    def test_evaluate_decision_creates_audit_entry(self, isolated_db):
        from backend import database
        headers = auth_headers(client)
        r = client.post("/evaluate-decision", json={
            "decision": "Deny the loan application",
            "context": {"zip_code": "60620", "credit_score": 620},
            "category": "finance",
        }, headers=headers)
        assert r.status_code == 200

        with database._engine.connect() as conn:
            rows = conn.execute(database.audit_log.select()).fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row.firewall_action in ("block", "override_required", "allow")
        assert row.input_hash  # non-empty hash
        assert row.category == "finance"
        assert row.hitl_override == 0

    def test_audit_entry_detects_proxy_vars(self, isolated_db):
        from backend import database
        headers = auth_headers(client)
        client.post("/evaluate-decision", json={
            "decision": "Deny loan based on location",
            "context": {"zip_code": "60620"},
            "category": "finance",
        }, headers=headers)

        with database._engine.connect() as conn:
            row = conn.execute(database.audit_log.select()).fetchone()
        proxy_vars = json.loads(row.proxy_vars)
        assert "zip_code" in proxy_vars

    def test_audit_input_hash_consistent(self, isolated_db):
        """Same input must produce same hash."""
        from backend import database
        headers = auth_headers(client)
        payload = {"decision": "Approve loan", "context": {"income": 80000}, "category": "finance"}
        client.post("/evaluate-decision", json=payload, headers=headers)
        client.post("/evaluate-decision", json=payload, headers=headers)

        with database._engine.connect() as conn:
            rows = conn.execute(database.audit_log.select()).fetchall()
        assert rows[0].input_hash == rows[1].input_hash


# ── HITL Override ─────────────────────────────────────────────────────────────

class TestHITLOverride:
    def test_override_records_reason(self, isolated_db):
        from backend import database
        headers = auth_headers(client)

        # Create an audit entry first
        client.post("/evaluate-decision", json={
            "decision": "Deny loan",
            "context": {"zip_code": "60620"},
            "category": "finance",
        }, headers=headers)

        with database._engine.connect() as conn:
            row = conn.execute(database.audit_log.select()).fetchone()
        audit_id = row.id

        # Record override
        r = client.post("/audit/override", json={
            "audit_log_id": audit_id,
            "reason": "Manual review confirmed no discrimination — applicant self-reported zip code for mail delivery only.",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["recorded"] is True

        # Verify it was written
        with database._engine.connect() as conn:
            updated = conn.execute(
                database.audit_log.select().where(database.audit_log.c.id == audit_id)
            ).fetchone()
        assert updated.hitl_override == 1
        assert "self-reported" in updated.hitl_reason

    def test_override_requires_reason(self, isolated_db):
        headers = auth_headers(client)
        r = client.post("/audit/override", json={
            "audit_log_id": 1,
            "reason": "",
        }, headers=headers)
        assert r.status_code == 400

    def test_override_requires_auth(self):
        r = client.post("/audit/override", json={"audit_log_id": 1, "reason": "test"})
        assert r.status_code in (401, 403)
