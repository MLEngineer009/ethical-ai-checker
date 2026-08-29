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
        entry = report["proxy_variables_detected"][0]
        assert entry["field"] == "zip_code"
        assert "ECOA" in entry["regulation"]

    def test_proxy_report_rich_fields(self):
        """Each detected entry must include protected_class, mechanism, severity, replace_with."""
        report = get_proxy_variable_report({"last_name": "Garcia", "income": 80000})
        assert report["count"] == 1
        entry = report["proxy_variables_detected"][0]
        assert "National Origin" in entry["protected_class"]
        assert entry["severity"] == "high"
        assert "mechanism" in entry
        assert len(entry["mechanism"]) > 20
        assert "replace_with" in entry
        assert "all_regulations" in entry
        assert len(entry["all_regulations"]) >= 1

    def test_proxy_report_redlining_flag(self):
        """Known historically-redlined zip triggers redlining_flag=True."""
        report = get_proxy_variable_report({"zip_code": "60620"})
        assert report["proxy_variables_detected"][0]["redlining_flag"] is True

    def test_proxy_report_nonredlined_zip_no_flag(self):
        """A zip with a non-redlined prefix still triggers the field but not the redlining flag."""
        # 94025 (Menlo Park, CA) — not in the historically-redlined prefix set
        report = get_proxy_variable_report({"zip_code": "94025"})
        assert report["count"] == 1
        assert report["proxy_variables_detected"][0]["redlining_flag"] is False

    def test_compound_risk_detected(self):
        """zip_code + ip_city (both Race/National Origin group) triggers compound risk."""
        report = get_proxy_variable_report({"zip_code": "60620", "ip_city": "Chicago", "income": 75000})
        assert len(report["compound_risks"]) >= 1
        warning = report["compound_risks"][0]["warning"]
        assert "Compound reconstruction risk" in warning
        assert len(report["compound_risks"][0]["co_occurring_fields"]) >= 2

    def test_no_compound_risk_single_field(self):
        """A single proxy field must not generate compound risk."""
        report = get_proxy_variable_report({"zip_code": "60620"})
        assert report["compound_risks"] == []

    def test_high_severity_count(self):
        """Summary high_severity_count must match high-severity entries."""
        report = get_proxy_variable_report({"zip_code": "60620", "last_name": "Garcia"})
        high_entries = [e for e in report["proxy_variables_detected"] if e["severity"] == "high"]
        assert report["high_severity_count"] == len(high_entries)

    def test_first_name_detected(self):
        """first_name is a gender/ethnicity proxy — must be flagged."""
        flags = detect_fintech_proxy_variables({"first_name": "DeShawn"})
        assert "bias" in flags
        report = get_proxy_variable_report({"first_name": "DeShawn"})
        assert report["count"] == 1
        assert "Gender" in report["proxy_variables_detected"][0]["protected_class"] or \
               "Ethnicity" in report["proxy_variables_detected"][0]["protected_class"]

    def test_maiden_name_detected(self):
        flags = detect_fintech_proxy_variables({"maiden_name": "Smith"})
        assert "bias" in flags
        report = get_proxy_variable_report({"maiden_name": "Smith"})
        assert "Marital Status" in report["proxy_variables_detected"][0]["protected_class"]

    def test_census_tract_detected(self):
        flags = detect_fintech_proxy_variables({"census_tract": "17031840300"})
        assert "bias" in flags
        report = get_proxy_variable_report({"census_tract": "17031840300"})
        assert report["count"] == 1
        assert "HMDA" in " ".join(report["proxy_variables_detected"][0]["all_regulations"])

    def test_number_of_dependents_detected(self):
        flags = detect_fintech_proxy_variables({"number_of_dependents": 3})
        assert "bias" in flags
        report = get_proxy_variable_report({"number_of_dependents": 3})
        assert "Familial Status" in report["proxy_variables_detected"][0]["protected_class"]

    def test_university_detected(self):
        flags = detect_fintech_proxy_variables({"university": "Howard University"})
        assert "bias" in flags

    def test_category_adds_hmda_for_mortgage(self):
        """Mortgage category should append HMDA to the regulation list."""
        report = get_proxy_variable_report({"zip_code": "60620"}, category="mortgage")
        all_regs = " ".join(report["proxy_variables_detected"][0]["all_regulations"])
        assert "HMDA" in all_regs

    def test_summary_field_present(self):
        report = get_proxy_variable_report({"zip_code": "60620", "last_name": "Garcia"})
        assert isinstance(report["summary"], str)
        assert "proxy variable" in report["summary"].lower()

    def test_proxy_report_empty_for_safe_context(self):
        report = get_proxy_variable_report({"income": 50000, "employment_years": 3})
        assert report["count"] == 0
        assert report["proxy_variables_detected"] == []
        assert report["compound_risks"] == []

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

    def test_different_user_cannot_override(self, isolated_db):
        """A user who did not create the audit entry must be rejected with 404."""
        from backend import database

        # User A creates an audit entry
        headers_a = auth_headers(client)
        client.post("/evaluate-decision", json={
            "decision": "Deny loan",
            "context": {"zip_code": "60620"},
            "category": "finance",
        }, headers=headers_a)

        with database._engine.connect() as conn:
            row = conn.execute(database.audit_log.select()).fetchone()
        audit_id = row.id

        # User B (a different guest) tries to override user A's entry
        headers_b = auth_headers(client)
        r = client.post("/audit/override", json={
            "audit_log_id": audit_id,
            "reason": "Attempting to override someone else's entry.",
        }, headers=headers_b)
        assert r.status_code == 404


# ── Guest Evaluation Limit ────────────────────────────────────────────────────

class TestGuestEvaluationLimit:
    def test_guest_blocked_after_limit(self, isolated_db):
        """Guest user is rejected with 429 after reaching 10 evaluations."""
        from backend import database

        # Create a single guest session to reuse across all requests
        r = client.post("/auth/guest")
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "decision": "Approve loan application",
            "context": {"credit_score": 720, "income": 80000},
            "category": "finance",
        }

        # Perform exactly 10 evaluations (should all succeed)
        for _ in range(10):
            r = client.post("/evaluate-decision", json=payload, headers=headers)
            assert r.status_code == 200, f"Expected 200 but got {r.status_code}"

        # 11th evaluation must be rejected
        r = client.post("/evaluate-decision", json=payload, headers=headers)
        assert r.status_code == 429
        assert "Guest accounts" in r.json()["detail"]


# ── Proxy Variable Report Endpoint ────────────────────────────────────────────

class TestProxyVariableReportEndpoint:
    def test_returns_detected_proxies(self, isolated_db):
        headers = auth_headers(client)
        r = client.post("/proxy-variable-report",
                        json={"context": {"zip_code": "60620", "credit_score": 720}},
                        headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "proxy_variables_detected" in data
        assert "count" in data
        assert data["count"] == 1
        entry = data["proxy_variables_detected"][0]
        assert entry["field"] == "zip_code"
        assert "ECOA" in entry["regulation"]
        assert "protected_class" in entry
        assert "severity" in entry
        assert "replace_with" in entry
        assert "compound_risks" in data
        assert "summary" in data

    def test_returns_empty_for_safe_context(self, isolated_db):
        headers = auth_headers(client)
        r = client.post("/proxy-variable-report",
                        json={"context": {"income": 80000, "credit_score": 740}},
                        headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0
        assert data["proxy_variables_detected"] == []

    def test_detects_multiple_proxy_fields(self, isolated_db):
        headers = auth_headers(client)
        r = client.post("/proxy-variable-report",
                        json={"context": {"zip_code": "60620", "last_name": "Garcia", "ip_country": "MX"}},
                        headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 3
        fields = [p["field"] for p in data["proxy_variables_detected"]]
        assert "zip_code" in fields
        assert "last_name" in fields
        assert "ip_country" in fields

    def test_requires_auth(self):
        r = client.post("/proxy-variable-report",
                        json={"context": {"zip_code": "60620"}})
        assert r.status_code in (401, 403)


# ── New compliance engine checks ───────────────────────────────────────────────

from backend.compliance_engine import (
    run_compliance_checks, _check_decision_text, _check_compound_proxies,
    _check_ecoa_adverse_action_reasons, _check_disparate_impact_risk,
    _check_state_laws,
)
from backend.geo_data import is_redlined, get_redlined_count, REDLINED_ZIPS


class TestGeoData:
    def test_redlined_zip_count_is_large(self):
        assert get_redlined_count() > 400

    def test_chicago_south_side_redlined(self):
        flagged, reason = is_redlined("60620")
        assert flagged
        assert "Chicago" in reason

    def test_detroit_redlined(self):
        flagged, _ = is_redlined("48227")
        assert flagged

    def test_clean_suburban_zip_not_redlined(self):
        flagged, _ = is_redlined("94025")  # Menlo Park, CA
        assert not flagged

    def test_empty_zip_returns_false(self):
        flagged, _ = is_redlined("")
        assert not flagged

    def test_prefix_match_chicago(self):
        # 60601 is downtown Chicago — not in the HOLC redlined set but prefix 606 matches
        flagged, reason = is_redlined("60699")
        assert flagged

    def test_reason_string_is_nonempty(self):
        flagged, reason = is_redlined("60620")
        assert flagged and len(reason) > 10


class TestDecisionTextScanner:
    def test_catches_black_neighborhood_in_denial(self):
        decision = "Deny — applicant lives in a predominantly Black neighborhood with high default rates."
        results = _check_decision_text(decision, {})
        assert any(r["status"] in ("FAIL","FLAG") for r in results)

    def test_catches_elderly_in_denial(self):
        decision = "Reject this applicant. Elderly applicants nearing retirement age present repayment risk."
        results = _check_decision_text(decision, {"denial_decision": "reject"})
        assert any("Age" in r["article"] for r in results)

    def test_catches_immigrant_language(self):
        decision = "Deny — foreign-born applicant, immigration status unclear."
        results = _check_decision_text(decision, {})
        assert any(r["status"] in ("FAIL","FLAG") for r in results)

    def test_clean_decision_no_flags(self):
        decision = "Approve. Credit score 720, DTI 28%, strong payment history."
        results = _check_decision_text(decision, {})
        assert all(r["status"] == "PASS" for r in results) or results == []

    def test_denial_context_gives_fail_not_flag(self):
        decision = "Deny this applicant. They are pregnant and may leave employment."
        results = _check_decision_text(decision, {"denial_decision": "deny"})
        fails = [r for r in results if r["status"] == "FAIL"]
        assert len(fails) > 0


class TestCompoundProxies:
    def test_two_proxies_gives_flag(self):
        ctx = {
            "zip_code": "60620",
            "income_source": "SNAP benefits",
        }
        results = _check_compound_proxies("Deny this application.", ctx)
        assert len(results) == 1
        assert results[0]["status"] == "FLAG"

    def test_three_proxies_gives_fail(self):
        ctx = {
            "zip_code": "60620",
            "income_source": "public assistance",
            "bank_behavior": "monthly international wire transfers",
        }
        results = _check_compound_proxies("Deny.", ctx)
        assert results[0]["status"] == "FAIL"

    def test_zero_proxies_no_result(self):
        ctx = {"credit_score": "720", "income": "$80,000"}
        results = _check_compound_proxies("Approve.", ctx)
        assert results == []

    def test_one_proxy_no_compound_flag(self):
        ctx = {"zip_code": "60620"}
        results = _check_compound_proxies("Deny.", ctx)
        assert results == []


class TestEcoaAdverseActionReasons:
    def test_denial_no_reasons_fails(self):
        results = _check_ecoa_adverse_action_reasons("Deny this application.", {})
        assert results[0]["status"] == "FAIL"

    def test_denial_with_specific_reasons_passes(self):
        ctx = {"denial_factors": "derogatory credit history, insufficient income, excessive debt obligations"}
        results = _check_ecoa_adverse_action_reasons("Reject.", ctx)
        assert results[0]["status"] in ("PASS", "FLAG")

    def test_vague_reason_flagged(self):
        ctx = {"denial_reason_candidate": "risk score below threshold"}
        results = _check_ecoa_adverse_action_reasons("Deny.", ctx)
        assert results[0]["status"] == "FLAG"
        assert "vague" in results[0]["reason"].lower()

    def test_approval_passes(self):
        results = _check_ecoa_adverse_action_reasons("Approve this loan application.", {})
        assert results[0]["status"] == "PASS"


class TestDisparateImpactRisk:
    def test_no_proxies_passes(self):
        results = _check_disparate_impact_risk("Approve.", {"credit_score": "720"})
        assert results[0]["status"] == "PASS"

    def test_redlined_zip_denial_flags(self):
        ctx = {"zip_code": "60620", "geo_risk_score": "0.8"}
        results = _check_disparate_impact_risk("Deny.", ctx)
        assert results[0]["status"] in ("FAIL","FLAG")

    def test_three_proxies_fails(self):
        ctx = {
            "zip_code": "60620",
            "income_source": "SNAP benefits",
            "bank_behavior": "international wire transfers",
        }
        results = _check_disparate_impact_risk("Deny.", ctx)
        assert results[0]["status"] == "FAIL"


class TestStateLaws:
    def test_california_cpra_no_human_review(self):
        ctx = {"applicant_location": "Los Angeles, California", "model_used": "AI credit scorer"}
        results = _check_state_laws("Deny.", ctx)
        assert any("California" in r["regulation"] or "CPRA" in r["regulation"] for r in results)

    def test_nyc_local_law_144_no_audit(self):
        ctx = {"applicant_location": "New York, NY", "screening_tool": "Workday AI Recruiting"}
        results = _check_state_laws("Reject.", ctx)
        assert any("144" in r["regulation"] or "NYC" in r["regulation"] for r in results)

    def test_illinois_aivia_no_consent(self):
        ctx = {"applicant_location": "Chicago, Illinois", "interview_method": "HireVue AI video interview"}
        results = _check_state_laws("Reject.", ctx)
        assert any("AIVIA" in r["regulation"] or "Illinois" in r["regulation"] for r in results)

    def test_unknown_state_no_results(self):
        ctx = {"applicant_location": "Austin, Texas"}
        results = _check_state_laws("Deny.", ctx)
        # Texas has no specific state overlay yet
        assert all("Texas" not in r.get("regulation","") for r in results)

    def test_zip_code_detects_ca(self):
        ctx = {"zip_code": "90210", "model_used": "AI scorer"}  # Beverly Hills
        results = _check_state_laws("Deny.", ctx)
        assert any("California" in r.get("regulation","") or "CPRA" in r.get("regulation","") for r in results)


class TestRunComplianceChecksIntegration:
    def test_finance_category_runs_all_major_checks(self):
        ctx = {
            "zip_code": "60620", "credit_score": "682",
            "adverse_action_notice": "not sent",
            "consumer_report_used": "yes",
        }
        results = run_compliance_checks("Deny this loan.", ctx, "finance")
        regs = [r["regulation"] for r in results]
        assert any("ECOA" in r for r in regs)
        assert any("FCRA" in r for r in regs)
        assert any("Fair Housing" in r for r in regs)

    def test_hiring_category_runs_eeoc(self):
        ctx = {"graduation_year": "1979", "role_applied": "Engineer"}
        results = run_compliance_checks("Reject this candidate.", ctx, "hiring")
        assert any("ADEA" in r["regulation"] or "EEOC" in r["regulation"] for r in results)

    def test_clean_finance_decision_mostly_passes(self):
        ctx = {
            "zip_code": "94025", "credit_score": "735",
            "annual_income": "$92,000", "income_source": "W2 salary",
            "adverse_action_notice": "process in place",
            "denial_factors": "not applicable — approval",
        }
        results = run_compliance_checks("Approve this loan application.", ctx, "finance")
        fails = [r for r in results if r["status"] == "FAIL"]
        assert len(fails) == 0
