"""
EU AI Act compliance checklist engine.

Evaluates a registered AI system against the six core EU AI Act articles
that apply to all risk tiers. Returns a per-article status and overall score.

Articles evaluated:
  Art. 9  — Risk management system
  Art. 10 — Data governance
  Art. 11 — Technical documentation
  Art. 12 — Record-keeping / logging
  Art. 13 — Transparency
  Art. 14 — Human oversight
"""

from typing import Any, Dict, List


ARTICLES = {
    "art_9":  {
        "title": "Article 9 — Risk Management System",
        "description": "A continuous risk management process must be established and maintained throughout the AI system lifecycle.",
        "requirement": "At least 10 compliance evaluations run with risk flags detected and assessed.",
    },
    "art_10": {
        "title": "Article 10 — Data and Data Governance",
        "description": "Training, validation, and testing datasets must be subject to data governance practices including origin documentation.",
        "requirement": "Training data sources declared in system profile.",
    },
    "art_11": {
        "title": "Article 11 — Technical Documentation",
        "description": "Technical documentation must be drawn up before the AI system is placed on the market and kept up to date.",
        "requirement": "System profile fully completed: name, use case, model version, risk tier, intended purpose, geographic scope.",
    },
    "art_12": {
        "title": "Article 12 — Record-Keeping",
        "description": "High-risk AI systems must be designed to enable automatic recording of events (logging) throughout their lifetime.",
        "requirement": "Immutable audit trail active with at least 1 logged evaluation.",
    },
    "art_13": {
        "title": "Article 13 — Transparency and Provision of Information",
        "description": "AI systems must be designed and developed to ensure sufficient transparency to enable users to interpret the output.",
        "requirement": "Regulatory references mapped in at least one evaluation.",
    },
    "art_14": {
        "title": "Article 14 — Human Oversight",
        "description": "AI systems must be designed and developed with human oversight measures to minimise risks.",
        "requirement": "At least one human-in-the-loop override recorded in audit trail.",
    },
}

RISK_TIER_LABELS = {
    "minimal":       "Minimal Risk",
    "limited":       "Limited Risk",
    "high":          "High Risk",
    "unacceptable":  "Unacceptable Risk (prohibited)",
}


def _check_art9(system: Dict, stats: Dict) -> Dict:
    passed = stats["total"] >= 10 and stats["has_risk_flags"]
    partial = stats["total"] >= 1 and stats["has_risk_flags"]
    return {
        **ARTICLES["art_9"],
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{stats['total']} evaluations logged; risk flags detected: {stats['has_risk_flags']}",
    }


def _check_art10(system: Dict, stats: Dict) -> Dict:
    sources = system.get("training_data_sources", [])
    passed = len(sources) >= 1
    return {
        **ARTICLES["art_10"],
        "status": "pass" if passed else "fail",
        "evidence": f"{len(sources)} training data source(s) declared: {', '.join(sources) if sources else 'none'}",
    }


def _check_art11(system: Dict, stats: Dict) -> Dict:
    required_fields = ["system_name", "company_name", "use_case", "model_version",
                       "intended_purpose", "geographic_scope"]
    filled = [f for f in required_fields if system.get(f) and system[f] not in ("", "unknown")]
    passed = len(filled) == len(required_fields)
    partial = len(filled) >= 4
    missing = [f for f in required_fields if not system.get(f) or system[f] in ("", "unknown")]
    return {
        **ARTICLES["art_11"],
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{len(filled)}/{len(required_fields)} fields completed" + (
            f". Missing: {', '.join(missing)}" if missing else ""
        ),
    }


def _check_art12(system: Dict, stats: Dict) -> Dict:
    passed = stats["total"] >= 1
    return {
        **ARTICLES["art_12"],
        "status": "pass" if passed else "fail",
        "evidence": f"{stats['total']} audit log entries; proxy variables caught: {stats['proxy_vars_caught']}",
    }


def _check_art13(system: Dict, stats: Dict) -> Dict:
    passed = stats["has_regulatory_refs"]
    partial = stats["total"] >= 1
    return {
        **ARTICLES["art_13"],
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"Regulatory references mapped: {stats['has_regulatory_refs']}; evaluations run: {stats['total']}",
    }


def _check_art14(system: Dict, stats: Dict) -> Dict:
    passed = stats["hitl_overrides"] >= 1
    partial = stats["total"] >= 1
    return {
        **ARTICLES["art_14"],
        "status": "pass" if passed else ("partial" if partial else "fail"),
        "evidence": f"{stats['hitl_overrides']} human override(s) recorded in audit trail",
    }


def compute_compliance(system: Dict, stats: Dict) -> Dict[str, Any]:
    """
    Compute the EU AI Act compliance checklist for a registered AI system.
    Returns per-article status plus overall score and readiness verdict.
    """
    checks = {
        "art_9":  _check_art9(system, stats),
        "art_10": _check_art10(system, stats),
        "art_11": _check_art11(system, stats),
        "art_12": _check_art12(system, stats),
        "art_13": _check_art13(system, stats),
        "art_14": _check_art14(system, stats),
    }

    statuses = [c["status"] for c in checks.values()]
    passes   = statuses.count("pass")
    partials = statuses.count("partial")
    total    = len(statuses)

    # Score: pass=1.0, partial=0.5, fail=0.0
    score = (passes * 1.0 + partials * 0.5) / total

    if score >= 0.9:
        verdict = "ready"
        verdict_label = "Compliance Ready"
    elif score >= 0.6:
        verdict = "partial"
        verdict_label = "Partially Compliant"
    else:
        verdict = "not_ready"
        verdict_label = "Not Ready"

    risk_tier = system.get("risk_tier", "unknown")

    return {
        "system_id":    system["system_id"],
        "system_name":  system["system_name"],
        "company_name": system["company_name"],
        "risk_tier":    risk_tier,
        "risk_tier_label": RISK_TIER_LABELS.get(risk_tier, risk_tier),
        "articles":     checks,
        "overall_score": round(score, 3),
        "verdict":      verdict,
        "verdict_label": verdict_label,
        "passes":       passes,
        "partials":     partials,
        "fails":        total - passes - partials,
        "total_articles": total,
        "stats":        stats,
    }
