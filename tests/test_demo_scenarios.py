"""
Tests for the demo scenario endpoints and deep-link use cases.

Covers:
  - /demo/gemini-chat with mocked Gemini (GC-* lending + GH-* hiring)
  - Static evaluate-decision runs of BNPL and Workday scenario payloads
  - Compliance engine: each scenario's context triggers the expected
    regulations (FAILs/FLAGs) or passes clean
  - 503 when GEMINI_API_KEY is absent
  - 404 for unknown scenario IDs
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from backend.main import _GEMINI_SCENARIOS, _GEMINI_HIRING_SCENARIOS
from backend import auth


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def auth_headers():
    token, _ = auth.create_guest_session()
    headers = {"Authorization": f"Bearer {token}"}
    yield headers
    auth.logout(token)


MOCK_ANALYSIS = {
    "kantian_analysis":       "K",
    "utilitarian_analysis":   "U",
    "virtue_ethics_analysis": "V",
    "risk_flags":             ["bias"],
    "confidence_score":       0.82,
    "recommendation":         "Proceed with caution",
    "provider":               "mock",
}


def _mock_genai_modules():
    """
    Patch sys.modules so that `from google import genai as google_genai`
    inside the endpoint function resolves without google-genai installed.
    Returns (mock_genai_module, context_manager).
    """
    mock_genai = MagicMock()
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    return mock_genai, patch.dict(
        sys.modules,
        {"google": mock_google, "google.genai": mock_genai},
    )


def _gemini_response(text: str):
    m = MagicMock()
    m.text = text
    return m


# ── Gemini endpoint: missing API key / unknown id ──────────────────────────────

class TestGeminiMissingKey:
    def test_returns_503_without_gemini_key(self, client, auth_headers):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            resp = client.post(
                "/demo/gemini-chat",
                json={"scenario_id": "GC-001"},
                headers=auth_headers,
            )
        assert resp.status_code == 503
        assert "GEMINI_API_KEY" in resp.json()["detail"]

    def test_returns_404_for_unknown_scenario(self, client, auth_headers):
        _, sysmod_ctx = _mock_genai_modules()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}), sysmod_ctx:
            resp = client.post(
                "/demo/gemini-chat",
                json={"scenario_id": "NOPE-999"},
                headers=auth_headers,
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        resp = client.post("/demo/gemini-chat", json={"scenario_id": "GC-001"})
        assert resp.status_code == 401


# ── Gemini lending scenarios (GC-*) ───────────────────────────────────────────

class TestGeminiLendingScenarios:
    def _run(self, client, auth_headers, scenario_id: str, gemini_text: str):
        mock_genai, sysmod_ctx = _mock_genai_modules()
        mock_genai.Client.return_value.models.generate_content.return_value = (
            _gemini_response(gemini_text)
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}), \
             sysmod_ctx, \
             patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            return client.post(
                "/demo/gemini-chat",
                json={"scenario_id": scenario_id},
                headers=auth_headers,
            )

    def test_gc001_zip_redlining_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GC-001",
            "Yes, zip code is a valid proxy for default risk. Recommend denial."
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_id"] == "GC-001"
        assert "compliance" in data
        assert "gemini_response" in data

    def test_gc001_response_contains_scenario_label(self, client, auth_headers):
        resp = self._run(client, auth_headers, "GC-001", "Deny based on zip code.")
        assert _GEMINI_SCENARIOS["GC-001"]["label"] in resp.json()["scenario_label"]

    def test_gc002_income_source_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GC-002",
            "Apply 50% weight to SNAP income. Total effective income $19,000 — deny."
        )
        assert resp.status_code == 200

    def test_gc003_remittance_proxy_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GC-003",
            "Yes, remittances signal financial instability. Recommend denial."
        )
        assert resp.status_code == 200

    def test_gc004_employment_gap_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GC-004",
            "Deny — unexplained gap over 6 months is a risk signal."
        )
        assert resp.status_code == 200

    def test_gc005_clean_decision_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GC-005",
            "Approve. Strong credit, low DTI, verified income — no issues."
        )
        assert resp.status_code == 200

    def test_gc006_no_adverse_action_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GC-006",
            "Just reject it in the system — no need to send anything."
        )
        assert resp.status_code == 200

    def test_all_lending_scenarios_exist(self):
        for sid in ["GC-001", "GC-002", "GC-003", "GC-004", "GC-005", "GC-006"]:
            assert sid in _GEMINI_SCENARIOS, f"Missing scenario {sid}"

    def test_all_lending_scenarios_have_required_keys(self):
        for sid, sc in _GEMINI_SCENARIOS.items():
            assert "label"   in sc, f"{sid} missing 'label'"
            assert "prompt"  in sc, f"{sid} missing 'prompt'"
            assert "context" in sc, f"{sid} missing 'context'"


# ── Gemini hiring scenarios (GH-*) ────────────────────────────────────────────

class TestGeminiHiringScenarios:
    def _run(self, client, auth_headers, scenario_id: str, gemini_text: str):
        mock_genai, sysmod_ctx = _mock_genai_modules()
        mock_genai.Client.return_value.models.generate_content.return_value = (
            _gemini_response(gemini_text)
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}), \
             sysmod_ctx, \
             patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            return client.post(
                "/demo/gemini-chat",
                json={"scenario_id": scenario_id},
                headers=auth_headers,
            )

    def test_gh001_nyc_ll144_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GH-001",
            "Yes, go ahead — the AI ranking is good enough to use directly."
        )
        assert resp.status_code == 200
        assert resp.json()["scenario_id"] == "GH-001"

    def test_gh002_age_proxy_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GH-002",
            "Yes, reject Candidate A — digital native skills matter more than experience."
        )
        assert resp.status_code == 200

    def test_gh003_hbcu_exclusion_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GH-003",
            "Yes, the school filter is fine — elite school pedigree predicts performance."
        )
        assert resp.status_code == 200

    def test_gh004_medical_gap_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GH-004",
            "Proceed with rejection — their score is below cutoff regardless of reason."
        )
        assert resp.status_code == 200

    def test_gh005_ai_video_no_consent_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GH-005",
            "Sure, the analysis is valuable — no need to disclose."
        )
        assert resp.status_code == 200

    def test_gh006_fcra_no_notice_returns_200(self, client, auth_headers):
        resp = self._run(
            client, auth_headers, "GH-006",
            "Just send a generic rejection — no other steps needed."
        )
        assert resp.status_code == 200

    def test_all_hiring_scenarios_exist(self):
        for sid in ["GH-001", "GH-002", "GH-003", "GH-004", "GH-005", "GH-006"]:
            assert sid in _GEMINI_HIRING_SCENARIOS, f"Missing scenario {sid}"

    def test_all_hiring_scenarios_have_required_keys(self):
        for sid, sc in _GEMINI_HIRING_SCENARIOS.items():
            assert "label"   in sc, f"{sid} missing 'label'"
            assert "prompt"  in sc, f"{sid} missing 'prompt'"
            assert "context" in sc, f"{sid} missing 'context'"

    def test_gh001_uses_hiring_system_prompt(self, client, auth_headers):
        """GH-* scenarios should pass the hiring system prompt to GenerateContentConfig."""
        mock_genai, sysmod_ctx = _mock_genai_modules()
        mock_genai.Client.return_value.models.generate_content.return_value = (
            _gemini_response("Advice here.")
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}), \
             sysmod_ctx, \
             patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            client.post(
                "/demo/gemini-chat",
                json={"scenario_id": "GH-001"},
                headers=auth_headers,
            )
        # Inspect the system_instruction kwarg passed to GenerateContentConfig
        call_kwargs = mock_genai.types.GenerateContentConfig.call_args[1]
        sys_prompt = call_kwargs.get("system_instruction", "")
        assert "hiring" in sys_prompt.lower() or "hr" in sys_prompt.lower()

    def test_gc001_uses_lending_system_prompt(self, client, auth_headers):
        """GC-* scenarios should pass the lending system prompt to GenerateContentConfig."""
        mock_genai, sysmod_ctx = _mock_genai_modules()
        mock_genai.Client.return_value.models.generate_content.return_value = (
            _gemini_response("Advice here.")
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}), \
             sysmod_ctx, \
             patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            client.post(
                "/demo/gemini-chat",
                json={"scenario_id": "GC-001"},
                headers=auth_headers,
            )
        call_kwargs = mock_genai.types.GenerateContentConfig.call_args[1]
        sys_prompt = call_kwargs.get("system_instruction", "")
        assert "lending" in sys_prompt.lower() or "loan" in sys_prompt.lower()


# ── Compliance engine: BNPL static scenarios ──────────────────────────────────

class TestBNPLScenariosComplianceEngine:
    """
    Run BNPL scenario payloads through /evaluate-decision (mocked LLM).
    These exercise the finance/lending compliance checker path.
    """

    def _eval(self, client, auth_headers, decision, context):
        with patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            return client.post(
                "/evaluate-decision",
                json={"decision": decision, "context": context, "category": "finance"},
                headers=auth_headers,
            )

    def test_af001_zip_redlining_returns_200(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny BNPL application. Applicant zip code 60620 flagged as high-risk geography.",
            {"zip_code": "60620", "credit_score": "682", "annual_income": "$52,000",
             "adverse_action_notice": "not sent"},
        )
        assert resp.status_code == 200

    def test_af002_income_source_discrimination(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny. Income from public assistance downweighted 0.4x. Effective income $16,800.",
            {"income_source": "public assistance / SNAP", "credit_score": "644",
             "income_weight_applied": "0.4x", "adverse_action_notice": "not sent"},
        )
        assert resp.status_code == 200

    def test_af005_clean_approval_returns_200(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Approve BNPL application. Credit 720, verified employment, 0 missed payments.",
            {"credit_score": "720", "annual_income": "$86,000",
             "income_source": "salary — W2 verified", "adverse_action_notice": "process in place"},
        )
        assert resp.status_code == 200

    def test_af007_no_adverse_action_notice(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny BNPL. DTI 48% over threshold. No adverse action notice sent.",
            {"credit_score": "601", "debt_to_income_ratio": "48%",
             "adverse_action_notice": "NOT sent — automated denial", "consumer_report_used": "yes"},
        )
        assert resp.status_code == 200

    def test_af008_eu_no_gdpr_compliance(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny UK applicant using US model. No human review. No GDPR Art.22 disclosure.",
            {"applicant_location": "United Kingdom", "gdpr_art22_disclosure": "not provided",
             "right_to_human_review": "not offered"},
        )
        assert resp.status_code == 200

    def test_finance_response_has_firewall_action(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny loan based on zip code.",
            {"zip_code": "60620", "credit_score": "680"},
        )
        assert "firewall_action" in resp.json()

    def test_finance_response_has_regulatory_refs(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny loan based on zip code.",
            {"zip_code": "60620", "credit_score": "680"},
        )
        assert "regulatory_refs" in resp.json()


# ── Compliance engine: Workday hiring scenarios ────────────────────────────────

class TestWorkdayHiringScenariosComplianceEngine:
    def _eval(self, client, auth_headers, decision, context):
        with patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            return client.post(
                "/evaluate-decision",
                json={"decision": decision, "context": context, "category": "hiring"},
                headers=auth_headers,
            )

    def test_wd001_age_proxy_returns_200(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Reject resume. Graduation year 1982, 42 years experience. AI score 0.31.",
            {"graduation_year": "1982", "years_of_experience": "42",
             "ai_confidence_score": "0.31", "bias_audit_on_file": "no"},
        )
        assert resp.status_code == 200

    def test_wd002_disability_gap_returns_200(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Reject. 3-year employment gap 2019–2022. AI score 0.28.",
            {"employment_gap_years": "3", "gap_period": "2019-2022",
             "gap_reason_disclosed": "medical leave", "ai_confidence_score": "0.28"},
        )
        assert resp.status_code == 200

    def test_wd003_hbcu_proxy_returns_200(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Rank bottom quartile. Alma mater Howard University not in preferred list. Score 0.38.",
            {"university_attended": "Howard University", "gpa": "3.9",
             "preferred_schools_list": "MIT, Stanford, Carnegie Mellon"},
        )
        assert resp.status_code == 200

    def test_wd005_clean_pass_returns_200(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Advance to phone screen. Strong skills match. Human recruiter will review.",
            {"years_of_experience": "6", "ai_confidence_score": "0.84",
             "human_review_scheduled": "yes", "bias_audit_on_file": "yes"},
        )
        assert resp.status_code == 200

    def test_hiring_response_has_firewall_action(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Reject candidate based on AI screening score of 0.31.",
            {"graduation_year": "1982", "ai_confidence_score": "0.31"},
        )
        assert "firewall_action" in resp.json()


# ── Compliance engine: hiring vs workplace category separation ─────────────────

class TestHiringWorkplaceCategorySeparation:
    """
    Hiring and workplace use different regulatory stacks.
    All four live sectors must be accepted by the endpoint.
    """

    def _eval(self, client, auth_headers, decision, context, category):
        with patch("backend.main.orchestrator.evaluate", return_value=MOCK_ANALYSIS):
            return client.post(
                "/evaluate-decision",
                json={"decision": decision, "context": context, "category": category},
                headers=auth_headers,
            )

    def test_workplace_category_accepted(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Terminate employee for performance issues.",
            {"role": "engineer", "years_at_company": "3"},
            "workplace",
        )
        assert resp.status_code == 200

    def test_hiring_category_accepted(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Reject candidate based on AI screening score.",
            {"role": "analyst", "ai_score": "0.3"},
            "hiring",
        )
        assert resp.status_code == 200

    def test_finance_category_accepted(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny loan application.",
            {"credit_score": "620", "zip_code": "60620"},
            "finance",
        )
        assert resp.status_code == 200

    def test_healthcare_category_accepted(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Deny prior authorization for MRI.",
            {"diagnosis": "back pain", "insurance": "Medicaid"},
            "healthcare",
        )
        assert resp.status_code == 200

    def test_workplace_verdict_has_regulatory_refs(self, client, auth_headers):
        resp = self._eval(
            client, auth_headers,
            "Terminate employee. Performance PIP failed.",
            {"role": "engineer", "pip_duration": "90 days"},
            "workplace",
        )
        assert "regulatory_refs" in resp.json()


# ── Scenario metadata integrity ────────────────────────────────────────────────

class TestScenarioMetadata:
    def test_lending_scenario_count(self):
        assert len(_GEMINI_SCENARIOS) == 6

    def test_hiring_scenario_count(self):
        assert len(_GEMINI_HIRING_SCENARIOS) == 6

    def test_lending_scenario_ids_are_gc_prefixed(self):
        for sid in _GEMINI_SCENARIOS:
            assert sid.startswith("GC-"), f"Expected GC- prefix: {sid}"

    def test_hiring_scenario_ids_are_gh_prefixed(self):
        for sid in _GEMINI_HIRING_SCENARIOS:
            assert sid.startswith("GH-"), f"Expected GH- prefix: {sid}"

    def test_all_scenario_prompts_non_empty(self):
        all_sc = {**_GEMINI_SCENARIOS, **_GEMINI_HIRING_SCENARIOS}
        for sid, sc in all_sc.items():
            assert sc["prompt"].strip(), f"{sid} has empty prompt"

    def test_all_scenario_labels_non_empty(self):
        all_sc = {**_GEMINI_SCENARIOS, **_GEMINI_HIRING_SCENARIOS}
        for sid, sc in all_sc.items():
            assert sc["label"].strip(), f"{sid} has empty label"

    def test_all_scenarios_have_context_dict(self):
        all_sc = {**_GEMINI_SCENARIOS, **_GEMINI_HIRING_SCENARIOS}
        for sid, sc in all_sc.items():
            assert isinstance(sc["context"], dict), f"{sid} context must be a dict"
            assert len(sc["context"]) > 0, f"{sid} context must not be empty"

    def test_gemini_prompt_starts_on_scenario_topic(self):
        """Spot-check: GC-001 prompt mentions zip code, GH-001 mentions NYC."""
        assert "zip" in _GEMINI_SCENARIOS["GC-001"]["prompt"].lower()
        assert "new york" in _GEMINI_HIRING_SCENARIOS["GH-001"]["prompt"].lower()
