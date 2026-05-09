"""Risk detection heuristics for bias, fairness, and discrimination."""

import re
from typing import List, Dict, Any, Optional

# Sensitive attributes that trigger bias flags
SENSITIVE_ATTRIBUTES = {
    "gender", "sex", "race", "ethnicity", "color", "national_origin",
    "age", "disability", "religion", "veteran_status", "sexual_orientation",
    "marital_status", "zip_code", "postcode", "neighborhood",
    "mother_tongue", "accent", "appearance", "height", "weight"
}

# ---------------------------------------------------------------------------
# Proxy variable registry — field-level ECOA/FHA/HMDA intelligence
#
# Each entry defines:
#   protected_class  — the demographic the field proxies for
#   mechanism        — why the correlation exists (plain English)
#   severity         — "high" (directly actionable) | "medium" (context-dependent)
#   regulations      — ordered list of applicable statutes (primary first)
#   replace_with     — concrete, legally safer alternatives
# ---------------------------------------------------------------------------
PROXY_FIELD_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ── Geographic redlining ─────────────────────────────────────────────────
    "zip_code": {
        "protected_class": "Race / National Origin",
        "mechanism": (
            "Zip codes map to racially segregated neighborhoods created by "
            "mid-20th-century redlining. A model trained on zip code learns a "
            "race signal even without an explicit race field."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
            "Fair Housing Act — 42 U.S.C. § 3605",
            "CRA (Community Reinvestment Act) — 12 U.S.C. § 2901",
            "CFPB UDAP / UDAAP — 12 U.S.C. § 5531",
        ],
        "replace_with": "debt_to_income_ratio, credit_utilization, payment_history",
    },
    "zip": {
        "protected_class": "Race / National Origin",
        "mechanism": "Alias for zip_code — see zip_code.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
            "Fair Housing Act — 42 U.S.C. § 3605",
        ],
        "replace_with": "debt_to_income_ratio, credit_utilization, payment_history",
    },
    "postal_code": {
        "protected_class": "Race / National Origin",
        "mechanism": "Equivalent to zip_code in non-US contexts. Same redlining risk applies.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
            "Fair Housing Act — 42 U.S.C. § 3605",
        ],
        "replace_with": "debt_to_income_ratio, credit_utilization, payment_history",
    },
    "postcode": {
        "protected_class": "Race / National Origin",
        "mechanism": "UK/EU equivalent of zip_code. Geographic segregation patterns apply.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "Fair Housing Act — 42 U.S.C. § 3605",
        ],
        "replace_with": "debt_to_income_ratio, credit_utilization",
    },
    "neighborhood": {
        "protected_class": "Race / National Origin",
        "mechanism": (
            "Neighborhood names encode racial composition more directly than "
            "zip codes because they are often defined by community boundaries "
            "that track historical segregation."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "Fair Housing Act — 42 U.S.C. § 3605",
            "CRA — 12 U.S.C. § 2901",
        ],
        "replace_with": "property_value, local_unemployment_rate (from official sources)",
    },
    "census_tract": {
        "protected_class": "Race / National Origin / Income",
        "mechanism": (
            "Census tracts are drawn to be demographically homogeneous — "
            "they are by design a proxy for race and income. Using them in "
            "credit models is textbook redlining."
        ),
        "severity": "high",
        "regulations": [
            "HMDA — 12 U.S.C. § 2801 (census tract required in HMDA reporting, not as model input)",
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "CRA — 12 U.S.C. § 2901",
        ],
        "replace_with": "applicant-level income, employment_years, credit_score",
    },
    "block_group": {
        "protected_class": "Race / National Origin",
        "mechanism": "Sub-census-tract unit — same redlining risk as census_tract, higher granularity.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "Fair Housing Act — 42 U.S.C. § 3605",
        ],
        "replace_with": "applicant-level income, credit_score",
    },
    "commute_distance": {
        "protected_class": "Race / National Origin",
        "mechanism": (
            "Commute distance from a fixed workplace correlates with residential "
            "segregation — minority applicants in racially concentrated areas are "
            "systematically more distant from suburban job centers."
        ),
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "Fair Housing Act — 42 U.S.C. § 3605",
        ],
        "replace_with": "employment_status, income",
    },

    # ── Name-based ethnicity / national origin inference ────────────────────
    "last_name": {
        "protected_class": "National Origin / Ethnicity",
        "mechanism": (
            "Surname is a well-documented proxy for national origin and ethnicity. "
            "ML models trained on approval data with last_name learn to decline "
            "Hispanic, Arabic, or Asian surnames at higher rates."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
            "EEOC Title VII — 42 U.S.C. § 2000e-2 (if employment context)",
        ],
        "replace_with": "Remove name fields entirely from model inputs",
    },
    "surname": {
        "protected_class": "National Origin / Ethnicity",
        "mechanism": "Alias for last_name — see last_name.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
        ],
        "replace_with": "Remove name fields entirely from model inputs",
    },
    "family_name": {
        "protected_class": "National Origin / Ethnicity",
        "mechanism": "Alias for last_name — see last_name.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
        ],
        "replace_with": "Remove name fields entirely from model inputs",
    },
    "first_name": {
        "protected_class": "Gender / Ethnicity",
        "mechanism": (
            "First names carry strong gender signals (Emma → female, James → male) "
            "and ethnicity signals (DeShawn → Black, Ji-Ho → Korean) that are "
            "statistically detectable at scale. A model using first_name learns "
            "both gender and race without explicit labels."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
            "EEOC Title VII — 42 U.S.C. § 2000e-2 (if employment context)",
        ],
        "replace_with": "Remove name fields entirely from model inputs",
    },
    "maiden_name": {
        "protected_class": "Marital Status / Sex",
        "mechanism": (
            "Maiden name reveals marital status (ECOA-protected for credit) and "
            "is often used to infer gender. It can also reveal ethnicity change "
            "through marriage."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)(iv)",
        ],
        "replace_with": "Remove name fields entirely from model inputs",
    },

    # ── Digital / behavioral proxies ─────────────────────────────────────────
    "email_domain": {
        "protected_class": "National Origin / Religion",
        "mechanism": (
            "Email domains reveal religion (dioceseofchicago.org), ethnicity "
            "(jewishfed.org), or national origin (empresa.com.mx) when used as a "
            "decision feature. Free provider choice (gmail vs. hotmail.es) can "
            "also encode national origin."
        ),
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "CFPB UDAP / UDAAP — 12 U.S.C. § 5531",
        ],
        "replace_with": "Remove email domain from model inputs; use verified contact status",
    },
    "email": {
        "protected_class": "National Origin / Religion",
        "mechanism": "Full email contains both local-part and domain — both can encode demographic signals. See email_domain.",
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
        ],
        "replace_with": "Use email_verified (boolean) instead of the email string",
    },
    "ip_country": {
        "protected_class": "National Origin",
        "mechanism": (
            "IP-derived country of origin is a direct national origin signal. "
            "Using it in credit or hiring decisions constitutes national origin "
            "discrimination under ECOA and Title VII."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "EEOC Title VII — 42 U.S.C. § 2000e-2 (if employment context)",
        ],
        "replace_with": "Use account_country or mailing_address_country only if legally required for KYC",
    },
    "ip_region": {
        "protected_class": "National Origin / Race",
        "mechanism": "Sub-national IP region carries the same geographic segregation risk as zip codes, plus national origin.",
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
        ],
        "replace_with": "Remove IP-derived location from decision models",
    },
    "ip_city": {
        "protected_class": "National Origin / Race",
        "mechanism": "IP-derived city is a finer-grained geographic proxy — same redlining risk as zip_code.",
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "Fair Housing Act — 42 U.S.C. § 3605",
        ],
        "replace_with": "Remove IP-derived location from decision models",
    },
    "device_language": {
        "protected_class": "National Origin",
        "mechanism": (
            "Device or OS language setting reveals primary language, which is a "
            "strong national origin proxy. Spanish → Hispanic; Traditional Chinese → "
            "Taiwanese/HK; Arabic → Middle Eastern. CFPB has flagged language-based "
            "adverse action as a UDAAP risk."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "CFPB UDAP / UDAAP — 12 U.S.C. § 5531",
        ],
        "replace_with": "Use preferred_communication_language for UX only; never as a credit signal",
    },
    "browser_language": {
        "protected_class": "National Origin",
        "mechanism": "Browser language preference — same national origin proxy as device_language.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "CFPB UDAP / UDAAP — 12 U.S.C. § 5531",
        ],
        "replace_with": "Never use browser language as a credit or risk signal",
    },
    "social_media_handle": {
        "protected_class": "Race / Religion / National Origin",
        "mechanism": (
            "Social media usernames often incorporate cultural identifiers, religious "
            "terms, or ethnic markers. Scraping them for credit scoring constitutes "
            "discriminatory use of alternative data under CFPB guidance."
        ),
        "severity": "high",
        "regulations": [
            "CFPB UDAP / UDAAP — 12 U.S.C. § 5531",
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "FCRA — 15 U.S.C. § 1681 (if used as consumer report data)",
        ],
        "replace_with": "Remove social data from credit models entirely",
    },

    # ── Religion proxies ─────────────────────────────────────────────────────
    "church": {
        "protected_class": "Religion",
        "mechanism": "Direct religious affiliation identifier. Illegal as a credit factor under ECOA §202.6(b)(1).",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
        ],
        "replace_with": "Remove religious affiliation from all decision contexts",
    },
    "mosque": {
        "protected_class": "Religion",
        "mechanism": "Direct religious affiliation — Islamic community membership. Illegal as a credit factor.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
        ],
        "replace_with": "Remove religious affiliation from all decision contexts",
    },
    "temple": {
        "protected_class": "Religion",
        "mechanism": "Direct religious affiliation — Jewish, Hindu, or Buddhist community membership.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
        ],
        "replace_with": "Remove religious affiliation from all decision contexts",
    },
    "parish": {
        "protected_class": "Religion",
        "mechanism": "Catholic parish membership. Direct religious affiliation.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(1)",
        ],
        "replace_with": "Remove religious affiliation from all decision contexts",
    },

    # ── Age proxies ──────────────────────────────────────────────────────────
    "birth_date": {
        "protected_class": "Age",
        "mechanism": (
            "Exact date of birth directly reveals age, which is an ECOA-protected "
            "characteristic. Using it as a credit model input violates §202.6(b)(2). "
            "Only age-neutral derivations (years_of_credit_history) are permitted."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
            "ADEA (Age Discrimination in Employment Act) — 29 U.S.C. § 623 (if employment context)",
        ],
        "replace_with": "credit_history_length_years, not birth_date",
    },
    "dob": {
        "protected_class": "Age",
        "mechanism": "Alias for birth_date — see birth_date.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
        ],
        "replace_with": "credit_history_length_years, not dob",
    },
    "date_of_birth": {
        "protected_class": "Age",
        "mechanism": "Alias for birth_date — see birth_date.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
        ],
        "replace_with": "credit_history_length_years, not date_of_birth",
    },
    "telephone_type": {
        "protected_class": "Age",
        "mechanism": (
            "Landline vs. mobile phone correlates strongly with age (older applicants "
            "more likely to have landlines). Using telephone type as a signal "
            "introduces an indirect age-discrimination effect."
        ),
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)",
        ],
        "replace_with": "has_contact_number (boolean)",
    },

    # ── Marital / familial status ─────────────────────────────────────────────
    "marital_status": {
        "protected_class": "Marital Status / Sex",
        "mechanism": (
            "Marital status is directly protected under ECOA §202.6(b)(2)(iv). "
            "It also correlates with sex (female applicants more likely to be "
            "asked about marital status historically)."
        ),
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)(iv)",
        ],
        "replace_with": "Remove. Use combined_household_income if financial assessment is needed.",
    },
    "number_of_dependents": {
        "protected_class": "Familial Status / Sex",
        "mechanism": (
            "Number of dependents correlates with sex (women more likely to be primary "
            "caregivers) and familial status (protected under FHA for housing credit). "
            "CFPB has cited this field in disparate impact cases."
        ),
        "severity": "medium",
        "regulations": [
            "Fair Housing Act — 42 U.S.C. § 3604 (familial status for housing credit)",
            "ECOA / Regulation B — 15 U.S.C. § 1691; 12 C.F.R. § 202.6(b)(2)(v)",
        ],
        "replace_with": "household_income, not dependent count",
    },

    # ── Educational background (socioeconomic / racial proxy) ────────────────
    "school_name": {
        "protected_class": "Race / Socioeconomic Status",
        "mechanism": (
            "School name encodes socioeconomic status (elite prep school vs. public "
            "high school) and in the US is highly correlated with race due to "
            "residential segregation and school funding disparities."
        ),
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "EEOC Title VII — 42 U.S.C. § 2000e-2 (if employment context)",
        ],
        "replace_with": "highest_degree_level, GPA (not institution name)",
    },
    "university": {
        "protected_class": "Race / Socioeconomic Status",
        "mechanism": (
            "University name correlates with race (HBCUs, community colleges, Ivy League) "
            "and socioeconomic status. Using it in credit scoring creates a disparate "
            "impact on minority and low-income applicants."
        ),
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "EEOC Title VII — 42 U.S.C. § 2000e-2 (if employment context)",
        ],
        "replace_with": "highest_degree_level only",
    },
    "college": {
        "protected_class": "Race / Socioeconomic Status",
        "mechanism": "Alias for university — same race/socioeconomic proxy risk.",
        "severity": "medium",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
        ],
        "replace_with": "highest_degree_level only",
    },
    "alma_mater": {
        "protected_class": "Race / Socioeconomic Status",
        "mechanism": "Alma mater is the highest-signal version of the school name proxy. Elite schools are predominantly white; HBCUs signal race directly.",
        "severity": "high",
        "regulations": [
            "ECOA / Regulation B — 15 U.S.C. § 1691",
            "EEOC Title VII — 42 U.S.C. § 2000e-2",
        ],
        "replace_with": "Remove institution name; use degree level and GPA only",
    },
}

# Backward-compatible set for fast membership checks
FINTECH_PROXY_FIELDS = set(PROXY_FIELD_REGISTRY.keys())

# Proxy fields grouped by the protected class they signal.
# Used for compound risk detection — co-occurring fields from the same class
# are far more powerful predictors than any individual field.
_PROTECTED_CLASS_GROUPS: Dict[str, List[str]] = {
    "Race / National Origin": [
        "zip_code", "zip", "postal_code", "postcode", "neighborhood",
        "census_tract", "block_group", "commute_distance",
        "ip_country", "ip_region", "ip_city",
    ],
    "National Origin": [
        "last_name", "surname", "family_name", "first_name",
        "device_language", "browser_language",
        "email_domain", "social_media_handle",
    ],
    "Age": ["birth_date", "dob", "date_of_birth", "telephone_type"],
}

# Historically redlined zip code prefixes (US)
REDLINING_ZIP_PREFIXES = {
    "606", "607", "608",  # South/West Chicago
    "100", "101", "102",  # Harlem/South Bronx
    "902",                # Compton/Watts area (90220–90224, not 90210 Beverly Hills)
    "770", "771",         # Houston Fifth Ward
    "481", "482",         # Detroit East Side
    "191",                # North/West Philadelphia
    "945", "946",         # East Oakland
}


def detect_fintech_proxy_variables(context: Dict[str, Any]) -> List[str]:
    """
    Scan transaction/applicant context for proxy variables that correlate
    with protected demographics. Returns bias/discrimination flags.
    """
    detected_proxies = []

    for key in context:
        key_lower = key.lower().replace("-", "_")
        if key_lower in FINTECH_PROXY_FIELDS:
            detected_proxies.append(key_lower)

        # Redlining-specific zip value check
        if key_lower in {"zip_code", "zip", "postal_code"} and isinstance(context[key], str):
            if context[key][:3] in REDLINING_ZIP_PREFIXES:
                if key_lower not in detected_proxies:
                    detected_proxies.append(key_lower)

    flags: List[str] = []
    if detected_proxies:
        flags.append("bias")
        flags.append("discrimination")

    return flags


def get_proxy_variable_report(
    context: Dict[str, Any],
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a rich, field-specific proxy variable audit report.

    Each detected field includes:
      field           — the context key as submitted
      value           — truncated value (no PII storage)
      protected_class — the demographic this field proxies for
      mechanism       — plain-English explanation of the correlation
      severity        — "high" or "medium"
      regulation      — primary applicable statute (string, for backward compat)
      all_regulations — ordered list of all applicable statutes
      replace_with    — concrete, legally safer alternative fields
      redlining_flag  — True if a known historically-redlined zip was submitted

    Also returns a compound_risk warning when multiple fields from the same
    protected class co-occur — reconstruction risk is multiplicative, not additive.
    """
    detected = []
    present_keys_lower = set()

    for key, value in context.items():
        key_lower = key.lower().replace("-", "_")
        if key_lower not in FINTECH_PROXY_FIELDS:
            continue

        present_keys_lower.add(key_lower)
        defn = PROXY_FIELD_REGISTRY[key_lower]

        redlining_flag = False
        if key_lower in {"zip_code", "zip", "postal_code"} and isinstance(value, str):
            redlining_flag = value[:3] in REDLINING_ZIP_PREFIXES

        regulations = defn["regulations"]
        # Supplement citations based on decision category
        if category in ("hiring", "employment", "workplace"):
            if "EEOC Title VII — 42 U.S.C. § 2000e-2 (if employment context)" not in regulations:
                regulations = [*regulations, "EEOC Title VII — 42 U.S.C. § 2000e-2"]
        if category in ("lending", "finance", "mortgage", "credit"):
            if "HMDA — 12 U.S.C. § 2801" not in " ".join(regulations):
                regulations = [*regulations, "HMDA — 12 U.S.C. § 2801 (reporting obligation)"]

        detected.append({
            "field": key,
            "value": str(value)[:50],
            "protected_class": defn["protected_class"],
            "mechanism": defn["mechanism"],
            "severity": defn["severity"],
            "regulation": regulations[0],          # primary citation (backward compat)
            "all_regulations": regulations,
            "replace_with": defn["replace_with"],
            "redlining_flag": redlining_flag,
        })

    # Compound risk: multiple fields from same protected-class group co-occurring
    compound_risks = []
    for protected_class, group_fields in _PROTECTED_CLASS_GROUPS.items():
        matched = [f for f in group_fields if f in present_keys_lower]
        if len(matched) >= 2:
            compound_risks.append({
                "protected_class": protected_class,
                "co_occurring_fields": matched,
                "warning": (
                    f"Compound reconstruction risk: {len(matched)} fields that proxy "
                    f"for {protected_class} are present simultaneously "
                    f"({', '.join(matched)}). A model trained on their combination "
                    f"can reconstruct {protected_class} with far higher accuracy "
                    f"than any single field alone. This is a higher-severity ECOA "
                    f"exposure than individual fields suggest."
                ),
            })

    # High-severity count for summary scoring
    high_count = sum(1 for d in detected if d["severity"] == "high")

    return {
        "proxy_variables_detected": detected,
        "count": len(detected),
        "high_severity_count": high_count,
        "compound_risks": compound_risks,
        "summary": (
            f"{len(detected)} proxy variable(s) detected "
            f"({high_count} high-severity). "
            + (f"{len(compound_risks)} compound reconstruction risk(s) identified." if compound_risks else "")
        ).strip(),
    }

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
