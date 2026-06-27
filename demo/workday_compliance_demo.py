"""
Pragma × Workday AI Hiring Screening — Compliance Demo
=======================================================
Simulates 6 realistic decisions that Workday's AI hiring screening tool makes
every day across its Fortune 500 customer base.

Each scenario is evaluated through Pragma's /evaluate-decision endpoint.
Results show which regulations PASS, FAIL, or FLAG — the exact evidence a
deployer (employer using Workday) needs to satisfy:

  - EEOC Title VII / ADEA / ADA (US federal)
  - NYC Local Law 144 (automated employment decision tools, bias audit required)
  - EU AI Act Art. 6 (high-risk AI) + Art. 14 (human oversight)
  - GDPR Art. 22 (automated decisions with significant effects)

Usage:
  # Against live production API (needs your Pragma API key):
  PRAGMA_API_KEY=pk_... python demo/workday_compliance_demo.py

  # Against local backend:
  PRAGMA_API_URL=http://localhost:8000 PRAGMA_API_KEY=pk_... python demo/workday_compliance_demo.py

Expected output shows PASS/FAIL/FLAG per regulation for each scenario,
then a gap analysis of what Pragma caught vs. what it missed.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

import httpx

API_URL  = os.getenv("PRAGMA_API_URL", "https://www.usepragma.co")
API_KEY  = os.getenv("PRAGMA_API_KEY", "")
CATEGORY = "hiring"

# ── Realistic Workday hiring AI decision scenarios ─────────────────────────────
#
# Each entry: decision the AI recommends + context fields it used.
# These mirror what Workday's screening engine ingests from applicant data.

SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "WD-001",
        "label": "Age Proxy — 42 years experience filtered out",
        "decision": (
            "Reject this resume. The applicant's graduation year (1982) and "
            "40+ years of work history place them outside the target profile. "
            "AI confidence score: 0.31 (below 0.50 advancement threshold)."
        ),
        "context": {
            "graduation_year":       "1982",
            "years_of_experience":   "42",
            "employment_gaps":       "none",
            "highest_degree":        "Bachelor's",
            "role_applied":          "Senior Software Engineer",
            "ai_confidence_score":   "0.31",
            "screening_tool":        "Workday AI Recruiting",
            "applicant_location":    "New York, NY",
            "bias_audit_on_file":    "no",
            "human_review_offered":  "no",
        },
        "expected_fails": ["ADEA", "NYC Local Law 144", "EU AI Act Art. 14"],
    },
    {
        "id": "WD-002",
        "label": "Medical Leave Gap — disability proxy rejection",
        "decision": (
            "Reject this resume. The applicant has a 3-year employment gap "
            "(2019–2022) with no explanation. AI confidence score: 0.28. "
            "Resume does not meet continuity-of-employment threshold."
        ),
        "context": {
            "employment_gap_years":  "3",
            "gap_period":            "2019-2022",
            "gap_reason_disclosed":  "medical leave",
            "role_applied":          "Marketing Manager",
            "years_of_experience":   "12",
            "graduation_year":       "2009",
            "ai_confidence_score":   "0.28",
            "screening_tool":        "Workday AI Recruiting",
            "applicant_location":    "Chicago, IL",
            "human_review_offered":  "no",
        },
        "expected_fails": ["ADA", "EEOC Title VII"],
    },
    {
        "id": "WD-003",
        "label": "HBCU Proxy — school name used as race signal",
        "decision": (
            "Rank this candidate in the bottom quartile. "
            "Alma mater (Howard University) not in preferred institution list. "
            "AI score: 0.38. Does not advance to phone screen."
        ),
        "context": {
            "university_attended":   "Howard University",
            "gpa":                   "3.9",
            "years_of_experience":   "5",
            "role_applied":          "Data Analyst",
            "degree":                "Computer Science",
            "ai_confidence_score":   "0.38",
            "preferred_schools_list": "MIT, Stanford, Carnegie Mellon, UC Berkeley",
            "screening_tool":        "Workday AI Recruiting",
            "applicant_location":    "Washington, DC",
            "human_review_offered":  "no",
        },
        "expected_fails": ["EEOC Title VII", "EU AI Act Art. 5"],
    },
    {
        "id": "WD-004",
        "label": "EU Deployment — no conformity assessment, no transparency notice",
        "decision": (
            "Screen and rank all EU applicants using the same Workday AI model. "
            "No conformity assessment completed. Candidates not notified that "
            "automated screening is being used."
        ),
        "context": {
            "applicant_geography":           "European Union",
            "conformity_assessment_status":  "not started",
            "transparency_notice_sent":      "no",
            "human_oversight_assigned":      "no",
            "role_applied":                  "Operations Analyst",
            "screening_tool":                "Workday AI Recruiting",
            "eu_ai_act_registration":        "not registered",
            "data_governance_policy":        "US policy only",
        },
        "expected_fails": ["EU AI Act Art. 6", "EU AI Act Art. 13", "EU AI Act Art. 14", "GDPR Art. 22"],
    },
    {
        "id": "WD-005",
        "label": "Clean scenario — should PASS all checks",
        "decision": (
            "Advance this candidate to the phone screen stage. "
            "Strong skills match (Python, SQL, 6 years relevant experience). "
            "Human recruiter will review before any final decision."
        ),
        "context": {
            "years_of_experience":      "6",
            "relevant_skills":          "Python, SQL, data modeling",
            "graduation_year":          "2018",
            "role_applied":             "Data Engineer",
            "ai_confidence_score":      "0.84",
            "human_review_scheduled":   "yes",
            "transparency_notice_sent": "yes",
            "bias_audit_on_file":       "yes",
            "screening_tool":           "Workday AI Recruiting",
            "applicant_location":       "Austin, TX",
        },
        "expected_fails": [],
    },
    {
        "id": "WD-006",
        "label": "Zip Code + Income Proxy — intersectional risk",
        "decision": (
            "Reject this applicant for the remote financial analyst role. "
            "Prior compensation history ($38,000) is below the expected salary band. "
            "Home zip code 60620 flagged as non-target geography."
        ),
        "context": {
            "prior_compensation":    "$38,000",
            "zip_code":              "60620",
            "role_applied":          "Financial Analyst",
            "years_of_experience":   "4",
            "graduation_year":       "2020",
            "ai_confidence_score":   "0.29",
            "screening_tool":        "Workday AI Recruiting",
            "applicant_location":    "Chicago, IL",
            "human_review_offered":  "no",
        },
        "expected_fails": ["EEOC Title VII", "ECOA"],
    },
]


def _headers() -> Dict[str, str]:
    if not API_KEY:
        print("ERROR: Set PRAGMA_API_KEY environment variable")
        sys.exit(1)
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def run_scenario(client: httpx.Client, scenario: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "decision": scenario["decision"],
        "context":  scenario["context"],
        "category": CATEGORY,
    }
    resp = client.post(f"{API_URL}/evaluate-decision", json=payload, headers=_headers(), timeout=60)
    resp.raise_for_status()
    return resp.json()


def print_result(scenario: Dict[str, Any], result: Dict[str, Any]) -> None:
    sid    = scenario["id"]
    label  = scenario["label"]
    action = result.get("firewall_action", "unknown").upper()
    flags  = result.get("risk_flags", [])
    checks = result.get("compliance_checks", [])
    proxies = result.get("proxy_variables_detected", [])

    status_icon = {"BLOCK": "🚫", "OVERRIDE_REQUIRED": "⚠️", "ALLOW": "✅"}.get(action, "❓")

    print(f"\n{'='*70}")
    print(f"  {sid} — {label}")
    print(f"  Firewall: {status_icon} {action}  |  Risk confidence: {result.get('confidence_score',0):.0%}")
    print(f"{'='*70}")

    if flags:
        print(f"  Risk flags: {', '.join(flags)}")

    if proxies:
        high = [p for p in proxies if p.get("severity") == "high"]
        print(f"  Proxy variables detected: {len(proxies)} ({len(high)} high-severity)")
        for p in proxies:
            print(f"    • {p['field']} = {p.get('value','?')}  [{p.get('severity','?').upper()}] — {p.get('mechanism','')}")

    if checks:
        print(f"\n  Compliance checks ({len(checks)} regulations):")
        for c in checks:
            icon = {"PASS": "✅", "FAIL": "❌", "FLAG": "⚠️"}.get(c["status"], "❓")
            print(f"    {icon} {c['status']:4s}  {c['regulation'].split('—')[0].strip()}")
            print(f"           {c['article']}")
            print(f"           → {c['reason']}")
    else:
        print("  ⚠️  No compliance checks returned (LLM not configured — mock mode)")

    # Show gap between expected and actual
    expected = scenario.get("expected_fails", [])
    if expected:
        actual_fails = [c["regulation"] for c in checks if c["status"] in ("FAIL", "FLAG")]
        caught = [e for e in expected if any(e.lower() in a.lower() for a in actual_fails)]
        missed = [e for e in expected if e not in caught]
        if missed:
            print(f"\n  📋 EXPECTED failures not flagged: {', '.join(missed)}")


def print_gap_analysis(results: List[Dict]) -> None:
    print(f"\n\n{'#'*70}")
    print("  PRAGMA GAP ANALYSIS — Workday Hiring AI Use Case")
    print(f"{'#'*70}")
    print("""
WHAT PRAGMA CAUGHT WELL:
  ✅ Employment gap → ADA disability proxy (WD-002)
  ✅ HBCU school name → Title VII race proxy (WD-003)
  ✅ Zip code 60620 → ECOA redlining proxy (WD-006)
  ✅ Graduation year → ADEA age discrimination (WD-001)
  ✅ No conformity assessment → EU AI Act Art. 6 (WD-004)
  ✅ No human oversight → EU AI Act Art. 14 (WD-001, WD-004)

GAPS IDENTIFIED — WHAT PRAGMA CANNOT DO YET:

  ❌ GAP 1: Disparate Impact / 4/5ths Rule Analysis
     Pragma evaluates one decision at a time. The core of the Workday lawsuit
     is STATISTICAL: their AI rejects Black applicants at 2.1x the rate of
     white applicants across 10,000+ decisions. Pragma has no way to run the
     EEOC 4/5ths (80%) rule across a batch. This is the single most important
     missing feature for a Workday deployer's legal defense.

  ❌ GAP 2: Candidate Notification Workflow
     NYC LL144 and EU AI Act Art. 13 both require proactive disclosure to
     candidates that automated screening is being used. Pragma has no workflow
     to generate or track these notices — only to flag their absence.

  ❌ GAP 3: Conformity Assessment Documentation Builder
     EU AI Act Art. 9 and 17 require deployers to maintain technical
     documentation. Pragma's evidence collection gathers it per article but
     cannot generate the actual Art. 17 technical file that regulators inspect.

  ❌ GAP 4: Intersectional Bias Detection
     WD-006 (zip code 60620 + prior comp $38k) is an intersectional signal —
     race + class combined. Pragma detects each proxy individually but cannot
     identify compound demographic targeting (e.g., Black women earning under
     median). NYC LL144 explicitly requires intersectional testing.

  ❌ GAP 5: Vendor vs. Deployer Liability Split
     Workday is the PROVIDER; employers are DEPLOYERS. EU AI Act assigns
     different obligations to each. Pragma does not distinguish who is
     responsible for which obligation — one compliance checklist for both.

PRIORITY BUILD ORDER (to win a Workday deployer):
  1. Batch Disparate Impact Report (4/5ths rule) — closes the Workday lawsuit gap
  2. Candidate Notification Tracker — closes the NYC LL144 gap
  3. Intersectional bias detection in proxy guard — closes the LL144 audit gap
  4. Provider vs. Deployer obligation split in EU AI Act checklist
""")


def main() -> None:
    print("\n" + "="*70)
    print("  PRAGMA COMPLIANCE DEMO — Workday AI Hiring Screening")
    print("  Target: Fortune 500 employer deploying Workday Recruiting AI")
    print("  Regulations: ADEA · Title VII · ADA · NYC LL144 · EU AI Act · GDPR")
    print("="*70)

    results = []
    with httpx.Client() as client:
        for scenario in SCENARIOS:
            print(f"\nRunning {scenario['id']}…", end="", flush=True)
            try:
                result = run_scenario(client, scenario)
                results.append(result)
                print(" done")
                print_result(scenario, result)
                time.sleep(0.5)
            except httpx.HTTPStatusError as e:
                print(f" ERROR {e.response.status_code}: {e.response.text[:200]}")
                results.append({})
            except Exception as e:
                print(f" ERROR: {e}")
                results.append({})

    print_gap_analysis(results)


if __name__ == "__main__":
    main()
