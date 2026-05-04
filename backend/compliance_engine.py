"""
EU AI Act compliance checklist engine — full 15-article framework.

Articles covered:
  Art. 4  — AI Literacy
  Art. 5  — Prohibited practices (prohibition screening)
  Art. 6  — High-risk classification (Annex III)
  Art. 9  — Risk management system
  Art. 10 — Data and data governance
  Art. 11 — Technical documentation
  Art. 12 — Record-keeping / logging
  Art. 13 — Transparency
  Art. 14 — Human oversight
  Art. 15 — Accuracy, robustness, cybersecurity
  Art. 17 — Quality management system
  Art. 25 — Deployer obligations
  Art. 27 — Fundamental Rights Impact Assessment (FRIA)
  Art. 30 — EU AI database registration
  Art. 33 — Conformity assessment
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Prohibited use-case patterns (Art. 5) ─────────────────────────────────────

_PROHIBITED_PATTERNS: List[tuple] = [
    ("social scor",         "Social scoring by public authorities (Art. 5(1)(c))"),
    ("social credit",       "Social credit system (Art. 5(1)(c))"),
    ("emotion recogni",     "Emotion recognition in workplace or educational contexts (Art. 5(1)(f))"),
    ("real-time biometric", "Real-time remote biometric identification in public spaces (Art. 5(1)(h))"),
    ("subliminal",          "Subliminal manipulation below conscious perception (Art. 5(1)(a))"),
    ("predictive polic",    "Predictive policing based solely on profiling (Art. 5(1)(d))"),
    ("mass surveillance",   "Mass biometric surveillance (Art. 5(1)(h))"),
    ("biometric categori",  "Biometric categorization to infer sensitive attributes (Art. 5(1)(g))"),
    ("exploit.*vulnerab",   "Exploitation of group vulnerabilities (Art. 5(1)(b))"),
]

# ── Annex III high-risk categories (Art. 6) ───────────────────────────────────

ANNEX_III_CATEGORIES = [
    "A.1 — Biometric identification and categorisation",
    "A.2 — Critical infrastructure management",
    "A.3 — Education and vocational training",
    "A.4 — Employment, workforce management, and access to self-employment",
    "A.5 — Access to and enjoyment of essential private services and public services and benefits",
    "A.6 — Law enforcement",
    "A.7 — Migration, asylum, and border control management",
    "A.8 — Administration of justice and democratic processes",
]

RISK_TIER_LABELS = {
    "minimal":      "Minimal Risk",
    "limited":      "Limited Risk",
    "high":         "High Risk",
    "unacceptable": "Unacceptable Risk (prohibited)",
}


def _check_prohibited(text: str, patterns: list) -> list:
    import re
    hits = []
    text_lower = text.lower()
    for pattern, label in patterns:
        if re.search(pattern, text_lower):
            hits.append(label)
    return hits


# ── Article checkers ──────────────────────────────────────────────────────────

def _check_art4(system: Dict, stats: Dict) -> Dict:
    passed = bool(system.get("art4_literacy_training"))
    return {
        "title": "Article 4 — AI Literacy",
        "description": "Providers and deployers must ensure staff have sufficient AI literacy to use and oversee AI systems appropriately.",
        "requirement": "Declare that AI literacy training has been provided to all staff operating or overseeing this system.",
        "status": "pass" if passed else "fail",
        "evidence": "AI literacy training confirmed by operator." if passed else "No literacy training declaration recorded.",
    }


def _check_art5(system: Dict, stats: Dict) -> Dict:
    risk_tier = system.get("risk_tier", "")
    use_case = system.get("use_case", "") + " " + system.get("intended_purpose", "")

    # Declared as unacceptable risk tier
    if risk_tier == "unacceptable":
        return {
            "title": "Article 5 — Prohibited AI Practices",
            "description": "Certain AI practices are prohibited outright regardless of safeguards.",
            "requirement": "System must not fall into any prohibited category. If it does, it cannot be deployed in the EU.",
            "status": "fail",
            "evidence": "System self-declared as 'Unacceptable Risk' — this system is prohibited under EU AI Act Art. 5.",
        }

    # Screen use case text for prohibited patterns
    hits = _check_prohibited(use_case, _PROHIBITED_PATTERNS)
    if hits:
        logger.warning(
            "Art. 5 PROHIBITED — system=%r hits=%s",
            system.get("system_name", "unknown"), hits,
        )
        return {
            "title": "Article 5 — Prohibited AI Practices",
            "description": "Certain AI practices are prohibited outright regardless of safeguards.",
            "requirement": "System must not fall into any prohibited category.",
            "status": "fail",
            "evidence": f"Prohibited practice detected in use case description: {'; '.join(hits)}",
        }

    return {
        "title": "Article 5 — Prohibited AI Practices",
        "description": "Certain AI practices are prohibited outright regardless of safeguards.",
        "requirement": "System must not fall into any prohibited category.",
        "status": "pass",
        "evidence": "No prohibited practices detected in declared use case and purpose.",
    }


def _check_art6(system: Dict, stats: Dict) -> Dict:
    risk_tier = system.get("risk_tier", "")
    annex_cat = system.get("art6_annex_category", "").strip()

    if risk_tier == "unacceptable":
        return {
            "title": "Article 6 — High-Risk AI Classification",
            "description": "AI systems listed in Annex III are classified as high-risk and subject to mandatory requirements.",
            "requirement": "Confirm whether system is high-risk under Annex III and declare which category applies.",
            "status": "fail",
            "evidence": "System classified as unacceptable risk — deployment is prohibited.",
        }

    if risk_tier in ("minimal", "limited") and not annex_cat:
        return {
            "title": "Article 6 — High-Risk AI Classification",
            "description": "AI systems listed in Annex III are classified as high-risk and subject to mandatory requirements.",
            "requirement": "Confirm whether system is high-risk under Annex III and declare which category applies.",
            "status": "pass",
            "evidence": f"System classified as {RISK_TIER_LABELS.get(risk_tier, risk_tier)} — reduced obligations apply. Arts 9–15 requirements are lighter.",
        }

    if risk_tier == "high" and annex_cat:
        return {
            "title": "Article 6 — High-Risk AI Classification",
            "description": "AI systems listed in Annex III are classified as high-risk and subject to mandatory requirements.",
            "requirement": "Confirm whether system is high-risk under Annex III and declare which category applies.",
            "status": "pass",
            "evidence": f"High-risk classification confirmed. Annex III category: {annex_cat}.",
        }

    if risk_tier == "high" and not annex_cat:
        return {
            "title": "Article 6 — High-Risk AI Classification",
            "description": "AI systems listed in Annex III are classified as high-risk and subject to mandatory requirements.",
            "requirement": "Confirm whether system is high-risk under Annex III and declare which category applies.",
            "status": "partial",
            "evidence": "Risk tier declared as high but Annex III category not specified. Specify which Annex III category applies.",
        }

    return {
        "title": "Article 6 — High-Risk AI Classification",
        "description": "AI systems listed in Annex III are classified as high-risk and subject to mandatory requirements.",
        "requirement": "Confirm whether system is high-risk under Annex III and declare which category applies.",
        "status": "partial",
        "evidence": "Risk tier and Annex III category not fully declared.",
    }


def _check_art9(system: Dict, stats: Dict) -> Dict:
    passed  = stats["total"] >= 10 and stats["has_risk_flags"]
    partial = stats["total"] >= 1  and stats["has_risk_flags"]
    return {
        "title": "Article 9 — Risk Management System",
        "description": "A continuous risk management process must be established and maintained throughout the AI system lifecycle.",
        "requirement": "At least 10 compliance evaluations run with risk flags detected and assessed.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{stats['total']} evaluations logged; risk flags detected: {stats['has_risk_flags']}",
    }


def _check_art10(system: Dict, stats: Dict) -> Dict:
    sources = system.get("training_data_sources", [])
    passed  = len(sources) >= 1
    return {
        "title": "Article 10 — Data and Data Governance",
        "description": "Training, validation, and testing datasets must be subject to data governance practices including origin documentation.",
        "requirement": "Training data sources declared in system profile.",
        "status": "pass" if passed else "fail",
        "evidence": f"{len(sources)} training data source(s) declared: {', '.join(sources) if sources else 'none'}",
    }


def _check_art11(system: Dict, stats: Dict) -> Dict:
    required = ["system_name", "company_name", "use_case", "model_version",
                "intended_purpose", "geographic_scope"]
    filled  = [f for f in required if system.get(f) and system[f] not in ("", "unknown")]
    missing = [f for f in required if not system.get(f) or system[f] in ("", "unknown")]
    passed  = len(filled) == len(required)
    partial = len(filled) >= 4
    return {
        "title": "Article 11 — Technical Documentation",
        "description": "Technical documentation must be drawn up before the AI system is placed on the market and kept up to date.",
        "requirement": "All profile fields completed: name, company, use case, model version, intended purpose, geographic scope.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{len(filled)}/{len(required)} fields completed" + (
            f". Missing: {', '.join(missing)}" if missing else ""
        ),
    }


def _check_art12(system: Dict, stats: Dict) -> Dict:
    passed = stats["total"] >= 1
    return {
        "title": "Article 12 — Record-Keeping",
        "description": "High-risk AI systems must be designed to enable automatic recording of events throughout their lifetime.",
        "requirement": "Immutable audit trail active with at least 1 logged evaluation.",
        "status": "pass" if passed else "fail",
        "evidence": f"{stats['total']} audit log entries; proxy variables caught: {stats['proxy_vars_caught']}",
    }


def _check_art13(system: Dict, stats: Dict) -> Dict:
    passed  = stats["has_regulatory_refs"]
    partial = stats["total"] >= 1
    return {
        "title": "Article 13 — Transparency and Provision of Information",
        "description": "AI systems must be designed to ensure sufficient transparency to enable deployers to interpret the output.",
        "requirement": "Regulatory references mapped in at least one evaluation.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"Regulatory references mapped: {stats['has_regulatory_refs']}; evaluations run: {stats['total']}",
    }


def _check_art14(system: Dict, stats: Dict) -> Dict:
    passed  = stats["hitl_overrides"] >= 1
    partial = stats["total"] >= 1
    return {
        "title": "Article 14 — Human Oversight",
        "description": "High-risk AI systems must be designed with human oversight measures to minimise risks.",
        "requirement": "At least one human-in-the-loop override recorded in audit trail.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{stats['hitl_overrides']} human override(s) recorded in audit trail",
    }


def _check_art15(system: Dict, stats: Dict) -> Dict:
    metric   = (system.get("art15_accuracy_metric") or "").strip()
    robust   = bool(system.get("art15_robustness_tested"))
    passed   = bool(metric) and robust
    partial  = bool(metric) or robust
    parts = []
    if metric:
        parts.append(f"Accuracy metric declared: {metric}")
    else:
        parts.append("No accuracy metric declared")
    parts.append(f"Robustness testing: {'confirmed' if robust else 'not confirmed'}")
    return {
        "title": "Article 15 — Accuracy, Robustness and Cybersecurity",
        "description": "High-risk AI systems must achieve appropriate levels of accuracy and be robust against errors, faults, and adversarial inputs.",
        "requirement": "Accuracy metric documented and adversarial/robustness testing conducted.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": "; ".join(parts),
    }


def _check_art17(system: Dict, stats: Dict) -> Dict:
    passed = bool(system.get("art17_qms_documented"))
    return {
        "title": "Article 17 — Quality Management System",
        "description": "Providers of high-risk AI systems must establish a quality management system covering development, testing, and monitoring.",
        "requirement": "Quality management system documented and in place.",
        "status": "pass" if passed else "fail",
        "evidence": "Quality management system confirmed." if passed else "No quality management system declaration recorded.",
    }


def _check_art25(system: Dict, stats: Dict) -> Dict:
    instructions = bool(system.get("art25_instructions_provided"))
    monitoring   = bool(system.get("art25_monitoring_active"))
    passed  = instructions and monitoring
    partial = instructions or monitoring
    parts = [
        f"Instructions for use provided to deployers: {'yes' if instructions else 'no'}",
        f"Post-deployment monitoring active: {'yes' if monitoring else 'no'}",
    ]
    return {
        "title": "Article 25 — Obligations of Deployers",
        "description": "Deployers must use AI systems in accordance with instructions, implement human oversight, and monitor performance.",
        "requirement": "Instructions for use provided to all deployers; post-deployment monitoring active.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": "; ".join(parts),
    }


def _check_art27(system: Dict, stats: Dict) -> Dict:
    passed = bool(system.get("art27_fria_conducted"))
    return {
        "title": "Article 27 — Fundamental Rights Impact Assessment (FRIA)",
        "description": "Deployers of high-risk AI systems that are bodies governed by public law, or private bodies providing public services, must conduct a FRIA before deployment.",
        "requirement": "Fundamental Rights Impact Assessment completed and documented.",
        "status": "pass" if passed else "fail",
        "evidence": "FRIA completed and documented." if passed else "No FRIA declaration recorded.",
    }


def _check_art30(system: Dict, stats: Dict) -> Dict:
    registered = bool(system.get("art30_eu_db_registered"))
    reg_number = (system.get("art30_registration_number") or "").strip()
    passed  = registered and bool(reg_number)
    partial = registered
    parts = [f"Registered in EU AI database: {'yes' if registered else 'no'}"]
    if reg_number:
        parts.append(f"Registration number: {reg_number}")
    return {
        "title": "Article 30 — Registration in EU AI Database",
        "description": "Providers of high-risk AI systems must register in the EU AI Act public database before placing on the EU market.",
        "requirement": "System registered in official EU AI database with valid registration number.",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": "; ".join(parts),
    }


def _check_art33(system: Dict, stats: Dict) -> Dict:
    conformity = (system.get("art33_conformity_type") or "").strip()
    passed  = conformity in ("self-assessment", "third-party")
    partial = conformity == "pending"
    label_map = {
        "self-assessment": "Self-assessment conformity assessment completed (Annex VI)",
        "third-party":     "Third-party notified body conformity assessment completed",
        "pending":         "Conformity assessment in progress",
        "":                "No conformity assessment declared",
    }
    return {
        "title": "Article 33 — Conformity Assessment",
        "description": "High-risk AI systems must undergo a conformity assessment before being placed on the market — either self-assessment or via a notified body.",
        "requirement": "Conformity assessment completed (self-assessment or third-party notified body).",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": label_map.get(conformity, f"Assessment type declared: {conformity}"),
    }


# ── Main entry point ──────────────────────────────────────────────────────────

_CHECKERS = [
    ("art_4",  _check_art4),
    ("art_5",  _check_art5),
    ("art_6",  _check_art6),
    ("art_9",  _check_art9),
    ("art_10", _check_art10),
    ("art_11", _check_art11),
    ("art_12", _check_art12),
    ("art_13", _check_art13),
    ("art_14", _check_art14),
    ("art_15", _check_art15),
    ("art_17", _check_art17),
    ("art_25", _check_art25),
    ("art_27", _check_art27),
    ("art_30", _check_art30),
    ("art_33", _check_art33),
]


def compute_compliance(system: Dict, stats: Dict) -> Dict[str, Any]:
    """
    Compute the full EU AI Act compliance checklist (15 articles) for a
    registered AI system. Returns per-article status plus overall score.
    """
    try:
        checks = {key: fn(system, stats) for key, fn in _CHECKERS}
    except Exception:
        logger.exception(
            "Compliance check failed — system_id=%s name=%r",
            system.get("system_id"), system.get("system_name"),
        )
        raise

    statuses = [c["status"] for c in checks.values()]
    passes   = statuses.count("pass")
    partials = statuses.count("partial")
    fails    = statuses.count("fail")
    total    = len(statuses)

    # Score: pass=1.0, partial=0.5, fail=0.0
    score = (passes * 1.0 + partials * 0.5) / total

    if score >= 0.9:
        verdict, verdict_label = "ready",     "Compliance Ready"
    elif score >= 0.6:
        verdict, verdict_label = "partial",   "Partially Compliant"
    else:
        verdict, verdict_label = "not_ready", "Not Ready"

    # Art. 5 fail always overrides the verdict — prohibited system cannot be certified
    if checks["art_5"]["status"] == "fail":
        verdict, verdict_label = "prohibited", "PROHIBITED — Cannot be deployed in the EU"

    logger.info(
        "Compliance computed — system=%r score=%.3f verdict=%s passes=%d partials=%d fails=%d",
        system.get("system_name"), score, verdict, passes, partials, fails,
    )

    risk_tier = system.get("risk_tier", "unknown")
    return {
        "system_id":      system["system_id"],
        "system_name":    system["system_name"],
        "company_name":   system["company_name"],
        "risk_tier":      risk_tier,
        "risk_tier_label": RISK_TIER_LABELS.get(risk_tier, risk_tier),
        "articles":       checks,
        "overall_score":  round(score, 3),
        "verdict":        verdict,
        "verdict_label":  verdict_label,
        "passes":         passes,
        "partials":       partials,
        "fails":          fails,
        "total_articles": total,
        "stats":          stats,
    }
