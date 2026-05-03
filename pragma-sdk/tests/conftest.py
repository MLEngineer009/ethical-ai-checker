import pytest

ALLOW_RESPONSE = {
    "firewall_action": "allow",
    "should_block": False,
    "confidence_score": 0.1,
    "risk_flags": [],
    "recommendation": "Proceed.",
    "regulatory_refs": [],
    "kantian_analysis": "No duty violations.",
    "utilitarian_analysis": "Net positive.",
    "virtue_ethics_analysis": "Virtuous.",
    "provider": "pragma",
    "audit_log_id": 1,
    "proxy_variables_detected": [],
}

BLOCK_RESPONSE = {
    "firewall_action": "block",
    "should_block": True,
    "confidence_score": 0.95,
    "risk_flags": ["bias", "discrimination"],
    "recommendation": "Do not proceed. Evaluate candidates on qualifications only.",
    "regulatory_refs": [
        {
            "law": "EEOC Title VII (Civil Rights Act 1964)",
            "jurisdiction": "United States",
            "description": "Prohibits employment discrimination based on sex.",
            "url": "https://www.eeoc.gov/statutes/title-vii-civil-rights-act-1964",
            "triggered_by": "bias",
        }
    ],
    "kantian_analysis": "Treats candidate as means only.",
    "utilitarian_analysis": "Net negative — perpetuates systemic harm.",
    "virtue_ethics_analysis": "Lacks fairness.",
    "provider": "pragma",
    "audit_log_id": 2,
    "proxy_variables_detected": [],
}

OVERRIDE_RESPONSE = {
    "firewall_action": "override_required",
    "should_block": False,
    "confidence_score": 0.65,
    "risk_flags": ["fairness"],
    "recommendation": "Human review required.",
    "regulatory_refs": [],
    "kantian_analysis": "",
    "utilitarian_analysis": "",
    "virtue_ethics_analysis": "",
    "provider": "pragma",
    "audit_log_id": 3,
    "proxy_variables_detected": [],
}

PROXY_RESPONSE = {
    **BLOCK_RESPONSE,
    "proxy_variables_detected": [
        {
            "field": "zip_code",
            "value": "90210",
            "risk": "Geographic redlining proxy for race/national origin",
            "regulation": "ECOA / Regulation B — 15 U.S.C. § 1691",
        }
    ],
}
