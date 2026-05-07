"""
Regulatory reference mapping for Pragma.

Maps (risk_flag, category) combinations to specific laws and regulations
so users understand the legal exposure behind each ethical risk flag.

DISCLAIMER: This mapping is for informational purposes only and does not
constitute legal advice. Entries marked review_status="needs_lawyer_review"
have not been reviewed by qualified legal counsel and may be incomplete,
overbroad, or jurisdiction-specific in ways not reflected here. Always
consult a qualified lawyer before relying on these references for compliance
decisions.

EU AI Act reference: Regulation (EU) 2024/1689 of the European Parliament
and of the Council of 13 June 2024 on artificial intelligence
(OJ L, 2024/1689, 12.7.2024).
"""

from typing import Any, Dict, List

# ── Law definitions ────────────────────────────────────────────────────────────
#
# review_status values:
#   "verified"             — well-established, widely cited, stable
#   "needs_lawyer_review"  — correct in broad strokes but nuances may vary
#                            by jurisdiction, use case, or regulatory guidance
#   "auto_generated"       — programmatically added, not manually reviewed

_LAWS: Dict[str, Dict[str, str]] = {
    # ── US Employment ─────────────────────────────────────────────────────────
    "eeoc_title_vii": {
        "name": "EEOC Title VII (Civil Rights Act 1964)",
        "jurisdiction": "US",
        "description": "Prohibits employment discrimination based on race, color, religion, sex, or national origin.",
        "url": "https://www.eeoc.gov/statutes/title-vii-civil-rights-act-1964",
        "review_status": "verified",
    },
    "eeoc_adea": {
        "name": "EEOC ADEA (Age Discrimination in Employment Act)",
        "jurisdiction": "US",
        "description": "Prohibits discrimination against employees 40+ years old.",
        "url": "https://www.eeoc.gov/statutes/age-discrimination-employment-act-1967",
        "review_status": "verified",
    },
    "eeoc_ada": {
        "name": "ADA (Americans with Disabilities Act)",
        "jurisdiction": "US",
        "description": "Prohibits discrimination against qualified individuals with disabilities in employment.",
        "url": "https://www.eeoc.gov/statutes/americans-disabilities-act-1990",
        "review_status": "verified",
    },
    "eeoc_equal_pay": {
        "name": "Equal Pay Act 1963",
        "jurisdiction": "US",
        "description": "Requires equal pay for equal work regardless of sex.",
        "url": "https://www.eeoc.gov/statutes/equal-pay-act-1963",
        "review_status": "verified",
    },
    "nlra": {
        "name": "NLRA (National Labor Relations Act)",
        "jurisdiction": "US",
        "description": "Protects employees' rights to organize and engage in collective bargaining.",
        "url": "https://www.nlrb.gov/guidance/key-reference-materials/national-labor-relations-act",
        "review_status": "verified",
    },
    # ── US Finance ────────────────────────────────────────────────────────────
    "ecoa": {
        "name": "ECOA (Equal Credit Opportunity Act) / Regulation B",
        "jurisdiction": "US",
        "description": "Prohibits credit discrimination based on race, color, religion, national origin, sex, marital status, or age. 15 U.S.C. § 1691. Implemented by CFPB Regulation B (12 CFR Part 1002).",
        "url": "https://www.consumerfinance.gov/compliance/compliance-resources/other-applicable-requirements/equal-credit-opportunity-act/",
        "review_status": "verified",
    },
    "fair_housing": {
        "name": "Fair Housing Act (42 U.S.C. §§ 3601–3619)",
        "jurisdiction": "US",
        "description": "Prohibits discrimination in housing and mortgage lending based on race, color, national origin, religion, sex, familial status, or disability.",
        "url": "https://www.hud.gov/program_offices/fair_housing_equal_opp/fair_housing_act_overview",
        "review_status": "verified",
    },
    "fcra": {
        "name": "FCRA (Fair Credit Reporting Act)",
        "jurisdiction": "US",
        "description": "Governs how consumer credit information is collected, shared, and used. Requires adverse action notices when credit decisions are based on consumer reports.",
        "url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        "review_status": "verified",
    },
    "cfpb_udaap": {
        "name": "CFPB UDAAP (Dodd-Frank Act §§ 1031–1036)",
        "jurisdiction": "US",
        "description": "Prohibits unfair, deceptive, or abusive acts or practices in consumer financial products. Applies to AI-driven decisioning that causes substantial consumer harm.",
        "url": "https://www.consumerfinance.gov/compliance/compliance-resources/supervision-and-examination-resources/unfair-deceptive-abusive-acts-practices/",
        "review_status": "verified",
    },
    # ── US Healthcare ─────────────────────────────────────────────────────────
    "hipaa": {
        "name": "HIPAA Privacy Rule (45 CFR Parts 160, 164)",
        "jurisdiction": "US",
        "description": "Protects the privacy of individually identifiable health information held by covered entities and business associates.",
        "url": "https://www.hhs.gov/hipaa/for-professionals/privacy/index.html",
        "review_status": "verified",
    },
    "aca_1557": {
        "name": "ACA Section 1557 (42 U.S.C. § 18116)",
        "jurisdiction": "US",
        "description": "Prohibits discrimination in healthcare programmes receiving federal financial assistance on grounds of race, color, national origin, sex, age, or disability.",
        "url": "https://www.hhs.gov/civil-rights/for-individuals/section-1557/index.html",
        "review_status": "verified",
    },
    # ── EU / Global ───────────────────────────────────────────────────────────
    "gdpr": {
        "name": "GDPR (Regulation (EU) 2016/679)",
        "jurisdiction": "EU / EEA",
        "description": "Governs data protection and privacy for EU/EEA residents. Requires a lawful basis for processing, data minimisation, and transparency. Applies to any organisation processing data of EU residents regardless of establishment.",
        "url": "https://gdpr-info.eu/",
        "review_status": "verified",
    },
    "gdpr_art22": {
        "name": "GDPR Article 22 — Automated Decision-Making",
        "jurisdiction": "EU / EEA",
        "description": "Gives individuals the right not to be subject to solely automated decisions that produce legal or similarly significant effects. Requires human oversight, explanation, and the right to contest decisions.",
        "url": "https://gdpr-info.eu/art-22-gdpr/",
        "review_status": "verified",
    },
    # Generic EU AI Act entry — used when no specific article is identified
    "eu_ai_act": {
        "name": "EU AI Act (Regulation (EU) 2024/1689)",
        "jurisdiction": "EU",
        "description": "Risk-based framework for AI systems placed on or used in the EU market. High-risk AI (hiring, credit, healthcare, law enforcement) must meet transparency, accuracy, and human oversight requirements. Phased enforcement: prohibited practices from Aug 2025, high-risk obligations from Aug 2026.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
        "review_status": "verified",
    },
    # Article-specific EU AI Act entries
    "eu_ai_act_art5": {
        "name": "EU AI Act Art. 5 — Prohibited AI Practices",
        "jurisdiction": "EU",
        "description": "Prohibits real-time remote biometric ID in public spaces, social scoring by public authorities, subliminal manipulation, and exploitation of vulnerabilities. Applies from 2 August 2025. Art. 5(1)(h) contains narrow law-enforcement exceptions.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
        # LAWYER REVIEW NEEDED: The law-enforcement exceptions in Art. 5(1)(h)
        # are context-dependent and require case-by-case legal analysis.
        "review_status": "needs_lawyer_review",
    },
    "eu_ai_act_art6": {
        "name": "EU AI Act Art. 6 — High-Risk AI Classification",
        "jurisdiction": "EU",
        "description": "Systems listed in Annex III are high-risk and subject to mandatory conformity assessment, technical documentation, and human oversight. Covers biometrics, employment, education, essential services, law enforcement, and justice.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
        "review_status": "needs_lawyer_review",
    },
    "eu_ai_act_art9": {
        "name": "EU AI Act Art. 9 — Risk Management System",
        "jurisdiction": "EU",
        "description": "Requires a continuous risk management process throughout the AI system lifecycle, including identification and analysis of risks, testing, and residual risk assessment.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
        # LAWYER REVIEW NEEDED: Art. 9 requires documented risk management
        # processes; Pragma's heuristic (10+ evaluations) is not a legal standard.
        "review_status": "needs_lawyer_review",
    },
    "eu_ai_act_art13": {
        "name": "EU AI Act Art. 13 — Transparency",
        "jurisdiction": "EU",
        "description": "High-risk AI systems must be designed to enable deployers to interpret outputs and use the system appropriately. Instructions for use must include capabilities, limitations, and human oversight measures.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
        "review_status": "needs_lawyer_review",
    },
    "eu_ai_act_art14": {
        "name": "EU AI Act Art. 14 — Human Oversight",
        "jurisdiction": "EU",
        "description": "High-risk AI systems must allow natural persons to effectively oversee, understand, and intervene or halt operation. Deployers must assign oversight to competent individuals.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
        "review_status": "needs_lawyer_review",
    },
    "eu_equal_treatment": {
        "name": "EU Equal Treatment Directive (2000/78/EC)",
        "jurisdiction": "EU",
        "description": "Prohibits employment discrimination based on religion or belief, disability, age, or sexual orientation. Implemented in national law across all EU member states.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32000L0078",
        "review_status": "verified",
    },
    # ── US Policy / AI ────────────────────────────────────────────────────────
    "eo14110": {
        "name": "Executive Order 14110 (Safe, Secure, and Trustworthy AI)",
        "jurisdiction": "US (Federal)",
        "description": "Directs federal agencies to manage AI risks including bias, privacy, and civil rights impacts. Non-binding on private sector but signals regulatory intent.",
        "url": "https://www.whitehouse.gov/briefing-room/presidential-actions/2023/10/30/executive-order-on-the-safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence/",
        "review_status": "verified",
    },
    "ftc_ai": {
        "name": "FTC AI Guidance",
        "jurisdiction": "US",
        "description": "FTC guidance on AI fairness, transparency, and avoiding deceptive or discriminatory outcomes. FTC Act Section 5 prohibits unfair or deceptive acts; the FTC has signalled enforcement against biased AI.",
        "url": "https://www.ftc.gov/business-guidance/blog/2023/02/keep-your-ai-claims-in-check",
        "review_status": "verified",
    },
    "ccpa": {
        "name": "CCPA / CPRA (California Consumer Privacy Act)",
        "jurisdiction": "US (California)",
        "description": "Grants California residents rights over their personal data, including the right to opt out of sale and to limit use of sensitive personal information in automated decisions. Enforced by the California Privacy Protection Agency.",
        "url": "https://oag.ca.gov/privacy/ccpa",
        "review_status": "verified",
    },
    "nyc_ll144": {
        "name": "NYC Local Law 144 (Automated Employment Decision Tools)",
        "jurisdiction": "US (New York City)",
        "description": "Requires NYC employers using automated employment decision tools to conduct annual bias audits and notify candidates. Applies to hiring and promotion decisions affecting NYC residents.",
        "url": "https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page",
        "review_status": "verified",
    },
}

# ── Mapping: (category, risk_flag) → list of law keys ─────────────────────────

_REFS: Dict[str, Dict[str, List[str]]] = {
    "hiring": {
        "bias":           ["eeoc_title_vii", "eeoc_adea", "eeoc_ada", "eu_ai_act_art6", "eu_equal_treatment", "nyc_ll144"],
        "discrimination": ["eeoc_title_vii", "eeoc_adea", "eeoc_ada", "eu_equal_treatment", "nyc_ll144"],
        "fairness":       ["eeoc_title_vii", "eeoc_equal_pay", "eu_ai_act_art13"],
        "transparency":   ["eu_ai_act_art13", "eu_ai_act_art14", "gdpr_art22", "eo14110"],
        "harm":           ["eeoc_ada", "nlra", "eu_ai_act_art9"],
    },
    "workplace": {
        "bias":           ["eeoc_title_vii", "eeoc_ada", "eeoc_adea", "eu_equal_treatment"],
        "discrimination": ["eeoc_title_vii", "eeoc_adea", "eeoc_ada"],
        "fairness":       ["eeoc_equal_pay", "nlra", "eu_equal_treatment"],
        "transparency":   ["eu_ai_act_art13", "eo14110"],
        "harm":           ["nlra", "eeoc_ada"],
    },
    "finance": {
        "bias":           ["ecoa", "fair_housing", "cfpb_udaap", "eu_ai_act_art6"],
        "discrimination": ["ecoa", "fair_housing", "fcra"],
        "fairness":       ["ecoa", "cfpb_udaap", "fcra"],
        "transparency":   ["fcra", "gdpr_art22", "cfpb_udaap", "eu_ai_act_art13"],
        "harm":           ["cfpb_udaap", "ecoa"],
    },
    "healthcare": {
        "bias":           ["aca_1557", "eeoc_ada", "eu_ai_act_art6"],
        "discrimination": ["aca_1557", "eeoc_ada"],
        "fairness":       ["aca_1557", "hipaa"],
        "transparency":   ["hipaa", "gdpr", "eu_ai_act_art13"],
        "harm":           ["hipaa", "aca_1557"],
    },
    "policy": {
        "bias":           ["eeoc_title_vii", "eu_ai_act_art9", "eo14110"],
        "discrimination": ["eeoc_title_vii", "eeoc_ada", "eu_equal_treatment"],
        "fairness":       ["eu_ai_act_art13", "eo14110", "ftc_ai"],
        "transparency":   ["gdpr_art22", "eu_ai_act_art13", "ccpa", "eo14110"],
        "harm":           ["eu_ai_act_art9", "eo14110", "ftc_ai"],
    },
    "personal": {
        "bias":           ["gdpr", "ccpa"],
        "discrimination": ["eeoc_title_vii"],
        "fairness":       [],
        "transparency":   ["gdpr", "ccpa"],
        "harm":           [],
    },
    "other": {
        "bias":           ["eu_ai_act", "ftc_ai", "eo14110"],
        "discrimination": ["eeoc_title_vii", "eu_equal_treatment"],
        "fairness":       ["eu_ai_act", "ftc_ai"],
        "transparency":   ["gdpr_art22", "eu_ai_act_art13", "ccpa"],
        "harm":           ["eu_ai_act", "ftc_ai"],
    },
}


def get_regulatory_refs(risk_flags: List[str], category: str) -> List[Dict[str, Any]]:
    """
    Return a deduplicated list of regulatory references relevant to the
    given risk flags and decision category.

    Note: These references are informational only. See module docstring.
    """
    cat_map = _REFS.get(category, _REFS["other"])
    seen: set = set()
    refs: List[Dict[str, Any]] = []

    for flag in risk_flags:
        for law_key in cat_map.get(flag, []):
            if law_key not in seen:
                seen.add(law_key)
                law = _LAWS[law_key]
                refs.append({
                    "law":           law["name"],
                    "jurisdiction":  law["jurisdiction"],
                    "description":   law["description"],
                    "url":           law["url"],
                    "triggered_by":  flag,
                    "review_status": law.get("review_status", "needs_lawyer_review"),
                })

    return refs
