"""
Hiring compliance test suite — one test per enforcement rule.

Coverage:
  ADEA §623           graduation year → age proxy
  Title VII §2000e-2  HBCU exclusion → race proxy
  ADA §12112          employment gap (FLAG and FAIL)
  FCRA §604(b)(3)     pre-adverse notice not sent
  FCRA §615(a)        final adverse notice not sent
  FCRA                both notices present → PASS
  NYC LL144           no bias audit (NY) → FAIL
  NYC LL144           candidate not notified (NY) → FAIL
  NYC LL144           regression — must NOT fire for non-NY candidates
  IL AIVIA            no consent → FAIL
  IL AIVIA            consent obtained → PASS
  IL AIVIA            non-IL location → no violation
  CA AB-168           prior comp in CA denial → FAIL
  NY §194-a           prior comp in NY denial → FAIL
  CO EPEWA            prior comp in CO denial → FAIL
  WA RCW §49.58.110   prior comp in WA denial → FAIL
  _is_denial          indirect rejection phrases detected
  Clean hiring        no violations → no FAILs
"""

import pytest
from backend.compliance_engine import run_compliance_checks, _is_denial

HIRING = "hiring"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _checks(result):
    return result.get("checks", [])


def _has_fail(result, keyword):
    return any(
        c["status"] == "FAIL" and keyword.lower() in c["regulation"].lower()
        for c in _checks(result)
    )


def _has_any(result, keyword):
    return any(
        c["status"] in ("FAIL", "FLAG") and keyword.lower() in c["regulation"].lower()
        for c in _checks(result)
    )


def _fail_articles(result, reg_keyword):
    return [
        c["article"]
        for c in _checks(result)
        if c["status"] == "FAIL" and reg_keyword.lower() in c["regulation"].lower()
    ]


# ── ADEA ──────────────────────────────────────────────────────────────────────

class TestADEA:
    def test_graduation_year_40_plus_denial_fails(self):
        ctx = {"graduation_year": "1984"}
        result = run_compliance_checks("Reject this candidate.", ctx, HIRING)
        assert _has_fail(result, "ADEA"), "grad year 1984 → ~42 years old — should FAIL ADEA §623"

    def test_graduation_year_just_below_40_no_adea(self):
        ctx = {"graduation_year": "2010"}
        result = run_compliance_checks("Reject this candidate.", ctx, HIRING)
        assert not _has_fail(result, "ADEA"), "grad year 2010 → below ADEA protected age threshold"

    def test_adea_not_triggered_on_approval(self):
        ctx = {"graduation_year": "1979"}
        result = run_compliance_checks("Hire this candidate.", ctx, HIRING)
        assert not _has_fail(result, "ADEA"), "approval should not trigger ADEA even with old grad year"

    def test_no_graduation_year_no_adea(self):
        ctx = {"years_of_experience": "15"}
        result = run_compliance_checks("Reject this candidate.", ctx, HIRING)
        assert not _has_fail(result, "ADEA")


# ── Title VII / HBCU ──────────────────────────────────────────────────────────

class TestTitleVIIHBCU:
    def test_hbcu_excluded_from_preferred_list_fails(self):
        ctx = {
            "university_attended": "Howard University",
            "preferred_schools_list": "MIT, Stanford, Harvard",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Title VII"), "HBCU excluded from preferred list → FAIL Title VII"

    def test_morehouse_excluded_fails(self):
        ctx = {
            "university_attended": "Morehouse",
            "preferred_schools_list": "MIT, Stanford, Cornell",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Title VII")

    def test_hbcu_on_preferred_list_no_fail(self):
        ctx = {
            "university_attended": "Howard University",
            "preferred_schools_list": "Howard University, MIT, Stanford",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "Title VII"), "HBCU on preferred list → no Title VII violation"

    def test_non_hbcu_not_flagged(self):
        ctx = {
            "university_attended": "University of Texas",
            "preferred_schools_list": "MIT, Stanford, Harvard",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "Title VII")

    def test_explicit_hbcu_keyword_triggers(self):
        ctx = {
            "university_attended": "an HBCU in Atlanta",
            "preferred_schools_list": "MIT, Stanford",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Title VII"), "'hbcu' keyword in school name should trigger Title VII"


# ── ADA ───────────────────────────────────────────────────────────────────────

class TestADA:
    def test_medical_gap_denial_fails(self):
        ctx = {"employment_gap_months": "14", "gap_reason": "medical leave"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "ADA"), "medical leave gap in denial → FAIL ADA §12112"

    def test_disability_gap_denial_fails(self):
        ctx = {"employment_gap_months": "10", "gap_reason": "disability treatment"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "ADA")

    def test_gap_without_reason_flags_not_silently_passes(self):
        ctx = {"employment_gap_months": "14", "gap_reason": "not captured"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        ada_checks = [c for c in _checks(result) if "ADA" in c["regulation"]]
        assert ada_checks, "unexplained gap should produce an ADA result (FLAG or FAIL)"
        assert any(c["status"] in ("FLAG", "FAIL") for c in ada_checks)

    def test_gap_approval_no_ada_fail(self):
        ctx = {"employment_gap_months": "18", "gap_reason": "medical leave"}
        result = run_compliance_checks("Hire this candidate.", ctx, HIRING)
        assert not _has_fail(result, "ADA"), "approval should not trigger ADA gap check"

    def test_no_gap_no_ada(self):
        ctx = {"role_applied": "software engineer"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "ADA")


# ── FCRA Employment Two-Step ──────────────────────────────────────────────────

class TestFCRAEmployment:
    def test_denial_bgcheck_no_pre_adverse_fails_604(self):
        ctx = {
            "background_check_used": "yes",
            "pre_adverse_action_notice": "not sent",
            "adverse_action_notice": "not sent",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        articles = _fail_articles(result, "FCRA")
        assert any("1681b" in a or "pre-adverse" in a.lower() for a in articles), \
            "missing pre-adverse notice → FAIL §604(b)(3) / 15 U.S.C. §1681b"

    def test_denial_bgcheck_no_final_adverse_fails_615(self):
        ctx = {
            "background_check_used": "yes",
            "pre_adverse_action_notice": "sent",
            "adverse_action_notice": "not sent",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        articles = _fail_articles(result, "FCRA")
        assert any("1681m" in a or "adverse action notice" in a.lower() for a in articles), \
            "missing final adverse notice → FAIL §615(a) / 15 U.S.C. §1681m"

    def test_denial_bgcheck_both_notices_sent_no_fcra_fail(self):
        ctx = {
            "background_check_used": "yes",
            "pre_adverse_action_notice": "sent",
            "adverse_action_notice": "sent",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "FCRA"), "both notices sent → no FCRA FAILs"

    def test_approval_no_fcra_adverse_required(self):
        ctx = {"background_check_used": "yes"}
        result = run_compliance_checks("Hire this candidate.", ctx, HIRING)
        assert not _has_fail(result, "FCRA"), "approval should not require FCRA adverse notices"

    def test_no_bgcheck_no_fcra_check(self):
        ctx = {"pre_adverse_action_notice": "not sent"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "FCRA"), "no background check → no FCRA adverse action required"


# ── NYC Local Law 144 ─────────────────────────────────────────────────────────

class TestNYCLL144:
    def test_ny_no_bias_audit_fails(self):
        ctx = {
            "screening_tool": "HireAI-v2",
            "bias_audit_on_file": "no",
            "candidate_notified": "sent",
            "applicant_location": "New York, NY",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Local Law 144"), "no bias audit in NY → FAIL LL144"

    def test_ny_no_candidate_notice_fails(self):
        ctx = {
            "screening_tool": "HireAI-v2",
            "bias_audit_on_file": "yes",
            "candidate_notified": "not sent",
            "applicant_location": "New York, NY",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Local Law 144"), "candidate not notified in NY → FAIL LL144"

    def test_ny_both_present_no_ll144_fail(self):
        ctx = {
            "screening_tool": "HireAI-v2",
            "bias_audit_on_file": "yes",
            "candidate_notified": "sent",
            "applicant_location": "New York, NY",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "Local Law 144"), "audit + notice present → no LL144 FAIL"

    def test_non_ny_no_ll144_violation_regression(self):
        """Regression: bias audit FLAG must NOT fire for non-NY candidates (fix #1)."""
        ctx = {
            "screening_tool": "HireAI-v2",
            "bias_audit_on_file": "no",
            "applicant_location": "Austin, TX",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        ll144 = [c for c in _checks(result) if "Local Law 144" in c["regulation"] and c["status"] == "FAIL"]
        assert not ll144, "non-NY applicant must never trigger NYC LL144 FAIL"

    def test_no_screening_tool_no_ll144(self):
        """LL144 only applies when an AEDT tool is in use."""
        ctx = {
            "bias_audit_on_file": "no",
            "candidate_notified": "not sent",
            "applicant_location": "New York, NY",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        ll144_fails = [c for c in _checks(result) if "Local Law 144" in c["regulation"] and c["status"] == "FAIL"]
        assert not ll144_fails, "LL144 requires a screening_tool to be in use"


# ── Illinois AIVIA ────────────────────────────────────────────────────────────

class TestILAIVIA:
    def test_il_video_no_consent_fails(self):
        ctx = {
            "interview_method": "AI video interview",
            "aivia_consent": "not obtained",
            "applicant_location": "Chicago, IL",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "AIVIA"), "IL AI video interview without consent → FAIL AIVIA"

    def test_il_hirevue_no_consent_fails(self):
        ctx = {
            "interview_method": "hirevue",
            "aivia_consent": "not obtained",
            "applicant_location": "Chicago, IL",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "AIVIA")

    def test_il_consent_obtained_no_aivia_fail(self):
        ctx = {
            "interview_method": "AI video interview",
            "aivia_consent": "yes",
            "applicant_location": "Chicago, IL",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "AIVIA"), "consent obtained → no AIVIA FAIL"

    def test_non_il_no_aivia(self):
        ctx = {
            "interview_method": "AI video interview",
            "aivia_consent": "not obtained",
            "applicant_location": "Austin, TX",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "AIVIA"), "non-IL applicant should not trigger AIVIA"


# ── Salary History Bans ───────────────────────────────────────────────────────

class TestSalaryHistoryBans:
    def test_ca_ab168_prior_comp_in_denial_fails(self):
        ctx = {"prior_compensation": "$45,000", "applicant_location": "San Francisco, CA"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "AB-168"), "prior comp used in CA denial → FAIL AB-168"

    def test_ca_ab168_approval_no_fail(self):
        ctx = {"prior_compensation": "$45,000", "applicant_location": "San Francisco, CA"}
        result = run_compliance_checks("Hire this candidate.", ctx, HIRING)
        assert not _has_fail(result, "AB-168"), "CA AB-168 only fires on denials"

    def test_ny_salary_history_ban_fails(self):
        ctx = {"prior_compensation": "$45,000", "applicant_location": "New York, NY"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Salary History"), "prior comp in NY denial → FAIL NY §194-a"

    def test_co_epewa_prior_comp_fails(self):
        ctx = {"prior_compensation": "$45,000", "applicant_location": "Denver, CO"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "EPEWA"), "prior comp in CO denial → FAIL CO EPEWA"

    def test_wa_rcw_prior_comp_fails(self):
        ctx = {"prior_compensation": "$45,000", "applicant_location": "Seattle, WA"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert _has_fail(result, "Washington"), "prior comp in WA denial → FAIL WA RCW §49.58.110"

    def test_no_prior_comp_no_salary_fail(self):
        ctx = {"applicant_location": "San Francisco, CA"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "AB-168")

    def test_tx_no_salary_ban(self):
        ctx = {"prior_compensation": "$45,000", "applicant_location": "Houston, TX"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        assert not _has_fail(result, "AB-168")
        assert not _has_fail(result, "EPEWA")
        assert not _has_fail(result, "Salary History")


# ── _is_denial indirect phrases ───────────────────────────────────────────────

class TestIsDenial:
    @pytest.mark.parametrize("phrase", [
        "we are not moving forward with your application",
        "we are moving in another direction",
        "you were not selected for this role",
        "we have decided not to proceed",
        "the position has been filled by another candidate",
        "you are not the right fit for this role",
        "we will not be extending an offer at this time",
        "your application was unsuccessful",
        "we are not advancing your candidacy",
        "we went with another candidate",
        "we will not extend an offer",
    ])
    def test_indirect_denial_detected(self, phrase):
        assert _is_denial(phrase, {}), f"should detect as denial: '{phrase}'"

    def test_direct_reject_still_works(self):
        assert _is_denial("Reject this candidate.", {})

    def test_direct_deny_still_works(self):
        assert _is_denial("Deny this application.", {})

    def test_approval_not_detected_as_denial(self):
        assert not _is_denial("Hire this candidate. Extend an offer.", {})

    def test_neutral_stage_advance_not_denial(self):
        assert not _is_denial("Move this candidate to the phone screen stage.", {})

    def test_denial_in_context_field(self):
        assert _is_denial("Reviewing application.", {"denial_decision": "reject"})


# ── Clean hiring decision ─────────────────────────────────────────────────────

class TestCleanHiring:
    def test_clean_decision_no_fails(self):
        ctx = {
            "years_of_experience": "6",
            "relevant_skills": "Python, SQL",
            "role_applied": "Data Engineer",
            "human_review_scheduled": "yes",
            "bias_audit_on_file": "yes",
            "screening_tool": "WorkdayAI",
            "candidate_notified": "sent",
            "applicant_location": "Austin, TX",
        }
        result = run_compliance_checks(
            "Advance this candidate to the phone screen stage.", ctx, HIRING
        )
        fails = [c for c in _checks(result) if c["status"] == "FAIL"]
        assert not fails, f"clean decision should have no FAILs, got: {[c['regulation'] for c in fails]}"

    def test_clean_ny_decision_with_proper_notices_no_fails(self):
        ctx = {
            "screening_tool": "WorkdayAI",
            "bias_audit_on_file": "yes",
            "candidate_notified": "sent",
            "applicant_location": "New York, NY",
            "background_check_used": "yes",
            "pre_adverse_action_notice": "sent",
            "adverse_action_notice": "sent",
        }
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        fails = [c for c in _checks(result) if c["status"] == "FAIL"]
        assert not fails, f"NY decision with all notices should have no FAILs, got: {[c['regulation'] for c in fails]}"
