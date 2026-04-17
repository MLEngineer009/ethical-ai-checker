"""
Regulatory reference mapping for Pragma.

Maps (risk_flag, category) combinations to specific laws and regulations
so users understand the legal exposure behind each ethical risk flag.
"""

from typing import Any, Dict, List

# ── Law definitions ────────────────────────────────────────────────────────────

_LAWS: Dict[str, Dict[str, str]] = {
    # US Employment
    "eeoc_title_vii": {
        "name": "EEOC Title VII (Civil Rights Act 1964)",
        "jurisdiction": "US",
        "description": "Prohibits employment discrimination based on race, color, religion, sex, or national origin.",
        "url": "https://www.eeoc.gov/statutes/title-vii-civil-rights-act-1964",
    },
    "eeoc_adea": {
        "name": "EEOC ADEA (Age Discrimination in Employment Act)",
        "jurisdiction": "US",
        "description": "Prohibits discrimination against employees 40+ years old.",
        "url": "https://www.eeoc.gov/statutes/age-discrimination-employment-act-1967",
    },
    "eeoc_ada": {
        "name": "ADA (Americans with Disabilities Act)",
        "jurisdiction": "US",
        "description": "Prohibits discrimination against qualified individuals with disabilities in employment.",
        "url": "https://www.eeoc.gov/statutes/americans-disabilities-act-1990",
    },
    "eeoc_equal_pay": {
        "name": "Equal Pay Act 1963",
        "jurisdiction": "US",
        "description": "Requires equal pay for equal work regardless of sex.",
        "url": "https://www.eeoc.gov/statutes/equal-pay-act-1963",
    },
    "nlra": {
        "name": "NLRA (National Labor Relations Act)",
        "jurisdiction": "US",
        "description": "Protects employees' rights to organize and engage in collective bargaining.",
        "url": "https://www.nlrb.gov/guidance/key-reference-materials/national-labor-relations-act",
    },
    # US Finance
    "ecoa": {
        "name": "ECOA (Equal Credit Opportunity Act)",
        "jurisdiction": "US",
        "description": "Prohibits credit discrimination based on race, color, religion, national origin, sex, marital status, or age.",
        "url": "https://www.consumerfinance.gov/compliance/compliance-resources/other-applicable-requirements/equal-credit-opportunity-act/",
    },
    "fair_housing": {
        "name": "Fair Housing Act",
        "jurisdiction": "US",
        "description": "Prohibits discrimination in housing and mortgage lending based on protected characteristics.",
        "url": "https://www.hud.gov/program_offices/fair_housing_equal_opp/fair_housing_act_overview",
    },
    "fcra": {
        "name": "FCRA (Fair Credit Reporting Act)",
        "jurisdiction": "US",
        "description": "Governs how consumer credit information is collected, shared, and used.",
        "url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
    },
    "cfpb_udaap": {
        "name": "CFPB UDAAP",
        "jurisdiction": "US",
        "description": "Prohibits unfair, deceptive, or abusive acts or practices in consumer financial products.",
        "url": "https://www.consumerfinance.gov/compliance/compliance-resources/supervision-and-examination-resources/unfair-deceptive-abusive-acts-practices/",
    },
    # US Healthcare
    "hipaa": {
        "name": "HIPAA Privacy Rule",
        "jurisdiction": "US",
        "description": "Protects the privacy of individually identifiable health information.",
        "url": "https://www.hhs.gov/hipaa/for-professionals/privacy/index.html",
    },
    "aca_1557": {
        "name": "ACA Section 1557",
        "jurisdiction": "US",
        "description": "Prohibits discrimination in healthcare based on race, color, national origin, sex, age, or disability.",
        "url": "https://www.hhs.gov/civil-rights/for-individuals/section-1557/index.html",
    },
    # EU / Global
    "gdpr": {
        "name": "GDPR (General Data Protection Regulation)",
        "jurisdiction": "EU",
        "description": "Governs data protection and privacy for EU residents; requires transparency and lawful basis for processing.",
        "url": "https://gdpr-info.eu/",
    },
    "gdpr_art22": {
        "name": "GDPR Article 22 (Automated Decision-Making)",
        "jurisdiction": "EU",
        "description": "Gives individuals the right not to be subject to solely automated decisions that produce significant effects.",
        "url": "https://gdpr-info.eu/art-22-gdpr/",
    },
    "eu_ai_act": {
        "name": "EU AI Act",
        "jurisdiction": "EU",
        "description": "Classifies AI systems by risk level; high-risk AI (hiring, credit, healthcare) requires transparency, human oversight, and bias testing.",
        "url": "https://artificialintelligenceact.eu/",
    },
    "eu_equal_treatment": {
        "name": "EU Equal Treatment Directive (2000/78/EC)",
        "jurisdiction": "EU",
        "description": "Prohibits employment discrimination based on religion, belief, disability, age, or sexual orientation.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32000L0078",
    },
    # US Policy / AI
    "eo14110": {
        "name": "Executive Order 14110 (Safe AI)",
        "jurisdiction": "US",
        "description": "Directs federal agencies to manage AI risks including bias, privacy, and civil rights impacts.",
        "url": "https://www.whitehouse.gov/briefing-room/presidential-actions/2023/10/30/executive-order-on-the-safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence/",
    },
    "ftc_ai": {
        "name": "FTC AI Guidance",
        "jurisdiction": "US",
        "description": "FTC guidance on AI fairness, transparency, and avoiding deceptive or discriminatory outcomes.",
        "url": "https://www.ftc.gov/business-guidance/blog/2023/02/keep-your-ai-claims-in-check",
    },
    "ccpa": {
        "name": "CCPA (California Consumer Privacy Act)",
        "jurisdiction": "US (California)",
        "description": "Grants California residents rights over their personal data and how it is used in automated decisions.",
        "url": "https://oag.ca.gov/privacy/ccpa",
    },
}

# ── Mapping: (category, risk_flag) → list of law keys ─────────────────────────

_REFS: Dict[str, Dict[str, List[str]]] = {
    "hiring": {
        "bias":           ["eeoc_title_vii", "eeoc_adea", "eeoc_ada", "eu_ai_act", "eu_equal_treatment"],
        "discrimination": ["eeoc_title_vii", "eeoc_adea", "eeoc_ada", "eu_equal_treatment"],
        "fairness":       ["eeoc_title_vii", "eeoc_equal_pay", "eu_ai_act"],
        "transparency":   ["eu_ai_act", "gdpr_art22", "eo14110"],
        "harm":           ["eeoc_ada", "nlra", "eu_ai_act"],
    },
    "workplace": {
        "bias":           ["eeoc_title_vii", "eeoc_ada", "eeoc_adea", "eu_equal_treatment"],
        "discrimination": ["eeoc_title_vii", "eeoc_adea", "eeoc_ada"],
        "fairness":       ["eeoc_equal_pay", "nlra", "eu_equal_treatment"],
        "transparency":   ["eu_ai_act", "eo14110"],
        "harm":           ["nlra", "eeoc_ada"],
    },
    "finance": {
        "bias":           ["ecoa", "fair_housing", "cfpb_udaap", "eu_ai_act"],
        "discrimination": ["ecoa", "fair_housing", "fcra"],
        "fairness":       ["ecoa", "cfpb_udaap", "fcra"],
        "transparency":   ["fcra", "gdpr_art22", "cfpb_udaap", "eu_ai_act"],
        "harm":           ["cfpb_udaap", "ecoa"],
    },
    "healthcare": {
        "bias":           ["aca_1557", "eeoc_ada", "eu_ai_act"],
        "discrimination": ["aca_1557", "eeoc_ada"],
        "fairness":       ["aca_1557", "hipaa"],
        "transparency":   ["hipaa", "gdpr", "eu_ai_act"],
        "harm":           ["hipaa", "aca_1557"],
    },
    "policy": {
        "bias":           ["eeoc_title_vii", "eu_ai_act", "eo14110"],
        "discrimination": ["eeoc_title_vii", "eeoc_ada", "eu_equal_treatment"],
        "fairness":       ["eu_ai_act", "eo14110", "ftc_ai"],
        "transparency":   ["gdpr_art22", "eu_ai_act", "ccpa", "eo14110"],
        "harm":           ["eu_ai_act", "eo14110", "ftc_ai"],
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
        "transparency":   ["gdpr_art22", "eu_ai_act", "ccpa"],
        "harm":           ["eu_ai_act", "ftc_ai"],
    },
}


def get_regulatory_refs(risk_flags: List[str], category: str) -> List[Dict[str, Any]]:
    """
    Return a deduplicated list of regulatory references relevant to the
    given risk flags and decision category.
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
                    "law":          law["name"],
                    "jurisdiction": law["jurisdiction"],
                    "description":  law["description"],
                    "url":          law["url"],
                    "triggered_by": flag,
                })

    return refs
