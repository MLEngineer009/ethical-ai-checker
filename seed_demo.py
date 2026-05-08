#!/usr/bin/env python3
"""
Seed the demo AI system (LoanSight AI by Veridian Finance SA) directly into
the local SQLite database.  Run once before a demo to have the system
pre-registered so you can jump straight to the compliance report and
certificate — no need to click through the 5-step wizard.

Usage:
    python seed_demo.py
"""

import sys, os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.dirname(__file__))

from backend import database

DEMO_SUB = "demo_user_loansight"  # stable sub so repeated runs don't duplicate

DEMO = dict(
    google_sub=DEMO_SUB,
    system_name="LoanSight AI",
    company_name="Veridian Finance SA",
    risk_tier="high",
    use_case="Automated creditworthiness scoring for retail loan applications",
    model_version="v2.3.1 (XGBoost ensemble)",
    training_data_sources=[
        "Internal loan repayment history 2018–2023 (2.1M records)",
        "Eurosystem credit bureau data (anonymised, GDPR-compliant)",
        "Open Banking PSD2 transaction streams (24-month lookback)",
        "HMDA public dataset (bias testing reference only)",
    ],
    intended_purpose=(
        "Assess creditworthiness of retail applicants seeking consumer loans "
        "€1,000–€250,000. Generates a risk score and approve / refer / decline "
        "recommendation to assist loan officers."
    ),
    geographic_scope="EU — DE, FR, NL, BE, LU",
    # Art. 6 — high-risk Annex III category
    art6_annex_category=(
        "A.5 — Access to and enjoyment of essential private services "
        "and public services and benefits"
    ),
    # Art. 15 — accuracy
    art15_accuracy_metric="AUROC 0.87, Precision 0.83, Recall 0.81 — Q4 2024 holdout set (n=42,500)",
    art15_robustness_tested=True,
    # Art. 4 — PASS (declaration + evidence)
    art4_literacy_training=True,
    art4_literacy_training_evidence_notes=(
        "All underwriting staff completed EU AI Act literacy course Q1 2025 "
        "— ref. training-log-VF-2025-001"
    ),
    art4_literacy_training_evidence_date="2025-03-01",
    # Art. 17 — PARTIAL (declaration only, no supporting docs)
    art17_qms_documented=True,
    art17_qms_documented_evidence_notes="",
    art17_qms_documented_evidence_date="",
    # Art. 25 instructions — PASS
    art25_instructions_provided=True,
    art25_instructions_provided_evidence_notes=(
        "Deployer handbook v4.1 distributed to all EU branch managers "
        "— doc ref IFU-VF-2025-07"
    ),
    art25_instructions_provided_evidence_date="2025-07-15",
    # Art. 25 monitoring — PASS
    art25_monitoring_active=True,
    art25_monitoring_active_evidence_notes=(
        "Monthly AUROC dashboard + automated drift alerts active since Jan 2025 "
        "— ref. MON-VF-2025-001"
    ),
    art25_monitoring_active_evidence_date="2025-01-20",
    # Art. 27 FRIA — FAIL (not conducted — critical gap for high-risk Annex III)
    art27_fria_conducted=False,
    art27_fria_conducted_evidence_notes="",
    art27_fria_conducted_evidence_date="",
    # Art. 30 — PARTIAL (declared but no EU registration number yet)
    art30_eu_db_registered=True,
    art30_registration_number="",
    art30_eu_db_registered_evidence_notes="",
    art30_eu_db_registered_evidence_date="",
    # Art. 33 — PARTIAL (self-assessment declared, no certificate docs)
    art33_conformity_type="self-assessment",
    art33_conformity_type_evidence_notes="",
    art33_conformity_type_evidence_date="",
)


def main():
    database.init_db()

    # Check if demo system already exists for this sub
    existing = database.get_ai_systems(DEMO_SUB)
    if existing:
        print(f"Demo system already seeded — system_id={existing[0]['system_id']}")
        print("Run the app and log in as the demo user to view it, or delete the DB and re-seed.")
        return

    result = database.create_ai_system(**DEMO)
    sid = result["system_id"]
    print(f"Demo system seeded successfully — system_id={sid}")
    print()
    print("Compliance profile:")
    print("  Art.  4  AI Literacy          → PASS   (declaration + evidence)")
    print("  Art. 17  QMS                  → PARTIAL (declaration only)")
    print("  Art. 25  Instructions          → PASS   (declaration + evidence)")
    print("  Art. 25  Monitoring            → PASS   (declaration + evidence)")
    print("  Art. 27  FRIA                 → FAIL   (not conducted)")
    print("  Art. 30  EU DB Registration   → PARTIAL (no registration number)")
    print("  Art. 33  Conformity Assessment → PARTIAL (no certificate docs)")
    print()
    print(f"To fetch compliance: GET /ai-systems/{sid}/compliance")
    print(f"To download cert:    POST /ai-systems/{sid}/certificate")


if __name__ == "__main__":
    main()
