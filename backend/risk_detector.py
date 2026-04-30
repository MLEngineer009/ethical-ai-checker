"""Risk detection heuristics for bias, fairness, and discrimination."""

import re
from typing import List, Dict, Any

# Sensitive attributes that trigger bias flags
SENSITIVE_ATTRIBUTES = {
    "gender", "sex", "race", "ethnicity", "color", "national_origin",
    "age", "disability", "religion", "veteran_status", "sexual_orientation",
    "marital_status", "zip_code", "postcode", "neighborhood",
    "mother_tongue", "accent", "appearance", "height", "weight"
}

# Fintech-specific proxy variables — fields that correlate with protected
# demographics and are illegal to use as credit/fraud decision inputs under ECOA.
FINTECH_PROXY_FIELDS = {
    "zip_code", "zip", "postal_code", "postcode",   # redlining proxy
    "neighborhood", "census_tract", "block_group",  # geographic redlining
    "surname", "last_name", "family_name",           # national origin proxy
    "email_domain", "email",                         # demographic inference
    "ip_country", "ip_region", "ip_city",            # national origin proxy
    "device_language", "browser_language",           # national origin proxy
    "church", "mosque", "temple", "parish",          # religion proxy
    "birth_date", "dob", "date_of_birth",            # age proxy
}

# High-risk fintech proxy values (zip code ranges known to correlate with
# majority-minority neighborhoods in US redlining literature)
REDLINING_ZIP_PREFIXES = {
    "606", "607", "608",  # South/West Chicago (historically redlined)
    "100", "101", "102",  # Harlem/South Bronx
    "902", "903",         # Compton/Watts, LA
    "770", "771",         # Houston Fifth Ward
}


def detect_fintech_proxy_variables(context: Dict[str, Any]) -> List[str]:
    """
    Scan transaction/applicant context for proxy variables that correlate
    with protected demographics. Flags 'bias' and 'discrimination' when found.
    Returns list of detected proxy field names for the audit trail.
    """
    flags = []
    detected_proxies = []

    for key, value in context.items():
        key_lower = key.lower().replace("-", "_")

        # Direct proxy field name match
        if key_lower in FINTECH_PROXY_FIELDS:
            detected_proxies.append(key)

        # Zip code redlining check
        if key_lower in {"zip_code", "zip", "postal_code"} and isinstance(value, str):
            prefix = value[:3]
            if prefix in REDLINING_ZIP_PREFIXES:
                detected_proxies.append(f"{key}:{value} (historically redlined area)")

    if detected_proxies:
        flags.append("bias")
        flags.append("discrimination")

    return flags


def get_proxy_variable_report(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a detailed proxy variable audit report for a given context dict.
    Used by the audit trail to document what was detected and why.
    """
    detected = []
    for key, value in context.items():
        key_lower = key.lower().replace("-", "_")
        if key_lower in FINTECH_PROXY_FIELDS:
            detected.append({
                "field": key,
                "value": str(value)[:50],
                "risk": "proxy variable for protected demographic characteristic",
                "regulation": "ECOA / Regulation B — 15 U.S.C. § 1691",
            })
    return {"proxy_variables_detected": detected, "count": len(detected)}

# Keywords that suggest exclusionary or harmful reasoning
HARM_KEYWORDS = {
    "exclude", "eliminate", "reject", "ban", "forbid", "prevent",
    "block", "disqualify", "unfit", "unsuitable", "unworthy"
}

TRANSPARENCY_KEYWORDS = {
    "assume", "likely", "probably", "might", "could", "unclear",
    "vague", "unspecified", "unknown", "undefined"
}


def detect_bias_risks(context: dict) -> List[str]:
    """Detect bias risks based on presence of sensitive attributes."""
    flags = []
    context_str = str(context).lower()
    
    for attr in SENSITIVE_ATTRIBUTES:
        if attr.lower() in context_str:
            flags.append("bias")
            break
    
    return flags


def detect_fairness_risks(decision: str, context: dict) -> List[str]:
    """Detect fairness issues based on decision reasoning."""
    flags = []
    decision_lower = decision.lower()
    
    # Check for exclusionary language
    if any(keyword in decision_lower for keyword in HARM_KEYWORDS):
        flags.append("fairness")
    
    # Check for group-based reasoning
    if any(group in decision_lower for group in ["all ", "any ", "every "]):
        flags.append("fairness")
    
    return flags


def detect_transparency_risks(decision: str, context: dict) -> List[str]:
    """Detect lack of transparency in reasoning."""
    flags = []
    decision_lower = decision.lower()
    
    if any(keyword in decision_lower for keyword in TRANSPARENCY_KEYWORDS):
        flags.append("transparency")
    
    # Check if context is too sparse
    if isinstance(context, dict) and len(context) < 2:
        flags.append("transparency")
    
    return flags


def detect_discrimination_risks(decision: str, context: dict) -> List[str]:
    """Detect potential discrimination patterns."""
    flags = []
    decision_lower = decision.lower()
    
    # Exclusionary patterns
    exclusionary_patterns = [
        r"based on.*(?:gender|race|age|religion)",
        r"(?:gender|race|age|religion).*based",
        r"not.*(?:similar to|like|matching)"
    ]
    
    for pattern in exclusionary_patterns:
        if re.search(pattern, decision_lower):
            flags.append("discrimination")
            break
    
    return flags


def detect_all_risks(decision: str, context: dict) -> List[str]:
    """Detect all risk flags for a decision."""
    all_flags = set()

    all_flags.update(detect_bias_risks(context))
    all_flags.update(detect_fairness_risks(decision, context))
    all_flags.update(detect_transparency_risks(decision, context))
    all_flags.update(detect_discrimination_risks(decision, context))
    all_flags.update(detect_fintech_proxy_variables(context))

    return sorted(list(all_flags))
