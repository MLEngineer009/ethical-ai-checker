"""Prompt templates for ethical decision evaluation with compliance checks."""

import json
from typing import Any, Dict

SYSTEM_PROMPT = """You are an AI compliance and ethics evaluation engine. For every decision you receive, perform two analyses.

PART 1 — ETHICAL ANALYSIS
Evaluate through three frameworks:
1. Kantian ethics — Is it fair, universally applicable, and duty-respecting?
2. Utilitarianism — Does it maximize benefit and minimize harm for all affected?
3. Virtue ethics — Does it reflect good character, fairness, and integrity?

PART 2 — COMPLIANCE CHECKS
The user prompt lists specific regulations that apply to this decision category.
For EACH regulation listed, return a compliance check:
- "regulation": exact regulation name as listed
- "article": most specific article/section/clause that applies
- "status": "PASS" (no violation), "FAIL" (clear violation), or "FLAG" (possible issue — needs human review)
- "reason": one sentence citing specific facts from the decision/context

Guidance on status:
- PASS: The decision as described does not appear to violate this regulation
- FLAG: There are concerning elements that may violate this regulation but more information is needed
- FAIL: The decision as described clearly violates this regulation

Respond with ONLY a valid JSON object — no markdown, no explanation outside the JSON:

{
  "kantian_analysis": "<string>",
  "utilitarian_analysis": "<string>",
  "virtue_ethics_analysis": "<string>",
  "risk_flags": ["<flag1>", ...],
  "confidence_score": <0.0–1.0>,
  "recommendation": "<string>",
  "compliance_checks": [
    {
      "regulation": "<name>",
      "article": "<specific article or section>",
      "status": "<PASS|FAIL|FLAG>",
      "reason": "<one sentence>"
    }
  ]
}

Rules:
- risk_flags: flat array of strings e.g. ["bias", "discrimination", "ecoa_proxy"]
- confidence_score: 0.0 to 1.0 (higher = more certain of risk)
- compliance_checks: one entry per regulation listed in the user prompt, in the same order
- Do NOT add extra keys
- Do NOT wrap in markdown code blocks"""

_CATEGORY_REGS: Dict[str, list] = {
    "hiring": [
        "EEOC Title VII (Civil Rights Act 1964) — prohibits employment discrimination based on race, color, religion, sex, or national origin",
        "ADEA (Age Discrimination in Employment Act) — prohibits discrimination against workers 40 years or older",
        "ADA (Americans with Disabilities Act) — prohibits discrimination against qualified individuals with disabilities in employment",
        "EU AI Act Art. 5 — prohibited AI practices including subliminal manipulation and exploitation of vulnerabilities",
        "EU AI Act Art. 6 — employment and recruitment AI systems are Annex III high-risk and require conformity assessment",
        "EU AI Act Art. 14 — human oversight must be maintained; high-risk AI hiring decisions cannot be fully automated",
        "NYC Local Law 144 — automated employment decision tools in NYC require annual bias audits and candidate notification",
    ],
    "workplace": [
        "EEOC Title VII (Civil Rights Act 1964) — prohibits workplace discrimination based on race, color, religion, sex, or national origin",
        "ADEA — prohibits age discrimination against employees 40 years or older",
        "ADA — prohibits disability discrimination in employment conditions and termination",
        "NLRA (National Labor Relations Act) — protects employees' rights to organize and engage in collective bargaining",
        "EU Equal Treatment Directive (2000/78/EC) — prohibits discrimination based on religion, disability, age, or sexual orientation",
        "EU AI Act Art. 14 — human oversight required for AI-assisted workplace management decisions",
    ],
    "finance": [
        "ECOA / Regulation B (12 CFR Part 1002) — prohibits credit discrimination based on race, color, religion, national origin, sex, marital status, or age",
        "Fair Housing Act (42 U.S.C. §§ 3601–3619) — prohibits discrimination in housing and mortgage lending",
        "FCRA (Fair Credit Reporting Act) — requires adverse action notice when consumer reports influence credit decisions",
        "CFPB UDAAP (Dodd-Frank §§ 1031–1036) — prohibits unfair, deceptive, or abusive practices in consumer financial products",
        "EU AI Act Art. 6 — creditworthiness assessment and credit scoring are Annex III high-risk AI systems",
        "GDPR Art. 22 — individuals have the right not to be subject to solely automated decisions with significant financial effects",
    ],
    "healthcare": [
        "ACA Section 1557 (42 U.S.C. § 18116) — prohibits discrimination in federally-funded healthcare programs based on race, color, national origin, sex, age, or disability",
        "ADA (Americans with Disabilities Act) — prohibits disability discrimination in healthcare provision",
        "HIPAA Privacy Rule (45 CFR Parts 160, 164) — protects individually identifiable health information",
        "EU AI Act Art. 5 — prohibits AI that exploits vulnerabilities of persons due to health status",
        "EU AI Act Art. 6 — AI for medical diagnosis, monitoring, and patient management is Annex III high-risk",
        "EU AI Act Art. 14 — clinical AI decisions require human oversight; cannot be fully automated for patient safety",
    ],
    "policy": [
        "EEOC Title VII — discriminatory impact on protected classes in workplace policies",
        "GDPR Art. 22 — automated decision-making policies affecting individuals require human oversight and explanation rights",
        "EU AI Act Art. 9 — risk management system must be established and maintained throughout the AI system lifecycle",
        "EU AI Act Art. 13 — AI outputs must be interpretable; deployers must understand capabilities and limitations",
        "FTC Act Section 5 — prohibits unfair or deceptive acts; FTC has signalled enforcement against biased AI policies",
        "CCPA / CPRA — California residents have rights over personal data used in automated decision-making",
    ],
    "personal": [
        "GDPR Art. 22 — right not to be subject to solely automated decisions with legal or similarly significant effects",
        "CCPA / CPRA (California Consumer Privacy Act) — rights over personal data used in automated or AI-assisted decisions",
    ],
    "other": [
        "EU AI Act (Regulation (EU) 2024/1689) — risk-based framework for AI systems placed on or used in the EU market",
        "GDPR Art. 22 — automated decision-making rights for EU/EEA residents",
        "FTC AI Guidance — fairness, transparency, and avoiding discriminatory or deceptive AI outcomes",
        "Executive Order 14110 — safe, secure, and trustworthy AI development and use",
    ],
}

USER_PROMPT_TEMPLATE = """Category: {category}

Decision: {decision}

Context: {context}

Regulations to check for this {category} decision:
{regulations}

Evaluate using both ethical frameworks and each regulation above. Return JSON only."""


def build_user_prompt(decision: str, context: Any, category: str) -> str:
    regs = _CATEGORY_REGS.get(category, _CATEGORY_REGS["other"])
    reg_list = "\n".join(f"- {r}" for r in regs)
    return USER_PROMPT_TEMPLATE.format(
        category=category,
        decision=decision,
        context=json.dumps(context) if isinstance(context, dict) else str(context),
        regulations=reg_list,
    )
