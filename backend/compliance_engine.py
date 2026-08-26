"""
EU AI Act compliance checklist engine — full 15-article framework.

Reference: Regulation (EU) 2024/1689 of the European Parliament and of the
Council of 13 June 2024 on artificial intelligence (OJ L, 2024/1689, 12.7.2024).

DISCLAIMER: This checklist is an informational self-assessment tool. It does
not constitute legal advice and does not substitute for formal conformity
assessment by a notified body or qualified legal counsel. Article descriptions
reflect Pragma's interpretation of the Regulation as of 2024 and may not
capture jurisdiction-specific implementing measures or subsequent guidance.

Articles covered:
  Art. 4  — AI Literacy (from 2 Feb 2025)
  Art. 5  — Prohibited practices (from 2 Aug 2025)
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


def _evidence_status(declared: bool, notes: str, date: str) -> tuple:
    has_notes = bool((notes or "").strip())
    has_date  = bool((date  or "").strip())
    if declared and (has_notes or has_date):
        parts = []
        if has_notes: parts.append(f"Documentation: {notes.strip()}")
        if has_date:  parts.append(f"Date: {date}")
        return "pass", "; ".join(parts)
    elif declared:
        return "partial", "Declaration only — no supporting documentation attached."
    else:
        return "fail", "Not declared and no documentation provided."


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
    status, evidence = _evidence_status(
        declared=bool(system.get("art4_literacy_training")),
        notes=system.get("art4_literacy_training_evidence_notes", ""),
        date=system.get("art4_literacy_training_evidence_date", ""),
    )
    return {
        "title": "Article 4 — AI Literacy",
        "description": "Regulation (EU) 2024/1689, Art. 4 (applies from 2 February 2025). Providers and deployers must ensure staff have AI literacy appropriate to their role, technical knowledge, and the context of use.",
        "requirement": "Declare that AI literacy training has been provided to all staff operating or overseeing this system.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 4; Recital 20",
        "status": status,
        "evidence": evidence,
    }


def _check_art5(system: Dict, stats: Dict) -> Dict:
    # LAWYER REVIEW NEEDED: Art. 5(1)(h) contains narrow law-enforcement
    # exceptions for real-time biometric ID that require case-by-case legal
    # analysis. This checker applies a broad heuristic only.
    risk_tier = system.get("risk_tier", "")
    use_case = system.get("use_case", "") + " " + system.get("intended_purpose", "")

    # Declared as unacceptable risk tier
    if risk_tier == "unacceptable":
        return {
            "title": "Article 5 — Prohibited AI Practices",
            "description": "Regulation (EU) 2024/1689, Art. 5 (applies from 2 August 2025). Certain AI practices are prohibited outright regardless of safeguards, including social scoring, real-time biometric ID in public spaces, and subliminal manipulation.",
            "requirement": "System must not fall into any prohibited category. If it does, it cannot be deployed in the EU.",
            "legal_citation": "Regulation (EU) 2024/1689, Art. 5(1)(a)–(h)",
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
            "description": "Regulation (EU) 2024/1689, Art. 5 (applies from 2 August 2025). Certain AI practices are prohibited outright regardless of safeguards.",
            "requirement": "System must not fall into any prohibited category.",
            "legal_citation": "Regulation (EU) 2024/1689, Art. 5(1)(a)–(h)",
            "status": "fail",
            "evidence": f"Prohibited practice detected in use case description: {'; '.join(hits)}",
        }

    return {
        "title": "Article 5 — Prohibited AI Practices",
        "description": "Regulation (EU) 2024/1689, Art. 5 (applies from 2 August 2025). Certain AI practices are prohibited outright regardless of safeguards.",
        "requirement": "System must not fall into any prohibited category.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 5(1)(a)–(h)",
        "status": "pass",
        "evidence": "No prohibited practices detected in declared use case and purpose.",
    }


def _check_art6(system: Dict, stats: Dict) -> Dict:
    risk_tier = system.get("risk_tier", "")
    annex_cat = system.get("art6_annex_category", "").strip()
    _desc = "Regulation (EU) 2024/1689, Art. 6 & Annex III. AI systems in listed categories (biometrics, employment, education, essential services, law enforcement, justice) are high-risk and subject to Arts. 9–15 obligations."
    _req  = "Confirm whether system is high-risk under Annex III and declare which category applies."
    _cite = "Regulation (EU) 2024/1689, Art. 6; Annex III"

    if risk_tier == "unacceptable":
        return {"title": "Article 6 — High-Risk AI Classification", "description": _desc,
                "requirement": _req, "legal_citation": _cite, "status": "fail",
                "evidence": "System classified as unacceptable risk — deployment is prohibited."}

    if risk_tier in ("minimal", "limited") and not annex_cat:
        return {"title": "Article 6 — High-Risk AI Classification", "description": _desc,
                "requirement": _req, "legal_citation": _cite, "status": "pass",
                "evidence": f"System classified as {RISK_TIER_LABELS.get(risk_tier, risk_tier)} — reduced obligations apply."}

    if risk_tier == "high" and annex_cat:
        return {"title": "Article 6 — High-Risk AI Classification", "description": _desc,
                "requirement": _req, "legal_citation": _cite, "status": "pass",
                "evidence": f"High-risk classification confirmed. Annex III category: {annex_cat}."}

    if risk_tier == "high" and not annex_cat:
        return {"title": "Article 6 — High-Risk AI Classification", "description": _desc,
                "requirement": _req, "legal_citation": _cite, "status": "partial",
                "evidence": "Risk tier declared as high but Annex III category not specified."}

    return {"title": "Article 6 — High-Risk AI Classification", "description": _desc,
            "requirement": _req, "legal_citation": _cite, "status": "partial",
            "evidence": "Risk tier and Annex III category not fully declared."}


def _check_art9(system: Dict, stats: Dict) -> Dict:
    # LAWYER REVIEW NEEDED: Art. 9 requires a documented continuous risk
    # management system — the 10-evaluation threshold is a Pragma heuristic,
    # not a legal standard. A formal risk management process must be documented
    # independently of this tool.
    passed  = stats["total"] >= 10 and stats["has_risk_flags"]
    partial = stats["total"] >= 1  and stats["has_risk_flags"]
    return {
        "title": "Article 9 — Risk Management System",
        "description": "Regulation (EU) 2024/1689, Art. 9. A continuous risk management process must be established, documented, and maintained throughout the AI system lifecycle.",
        "requirement": "At least 10 compliance evaluations run with risk flags detected and assessed.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 9",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{stats['total']} evaluations logged; risk flags detected: {stats['has_risk_flags']}",
    }


def _check_art10(system: Dict, stats: Dict) -> Dict:
    sources = system.get("training_data_sources", [])
    passed  = len(sources) >= 1
    return {
        "title": "Article 10 — Data and Data Governance",
        "description": "Regulation (EU) 2024/1689, Art. 10. Training, validation, and testing datasets must be subject to data governance practices including documentation of origin, collection methodology, and known limitations.",
        "requirement": "Training data sources declared in system profile.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 10",
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
        "description": "Regulation (EU) 2024/1689, Art. 11 & Annex IV. Technical documentation must be drawn up before the AI system is placed on the market and kept up to date throughout its lifecycle.",
        "requirement": "All profile fields completed: name, company, use case, model version, intended purpose, geographic scope.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 11; Annex IV",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{len(filled)}/{len(required)} fields completed" + (
            f". Missing: {', '.join(missing)}" if missing else ""
        ),
    }


def _check_art12(system: Dict, stats: Dict) -> Dict:
    passed = stats["total"] >= 1
    return {
        "title": "Article 12 — Record-Keeping",
        "description": "Regulation (EU) 2024/1689, Art. 12. High-risk AI systems must be designed to enable automatic recording of events throughout their lifetime, to a degree appropriate to the intended purpose.",
        "requirement": "Immutable audit trail active with at least 1 logged evaluation.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 12",
        "status": "pass" if passed else "fail",
        "evidence": f"{stats['total']} audit log entries; proxy variables caught: {stats['proxy_vars_caught']}",
    }


def _check_art13(system: Dict, stats: Dict) -> Dict:
    passed  = stats["has_regulatory_refs"]
    partial = stats["total"] >= 1
    return {
        "title": "Article 13 — Transparency and Provision of Information",
        "description": "Regulation (EU) 2024/1689, Art. 13. High-risk AI systems must be designed to ensure sufficient transparency so deployers can interpret outputs and use the system appropriately. Instructions for use must include capabilities, limitations, and human oversight measures.",
        "requirement": "Regulatory references mapped in at least one evaluation.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 13",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"Regulatory references mapped: {stats['has_regulatory_refs']}; evaluations run: {stats['total']}",
    }


def _check_art14(system: Dict, stats: Dict) -> Dict:
    passed  = stats["hitl_overrides"] >= 1
    partial = stats["total"] >= 1
    return {
        "title": "Article 14 — Human Oversight",
        "description": "Regulation (EU) 2024/1689, Art. 14. High-risk AI systems must allow natural persons to effectively oversee, understand, and where necessary intervene or halt operation. Deployers must assign oversight to competent individuals.",
        "requirement": "At least one human-in-the-loop override recorded in audit trail.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 14",
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
        "description": "Regulation (EU) 2024/1689, Art. 15. High-risk AI systems must achieve appropriate levels of accuracy and be robust against errors, faults, and adversarial inputs throughout their lifecycle.",
        "requirement": "Accuracy metric documented and adversarial/robustness testing conducted.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 15",
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": "; ".join(parts),
    }


def _check_art17(system: Dict, stats: Dict) -> Dict:
    status, evidence = _evidence_status(
        declared=bool(system.get("art17_qms_documented")),
        notes=system.get("art17_qms_documented_evidence_notes", ""),
        date=system.get("art17_qms_documented_evidence_date", ""),
    )
    return {
        "title": "Article 17 — Quality Management System",
        "description": "Regulation (EU) 2024/1689, Art. 17. Providers of high-risk AI systems must put in place a quality management system covering design, development, testing, and post-market monitoring.",
        "requirement": "Quality management system documented and in place.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 17",
        "status": status,
        "evidence": evidence,
    }


def _check_art25(system: Dict, stats: Dict) -> Dict:
    instr_status, instr_ev = _evidence_status(
        declared=bool(system.get("art25_instructions_provided")),
        notes=system.get("art25_instructions_provided_evidence_notes", ""),
        date=system.get("art25_instructions_provided_evidence_date", ""),
    )
    mon_status, mon_ev = _evidence_status(
        declared=bool(system.get("art25_monitoring_active")),
        notes=system.get("art25_monitoring_active_evidence_notes", ""),
        date=system.get("art25_monitoring_active_evidence_date", ""),
    )
    status_rank = {"pass": 2, "partial": 1, "fail": 0}
    combined = min(instr_status, mon_status, key=lambda s: status_rank[s])
    if instr_status == "pass" and mon_status == "pass":
        combined = "pass"
    elif instr_status == "fail" and mon_status == "fail":
        combined = "fail"
    else:
        combined = "partial"
    return {
        "title": "Article 25 — Obligations of Deployers",
        "description": "Regulation (EU) 2024/1689, Art. 25. Deployers must use AI systems in accordance with instructions for use, implement appropriate human oversight measures, and monitor performance.",
        "requirement": "Instructions for use provided to all deployers; post-deployment monitoring active.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 25",
        "status": combined,
        "evidence": f"Instructions: {instr_ev}; Monitoring: {mon_ev}",
    }


def _check_art27(system: Dict, stats: Dict) -> Dict:
    # LAWYER REVIEW NEEDED: Art. 27 FRIA applies specifically to deployers that
    # are bodies governed by public law or private bodies providing public
    # services — not all deployers. This checker applies it to all high-risk
    # systems, which may be overbroad for private-sector deployers.
    status, evidence = _evidence_status(
        declared=bool(system.get("art27_fria_conducted")),
        notes=system.get("art27_fria_conducted_evidence_notes", ""),
        date=system.get("art27_fria_conducted_evidence_date", ""),
    )
    return {
        "title": "Article 27 — Fundamental Rights Impact Assessment (FRIA)",
        "description": "Regulation (EU) 2024/1689, Art. 27. Deployers that are public bodies or private bodies providing public services must conduct a FRIA before deploying high-risk AI systems.",
        "requirement": "Fundamental Rights Impact Assessment completed and documented.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 27",
        "status": status,
        "evidence": evidence,
    }


def _check_art30(system: Dict, stats: Dict) -> Dict:
    registered = bool(system.get("art30_eu_db_registered"))
    reg_number = (system.get("art30_registration_number") or "").strip()
    ev_status, ev_text = _evidence_status(
        declared=registered,
        notes=system.get("art30_eu_db_registered_evidence_notes", ""),
        date=system.get("art30_eu_db_registered_evidence_date", ""),
    )
    if registered and reg_number:
        status = "pass"
        evidence = f"Registration number: {reg_number}; {ev_text}"
    elif registered:
        status = "partial"
        evidence = f"Registered but no registration number provided; {ev_text}"
    else:
        status = "fail"
        evidence = ev_text
    return {
        "title": "Article 30 — Registration in EU AI Database",
        "description": "Regulation (EU) 2024/1689, Art. 30. Providers of high-risk AI systems must register in the EU AI public database (managed by the EU AI Office) before placing on the EU market.",
        "requirement": "System registered in official EU AI database with valid registration number.",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 30; Art. 71",
        "status": status,
        "evidence": evidence,
    }


def _check_art33(system: Dict, stats: Dict) -> Dict:
    # LAWYER REVIEW NEEDED: Third-party notified body assessment (Annex VII)
    # is only mandatory for certain Annex III categories (A.1 biometrics, A.6
    # law enforcement). Self-assessment (Annex VI) suffices for most high-risk
    # categories. This checker treats both as equally valid, which may be
    # overbroad for biometric or law-enforcement systems.
    conformity = (system.get("art33_conformity_type") or "").strip()
    ev_status, ev_text = _evidence_status(
        declared=conformity in ("self-assessment", "third-party"),
        notes=system.get("art33_conformity_type_evidence_notes", ""),
        date=system.get("art33_conformity_type_evidence_date", ""),
    )
    label_map = {
        "self-assessment": "Self-assessment conformity assessment completed (Annex VI)",
        "third-party":     "Third-party notified body conformity assessment completed (Annex VII)",
        "pending":         "Conformity assessment in progress",
        "":                "No conformity assessment declared",
    }
    base_label = label_map.get(conformity, f"Assessment type declared: {conformity}")
    if conformity == "pending":
        status  = "partial"
        evidence = base_label
    else:
        status  = ev_status
        evidence = f"{base_label}; {ev_text}" if ev_text else base_label
    return {
        "title": "Article 33 — Conformity Assessment",
        "description": "Regulation (EU) 2024/1689, Art. 33. High-risk AI systems must undergo a conformity assessment before being placed on the market. Most categories use self-assessment (Annex VI); biometric and law-enforcement systems require third-party notified body assessment (Annex VII).",
        "requirement": "Conformity assessment completed (self-assessment or third-party notified body).",
        "legal_citation": "Regulation (EU) 2024/1689, Art. 33; Annex VI; Annex VII",
        "status": status,
        "evidence": evidence,
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


# ═══════════════════════════════════════════════════════════════════════════════
# PER-DECISION COMPLIANCE CHECKS
# Deterministic rule-based checks for individual AI decisions.
# No LLM required — always runs, always deterministic.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Geography ──────────────────────────────────────────────────────────────────
_REDLINED_ZIPS: set = {
    "60620","60621","60628","60636","60637","60619","60649",
    "48227","48228","48235","48238",
    "21213","21216","21223","21217",
    "44103","44104","44105","44108",
    "63106","63107","63108","63113",
    "90001","90002","90011","90059",
    "77020","77026",
    "30314","30318",
    "19132","19134","19140",
    "10037","10039","11212",
}
_REDLINED_PREFIXES: set = {"606","482","211","441","631","900","770","303"}

_PROTECTED_INCOME_KW: set = {
    "snap","food stamp","ebt","welfare","public assistance",
    "medicaid","ssi","social security disability","unemployment",
    "government assistance","housing assistance",
}
_REMITTANCE_KW: set = {
    "international wire","remittance","wire transfer","western union",
    "moneygram","international transfer","wire to",
}
_DISCOUNT_STORE_KW: set = {
    "save-a-lot","dollar tree","dollar general","food 4 less",
    "western union","check cashing","aldi",
}
_DENIAL_KW: set = {
    "deny","denied","denial","reject","rejected","decline",
    "declined","not approved","does not meet","below threshold",
}
_EU_LOC_KW: set = {
    "eu","european union","uk","united kingdom","germany","france",
    "netherlands","spain","italy","belgium","sweden","austria",
    "denmark","finland","ireland","portugal",
}
_HBCU_KW: set = {
    "howard university","morehouse","spelman","hampton university",
    "tuskegee","fisk university","clark atlanta","florida a&m",
}


def _s(val) -> str:
    return str(val or "").lower().strip()


def _has(text, keywords: set) -> bool:
    t = _s(text)
    return any(kw in t for kw in keywords)


def _is_denial(decision: str, context: dict) -> bool:
    return _has(decision, _DENIAL_KW) or _has(context.get("denial_decision", ""), _DENIAL_KW)


def _is_redlined(zip_code: str) -> bool:
    z = zip_code.strip()
    return z in _REDLINED_ZIPS or any(z.startswith(p) for p in _REDLINED_PREFIXES)


def _is_eu(context: dict) -> bool:
    loc = _s(context.get("applicant_location", context.get("applicant_geography", "")))
    return _has(loc, _EU_LOC_KW)


def _check_ecoa_decision(decision: str, ctx: dict) -> list:
    results = []
    denial = _is_denial(decision, ctx)

    zip_code = _s(ctx.get("zip_code", ""))
    geo_risk = ctx.get("geo_risk_score", "")
    denial_reason = _s(ctx.get("denial_reason_candidate", ""))
    geo_used = _has(denial_reason, {"geo","zip","geographic","geography"}) or bool(geo_risk)

    if zip_code and _is_redlined(zip_code):
        if denial or geo_used:
            results.append({
                "regulation": "ECOA — Equal Credit Opportunity Act",
                "article": "Regulation B, 12 CFR § 1002.6 — Prohibited Basis (Race)",
                "status": "FAIL",
                "reason": (
                    f"Zip code {zip_code} is in a historically redlined geography. "
                    "Using geographic risk scores as a denial factor is a proxy for race — "
                    "prohibited under ECOA Regulation B § 1002.6."
                ),
            })
        else:
            results.append({
                "regulation": "ECOA — Equal Credit Opportunity Act",
                "article": "Regulation B, 12 CFR § 1002.6 — Prohibited Basis",
                "status": "FLAG",
                "reason": f"Zip code {zip_code} is a historically redlined geography. Verify it was not used as a credit factor.",
            })
    else:
        results.append({
            "regulation": "ECOA — Equal Credit Opportunity Act",
            "article": "Regulation B, 12 CFR § 1002.6 — Geographic Discrimination",
            "status": "PASS",
            "reason": "No geographic discrimination pattern detected.",
        })

    income_source = _s(ctx.get("income_source", ""))
    income_weight = _s(ctx.get("income_weight_applied", ctx.get("income_weight_policy", "")))
    if income_source and _has(income_source, _PROTECTED_INCOME_KW):
        if _has(income_weight, {"0.","penalt","downweight","weight","50%","40%"}):
            results.append({
                "regulation": "ECOA — Equal Credit Opportunity Act",
                "article": "Regulation B, 12 CFR § 1002.6(b)(2) — Public Assistance Income",
                "status": "FAIL",
                "reason": (
                    f"Income from public assistance ('{ctx.get('income_source')}') was penalized "
                    f"with weight '{ctx.get('income_weight_applied', ctx.get('income_weight_policy'))}'. "
                    "ECOA prohibits discriminating against applicants who receive public assistance income."
                ),
            })
        elif denial:
            results.append({
                "regulation": "ECOA — Equal Credit Opportunity Act",
                "article": "Regulation B, 12 CFR § 1002.6(b)(2) — Public Assistance Income",
                "status": "FLAG",
                "reason": f"Applicant receives public assistance income. Verify it was not used as a denial factor.",
            })

    bank = _s(ctx.get("bank_behavior", ctx.get("bank_signals_used", "")))
    proposed_factor = _s(ctx.get("proposed_denial_factor", ""))
    if _has(bank, _REMITTANCE_KW) or _has(proposed_factor, _REMITTANCE_KW):
        results.append({
            "regulation": "ECOA — Equal Credit Opportunity Act",
            "article": "Regulation B, 12 CFR § 1002.6 — National Origin Proxy",
            "status": "FAIL",
            "reason": "International wire transfers / remittances are a proxy for national origin. Using remittance patterns as a credit factor is illegal under ECOA.",
        })

    gap_months = ctx.get("employment_gap_months", ctx.get("employment_gap_years", ""))
    gap_reason = _s(ctx.get("gap_reason", ""))
    if gap_months:
        try:
            gap_val = float(_s(gap_months).replace("months","").replace("years",""))
            if "year" in _s(ctx.get("employment_gap_years","")): gap_val *= 12
        except ValueError:
            gap_val = 0
        if gap_val >= 6:
            if not gap_reason or _has(gap_reason, {"not captured","unknown","not disclosed"}):
                results.append({
                    "regulation": "ECOA — Equal Credit Opportunity Act",
                    "article": "Regulation B, 12 CFR § 1002.6 — Sex / Pregnancy Discrimination",
                    "status": "FLAG",
                    "reason": (
                        f"A {gap_months}-month employment gap was penalized without capturing the reason. "
                        "May discriminate against applicants on parental or medical leave — a proxy for sex or disability."
                    ),
                })
            elif _has(gap_reason, {"medical","parental","maternity","paternity","disability","illness"}):
                results.append({
                    "regulation": "ECOA — Equal Credit Opportunity Act",
                    "article": "Regulation B, 12 CFR § 1002.6 — Sex / Disability Discrimination",
                    "status": "FAIL",
                    "reason": f"Penalizing '{ctx.get('gap_reason')}' gap discriminates on sex or disability basis.",
                })

    open_banking = _s(ctx.get("open_banking_signals", ""))
    if open_banking and _has(open_banking, _DISCOUNT_STORE_KW):
        results.append({
            "regulation": "ECOA — Equal Credit Opportunity Act",
            "article": "Regulation B, 12 CFR § 1002.6 — Race / National Origin Proxy",
            "status": "FAIL",
            "reason": (
                f"Spending at discount and check-cashing stores ('{ctx.get('open_banking_signals')}') "
                "correlates with race and national origin — prohibited as credit factor under ECOA."
            ),
        })

    prior_comp = ctx.get("prior_compensation", "")
    if prior_comp and (denial or _has(denial_reason, {"compensation","salary"})):
        results.append({
            "regulation": "ECOA — Equal Credit Opportunity Act",
            "article": "Regulation B, 12 CFR § 1002.6 — Sex / Race Compensation Proxy",
            "status": "FLAG",
            "reason": f"Prior compensation ({prior_comp}) was used as a denial factor — perpetuates pay gaps.",
        })

    return results


def _check_fcra_decision(decision: str, ctx: dict) -> list:
    denial = _is_denial(decision, ctx)
    adverse = _s(ctx.get("adverse_action_notice", ""))
    consumer_report = _s(ctx.get("consumer_report_used", ""))

    notice_sent = _has(adverse, {"sent","provided","yes","in place","process"})
    notice_missing = _has(adverse, {"not sent","not provided","not mentioned","not required","no notice"})

    if denial and consumer_report and "yes" in consumer_report:
        if notice_missing or (not notice_sent and adverse):
            return [{"regulation":"FCRA — Fair Credit Reporting Act","article":"15 U.S.C. § 1681m — Adverse Action Notice","status":"FAIL",
                     "reason":"Credit report used in adverse decision but no adverse action notice sent. FCRA § 615 requires written notice with bureau name and free report rights."}]
        elif notice_sent:
            return [{"regulation":"FCRA — Fair Credit Reporting Act","article":"15 U.S.C. § 1681m — Adverse Action Notice","status":"PASS",
                     "reason":"Adverse action notice process in place. FCRA § 615 satisfied."}]

    if denial and notice_missing:
        return [{"regulation":"FCRA — Fair Credit Reporting Act","article":"15 U.S.C. § 1681m — Adverse Action Notice","status":"FAIL",
                 "reason":"Application denied with no adverse action notice sent. FCRA requires notifying applicants of their rights."}]

    if denial and not notice_sent:
        return [{"regulation":"FCRA — Fair Credit Reporting Act","article":"15 U.S.C. § 1681m — Adverse Action Notice","status":"FLAG",
                 "reason":"Application denied — verify adverse action notice was sent per FCRA § 615."}]

    return [{"regulation":"FCRA — Fair Credit Reporting Act","article":"15 U.S.C. § 1681m — Adverse Action Notice","status":"PASS",
             "reason":"No adverse action notice violation detected."}]


def _check_fha_decision(decision: str, ctx: dict) -> list:
    zip_code = _s(ctx.get("zip_code", ""))
    geo_risk = ctx.get("geo_risk_score", "")
    denial = _is_denial(decision, ctx)
    if zip_code and _is_redlined(zip_code) and (denial or geo_risk):
        return [{"regulation":"Fair Housing Act","article":"42 U.S.C. § 3605 — Discrimination in Residential Real Estate","status":"FAIL",
                 "reason":f"Zip code {zip_code} is in a historically redlined area. Geographic risk scoring violates the Fair Housing Act."}]
    return [{"regulation":"Fair Housing Act","article":"42 U.S.C. § 3605 — Geographic Discrimination","status":"PASS" if not (zip_code and _is_redlined(zip_code)) else "FLAG",
             "reason":"No geographic discrimination pattern detected." if not (zip_code and _is_redlined(zip_code)) else f"Zip code {zip_code} is a historically redlined geography — verify not used as credit factor."}]


def _check_udaap_decision(decision: str, ctx: dict) -> list:
    results = []
    income_source = _s(ctx.get("income_source", ""))
    income_weight = _s(ctx.get("income_weight_applied", ctx.get("income_weight_policy", "")))
    if income_source and _has(income_source, _PROTECTED_INCOME_KW) and _has(income_weight, {"0.","penalt","downweight","50%","40%"}):
        results.append({"regulation":"CFPB UDAAP","article":"CFPA § 1031 — Unfair, Deceptive, or Abusive Acts","status":"FAIL",
                        "reason":"Penalty weight on public assistance income causes substantial consumer harm with no legitimate credit justification — unfair practice under UDAAP."})

    open_banking = _s(ctx.get("open_banking_signals",""))
    if open_banking and _has(open_banking, _DISCOUNT_STORE_KW):
        results.append({"regulation":"CFPB UDAAP","article":"CFPA § 1031 — Abusive Use of Consumer Financial Data","status":"FLAG",
                        "reason":"Using discount-store spending patterns as credit signals exploits consumer data in ways consumers would not expect — abusive practice under UDAAP."})

    if not results:
        results.append({"regulation":"CFPB UDAAP","article":"CFPA § 1031 — Unfair, Deceptive, or Abusive Acts","status":"PASS",
                        "reason":"No unfair, deceptive, or abusive practice pattern detected."})
    return results


def _check_eu_ai_act_decision(decision: str, ctx: dict) -> list:
    if not _is_eu(ctx):
        return [{"regulation":"EU AI Act","article":"Art. 6 — High-Risk AI Classification","status":"PASS",
                 "reason":"EU AI Act does not apply — no EU/UK applicant location detected."}]
    results = []
    conformity = _s(ctx.get("conformity_assessment_status", ctx.get("eu_ai_act_registration","")))
    if not conformity or _has(conformity, {"not","none","missing","incomplete","not started","not registered"}):
        results.append({"regulation":"EU AI Act","article":"Art. 6 + Annex III — High-Risk AI","status":"FAIL",
                        "reason":"AI-assisted credit/employment decisions are high-risk under EU AI Act Annex III. No conformity assessment completed before deployment."})
    else:
        results.append({"regulation":"EU AI Act","article":"Art. 6 — High-Risk AI Classification","status":"PASS",
                        "reason":"Conformity assessment completed."})

    human_review = _s(ctx.get("human_review_offered", ctx.get("human_review_scheduled", ctx.get("human_review_available",""))))
    if _has(human_review, {"yes","scheduled","available","offered"}):
        results.append({"regulation":"EU AI Act","article":"Art. 14 — Human Oversight","status":"PASS","reason":"Human review available as required by EU AI Act Art. 14."})
    else:
        results.append({"regulation":"EU AI Act","article":"Art. 14 — Human Oversight","status":"FAIL",
                        "reason":"No human review option offered. EU AI Act Art. 14 requires meaningful human oversight for high-risk AI decisions."})

    transparency = _s(ctx.get("transparency_notice_sent",""))
    if _has(transparency, {"yes","sent","provided"}):
        results.append({"regulation":"EU AI Act","article":"Art. 13 — Transparency","status":"PASS","reason":"Applicant informed AI was used in the decision."})
    else:
        results.append({"regulation":"EU AI Act","article":"Art. 13 — Transparency","status":"FLAG",
                        "reason":"Applicant not notified that AI was used. EU AI Act Art. 13 requires disclosure of automated decision-making."})
    return results


def _check_gdpr_decision(decision: str, ctx: dict) -> list:
    if not _is_eu(ctx): return []
    disclosure = _s(ctx.get("gdpr_art22_disclosure",""))
    human_review = _s(ctx.get("right_to_human_review", ctx.get("human_review_offered","")))
    if not _has(disclosure, {"yes","provided","sent"}) or not _has(human_review, {"yes","offered","available","scheduled"}):
        return [{"regulation":"GDPR","article":"Art. 22 — Automated Decision-Making","status":"FAIL",
                 "reason":"GDPR Art. 22 gives EU/UK residents the right to human review and to be informed of automated processing. Neither was satisfied."}]
    return [{"regulation":"GDPR","article":"Art. 22 — Automated Decision-Making","status":"PASS",
             "reason":"GDPR Art. 22 rights satisfied — human review offered and processing disclosed."}]


def _check_eeoc_decision(decision: str, ctx: dict) -> list:
    results = []
    denial = _is_denial(decision, ctx)

    grad_year = ctx.get("graduation_year","")
    if grad_year and denial:
        try:
            age_proxy = 2025 - int(str(grad_year))
            if age_proxy >= 40:
                results.append({"regulation":"ADEA — Age Discrimination in Employment Act","article":"29 U.S.C. § 623 — Age Discrimination","status":"FAIL",
                                 "reason":f"Graduation year {grad_year} implies ~{age_proxy} years of age (protected class 40+). Screening by graduation year is a proxy for age discrimination."})
        except ValueError: pass

    school = _s(ctx.get("university_attended",""))
    preferred = _s(ctx.get("preferred_schools_list",""))
    if school and _has(school, _HBCU_KW) and preferred and school not in preferred:
        results.append({"regulation":"EEOC Title VII — Civil Rights Act","article":"42 U.S.C. § 2000e-2 — Race Discrimination","status":"FAIL",
                        "reason":f"'{ctx.get('university_attended')}' is an HBCU. Excluding HBCUs from preferred school lists is a race discrimination proxy under Title VII."})

    gap = ctx.get("employment_gap_years", ctx.get("employment_gap_months",""))
    gap_reason = _s(ctx.get("gap_reason",""))
    if gap and denial:
        status = "FAIL" if _has(gap_reason, {"medical","disability"}) else "FLAG"
        reason = ("Penalizing a medical/disability gap is ADA discrimination." if status == "FAIL"
                  else f"Employment gap of {gap} penalized without capturing reason — may screen out applicants on medical or disability leave.")
        results.append({"regulation":"ADA — Americans with Disabilities Act","article":"42 U.S.C. § 12112 — Disability Discrimination","status":status,"reason":reason})

    bias_audit = _s(ctx.get("bias_audit_on_file",""))
    if not _has(bias_audit, {"yes","on file","completed"}):
        results.append({"regulation":"EEOC — Bias Audit (NYC Local Law 144)","article":"Annual Independent Bias Audit Required","status":"FLAG",
                        "reason":"No bias audit on file. NYC Local Law 144 and several state laws require annual independent audits of automated employment screening tools."})

    if not results:
        results.append({"regulation":"EEOC Title VII — Civil Rights Act","article":"42 U.S.C. § 2000e-2 — Discrimination in Employment","status":"PASS",
                        "reason":"No prohibited discrimination pattern detected in this hiring decision."})
    return results


_DECISION_CHECKERS = {
    "finance": [_check_ecoa_decision, _check_fcra_decision, _check_fha_decision, _check_udaap_decision, _check_eu_ai_act_decision, _check_gdpr_decision],
    "lending": [_check_ecoa_decision, _check_fcra_decision, _check_fha_decision, _check_udaap_decision, _check_eu_ai_act_decision, _check_gdpr_decision],
    "hiring":  [_check_eeoc_decision, _check_eu_ai_act_decision],
    "hr":      [_check_eeoc_decision, _check_eu_ai_act_decision],
    "other":   [_check_ecoa_decision, _check_fcra_decision],
}


def run_compliance_checks(decision: str, context: dict, category: str = "other") -> list:
    """
    Run deterministic per-decision compliance checks for the given category.
    Always runs — no LLM or API key required.
    Returns compliance_checks list with PASS/FAIL/FLAG per regulation.
    """
    checkers = _DECISION_CHECKERS.get(category.lower(), _DECISION_CHECKERS["other"])
    results = []
    for checker in checkers:
        try:
            results.extend(checker(decision, context))
        except Exception:
            pass
    return results
