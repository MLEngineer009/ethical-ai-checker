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
  TX TCHRA            Texas candidate flagged
  MA CORI             criminal check at initial stage → FAIL
  MA MEPA             prior comp in MA denial → FAIL
  NJ Opp to Compete   criminal check at initial stage → FAIL
  NJ Equal Pay        prior comp in NJ denial → FAIL
  Ban-the-box         criminal history auto-deny, no individualized assessment → FAIL
  Ban-the-box         arrest record used as denial factor → FAIL
  Ban-the-box         individualized assessment completed → PASS
  Ban-the-box         no criminal check → PASS
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


# ── New State Laws: TX, MA, NJ ─────────────────────────────────────────────────

class TestTexasLaws:
    def test_tx_candidate_gets_tchra_flag(self):
        ctx = {
            "applicant_location": "Houston, TX",
            "screening_tool": "HireVue",
            "graduation_year": "2010",
        }
        result = run_compliance_checks(
            "Reject applicant — does not meet threshold.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result)]
        assert any("TCHRA" in r or "Texas" in r for r in regs), \
            "Texas candidate should trigger TCHRA flag"

    def test_tx_ai_tool_gets_eeoc_guidance_flag(self):
        ctx = {
            "applicant_location": "Dallas, TX",
            "screening_tool": "Greenhouse AI",
        }
        result = run_compliance_checks(
            "Reject applicant — AI score below threshold.", ctx, HIRING
        )
        all_statuses = [c["status"] for c in _checks(result)]
        assert "FLAG" in all_statuses, "TX AI tool denial should trigger at least one FLAG"


class TestMassachusettsLaws:
    def test_ma_cori_criminal_check_at_initial_stage_fails(self):
        ctx = {
            "applicant_location": "Boston, MA",
            "criminal_history_check": "yes",
            "application_stage": "initial application",
        }
        result = run_compliance_checks(
            "Reject applicant — criminal record found.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("CORI" in r or "Massachusetts" in r for r in regs), \
            "MA criminal check at initial stage should FAIL CORI"

    def test_ma_mepa_prior_comp_fails(self):
        ctx = {
            "applicant_location": "Cambridge, MA",
            "prior_compensation": "95000",
        }
        result = run_compliance_checks(
            "Reject applicant — compensation expectations too high.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("MEPA" in r or "Massachusetts Equal Pay" in r for r in regs), \
            "MA prior comp in denial should FAIL MEPA"

    def test_ma_fepa_flag_always_present(self):
        ctx = {"applicant_location": "Worcester, MA"}
        result = run_compliance_checks("Advance to interview.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result)]
        assert any("FEPA" in r or "Massachusetts Fair" in r for r in regs), \
            "MA candidate should always get FEPA FLAG"


class TestNewJerseyLaws:
    def test_nj_btb_criminal_check_at_application_fails(self):
        ctx = {
            "applicant_location": "Newark, NJ",
            "criminal_history_check": "ran",
            "application_stage": "initial",
        }
        result = run_compliance_checks(
            "Reject applicant — background hit.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Opportunity to Compete" in r or "New Jersey" in r for r in regs), \
            "NJ criminal check at initial stage should FAIL Opportunity to Compete Act"

    def test_nj_equal_pay_prior_comp_fails(self):
        ctx = {
            "applicant_location": "Jersey City, NJ",
            "prior_compensation": "78000",
        }
        result = run_compliance_checks(
            "Reject applicant — salary expectations exceed band.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("NJ Equal Pay" in r or "New Jersey Equal Pay" in r for r in regs), \
            "NJ prior comp in denial should FAIL NJ Equal Pay Act"

    def test_njlad_flag_always_present(self):
        ctx = {"applicant_location": "Trenton, NJ"}
        result = run_compliance_checks("Advance candidate to phone screen.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result)]
        assert any("NJLAD" in r or "Law Against Discrimination" in r for r in regs), \
            "NJ candidate should always get NJLAD FLAG"


# ── Ban-the-box ────────────────────────────────────────────────────────────────

class TestBanTheBox:
    def test_no_criminal_check_passes(self):
        ctx = {"applicant_location": "Boston, MA"}
        result = run_compliance_checks("Reject applicant.", ctx, HIRING)
        btb = [c for c in _checks(result) if "Fair Chance" in c.get("regulation", "") or "Ban" in c.get("regulation", "")]
        fails = [c for c in btb if c["status"] == "FAIL"]
        assert not fails, "No criminal check → ban-the-box should PASS"

    def test_auto_denial_without_individualized_assessment_fails(self):
        ctx = {
            "applicant_location": "Chicago, IL",
            "criminal_history_check": "yes",
            "criminal_history_used": "yes",
            "individualized_assessment": "not conducted",
        }
        result = run_compliance_checks(
            "Reject applicant — criminal record found.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Criminal History" in r or "Fair Chance" in r for r in regs), \
            "Auto-denial without individualized assessment should FAIL"

    def test_arrest_record_as_denial_factor_fails(self):
        ctx = {
            "applicant_location": "Seattle, WA",
            "criminal_history_check": "yes",
            "arrest_record_used": "yes",
        }
        result = run_compliance_checks(
            "Reject applicant — arrest on record.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Arrest" in r or "Criminal History" in r for r in regs), \
            "Using arrest record as denial factor should FAIL"

    def test_btb_initial_stage_in_btb_state_fails(self):
        ctx = {
            "applicant_location": "Los Angeles, CA",
            "criminal_history_check": "ran",
            "application_stage": "initial application",
        }
        result = run_compliance_checks(
            "Reject applicant — criminal record.", ctx, HIRING
        )
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Ban-the-Box" in r or "Fair Chance" in r for r in regs), \
            "Criminal check at initial stage in ban-the-box state should FAIL"

    def test_individualized_assessment_completed_passes(self):
        ctx = {
            "applicant_location": "Denver, CO",
            "criminal_history_check": "yes",
            "criminal_history_used": "yes",
            "individualized_assessment": "completed",
            "job_related_justification": "Position involves financial access; fraud conviction is directly relevant.",
        }
        result = run_compliance_checks(
            "Reject applicant — criminal record directly related to job duties.", ctx, HIRING
        )
        btb_checks = [c for c in _checks(result)
                      if "Criminal History" in c.get("regulation", "") or "Fair Chance" in c.get("regulation", "")]
        fails = [c for c in btb_checks if c["status"] == "FAIL"]
        assert not fails, f"Individualized assessment done → no FAIL, got: {[c['reason'] for c in fails]}"


# ── New States: OR, CT, MN, DC, MD + IL pay transparency ──────────────────────

class TestOregonLaws:
    def test_or_salary_history_ban_fails(self):
        ctx = {"applicant_location": "Portland, OR", "prior_compensation": "82000"}
        result = run_compliance_checks("Reject applicant — comp expectations too high.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Oregon Equal Pay" in r for r in regs), "OR prior comp in denial should FAIL"

    def test_or_fair_chance_initial_stage_fails(self):
        ctx = {
            "applicant_location": "Salem, OR",
            "criminal_history_check": "ran",
            "application_stage": "initial application",
        }
        result = run_compliance_checks("Reject — background hit.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Oregon Fair Chance" in r for r in regs), "OR criminal check at initial stage should FAIL"


class TestConnecticutLaws:
    def test_ct_salary_history_ban_fails(self):
        ctx = {"applicant_location": "Stamford, CT", "prior_compensation": "110000"}
        result = run_compliance_checks("Reject — salary history exceeds band.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Connecticut Salary" in r for r in regs), "CT salary history should FAIL"

    def test_ct_pay_range_disclosure_flag(self):
        ctx = {
            "applicant_location": "Hartford, CT",
            "job_posting": "yes",
            "salary_range_disclosed": "not included",
        }
        result = run_compliance_checks("Advance to interview.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FLAG"]
        assert any("Connecticut Pay Range" in r for r in regs), "CT missing pay range should FLAG"

    def test_ct_ban_the_box_initial_stage_fails(self):
        ctx = {
            "applicant_location": "New Haven, CT",
            "criminal_history_check": "obtained",
            "application_stage": "resume screening",
        }
        result = run_compliance_checks("Reject — background check returned hit.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Connecticut Fair Chance" in r or "Ban-the-Box" in r for r in regs), \
            "CT criminal check at resume stage should FAIL"


class TestMinnesotaLaws:
    def test_mn_salary_history_ban_fails(self):
        ctx = {"applicant_location": "Minneapolis, MN", "prior_compensation": "95000"}
        result = run_compliance_checks("Reject — prior comp above band.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Minnesota Salary" in r for r in regs), "MN salary history should FAIL"

    def test_mn_pay_transparency_flag(self):
        ctx = {
            "applicant_location": "Saint Paul, MN",
            "job_posting": "yes",
            "salary_range_disclosed": "not posted",
        }
        result = run_compliance_checks("Advance to interview.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FLAG"]
        assert any("Minnesota Pay Transparency" in r for r in regs), "MN missing pay range should FLAG"

    def test_mn_ban_the_box_initial_stage_fails(self):
        ctx = {
            "applicant_location": "Duluth, MN",
            "criminal_history_check": "ran",
            "application_stage": "initial",
        }
        result = run_compliance_checks("Reject — criminal record.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Minnesota Ban-the-Box" in r for r in regs), "MN criminal check at initial stage should FAIL"


class TestDCLaws:
    def test_dc_salary_history_ban_fails(self):
        ctx = {"applicant_location": "Washington DC", "prior_compensation": "130000"}
        result = run_compliance_checks("Reject — comp history exceeds band.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("DC Salary History" in r for r in regs), "DC salary history should FAIL"

    def test_dc_fair_criminal_screening_fails(self):
        ctx = {
            "applicant_location": "Washington DC",
            "criminal_history_check": "yes",
            "application_stage": "initial application",
        }
        result = run_compliance_checks("Reject — background check.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("DC Fair Criminal Record" in r or "Ban-the-Box" in r for r in regs), \
            "DC criminal check before conditional offer should FAIL"

    def test_dc_wage_transparency_flag(self):
        ctx = {
            "applicant_location": "Washington D.C.",
            "job_posting": "yes",
            "salary_range_disclosed": "not included",
        }
        result = run_compliance_checks("Advance to first round.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FLAG"]
        assert any("DC Wage Transparency" in r for r in regs), "DC missing pay range should FLAG"


class TestMarylandLaws:
    def test_md_ban_the_box_initial_stage_fails(self):
        ctx = {
            "applicant_location": "Baltimore, MD",
            "criminal_history_check": "ran",
            "application_stage": "initial application",
        }
        result = run_compliance_checks("Reject — background check.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Maryland Job Applicant" in r for r in regs), "MD criminal check at initial stage should FAIL"

    def test_md_pay_transparency_flag(self):
        ctx = {
            "applicant_location": "Bethesda, MD",
            "job_posting": "yes",
            "salary_range_disclosed": "not posted",
        }
        result = run_compliance_checks("Advance to interview.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FLAG"]
        assert any("Maryland Pay Transparency" in r for r in regs), "MD missing pay range should FLAG"

    def test_md_facial_recognition_disclosure_fails(self):
        ctx = {
            "applicant_location": "Annapolis, MD",
            "facial_analysis_used": "HireVue facial analysis",
            "candidate_notified": "not sent",
        }
        result = run_compliance_checks("Reject — video interview score low.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FAIL"]
        assert any("Maryland Facial Recognition" in r for r in regs), \
            "MD facial recognition without disclosure should FAIL"


class TestILPayTransparency:
    def test_il_pay_scale_in_posting_flag(self):
        ctx = {
            "applicant_location": "Chicago, IL",
            "job_posting": "yes",
            "salary_range_disclosed": "not included",
        }
        result = run_compliance_checks("Advance to phone screen.", ctx, HIRING)
        regs = [c["regulation"] for c in _checks(result) if c["status"] == "FLAG"]
        assert any("Illinois Equal Pay" in r or "Pay Scale" in r for r in regs), \
            "IL job posting without pay scale should FLAG"
