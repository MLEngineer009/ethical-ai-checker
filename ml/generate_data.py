"""
Distillation data generator — uses Claude (teacher) to produce
labelled (input → structured JSON) training pairs for the student model.

Run:
    pip install anthropic tqdm
    ANTHROPIC_API_KEY=sk-ant-... python ml/generate_data.py

Output: ml/data/train.jsonl  ml/data/eval.jsonl
"""

import json
import os
import random
import time
from pathlib import Path

import anthropic
from tqdm import tqdm

# ── Teacher ───────────────────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are an ethical reasoning engine. Respond with ONLY valid JSON using EXACTLY this structure:
{
  "kantian_analysis": "<string>",
  "utilitarian_analysis": "<string>",
  "virtue_ethics_analysis": "<string>",
  "risk_flags": ["<string>", ...],
  "confidence_score": <float 0-1>,
  "recommendation": "<string>"
}
risk_flags must be a flat array chosen from: bias, fairness, discrimination, transparency, harm
Do NOT wrap in markdown. Do NOT add extra keys."""


def call_teacher(decision: str, context: dict, category: str) -> dict | None:
    try:
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content":
                f"Category: {category}\nDecision: {decision}\nContext: {json.dumps(context)}"}],
        )
        text = next((b.text for b in msg.content if b.type == "text"), "")
        start, end = text.find("{"), text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        data = json.loads(text[start:end])
        required = {"kantian_analysis","utilitarian_analysis","virtue_ethics_analysis",
                    "risk_flags","confidence_score","recommendation"}
        if not required.issubset(data):
            return None
        return data
    except Exception as e:
        print(f"  Teacher error: {e}")
        return None


# ── Scenario seeds ────────────────────────────────────────────────────────────

SCENARIOS = [
    # ── HIRING ──────────────────────────────────────────────────────────────
    ("hiring", "Reject job candidate",
     lambda: {"gender": random.choice(["female","male","non-binary"]),
               "experience_years": random.randint(0,15),
               "education": random.choice(["high school","bachelor","master","phd"])}),

    ("hiring", "Screen out resume before interview",
     lambda: {"name_origin": random.choice(["Western","Asian","African","Hispanic"]),
               "graduation_year": random.choice(["2010","2018","2023"]),
               "gpa": round(random.uniform(2.5, 4.0), 1)}),

    ("hiring", "Reject candidate after technical interview",
     lambda: {"age": random.randint(22, 60),
               "performance_score": random.randint(50, 100),
               "position": "software engineer"}),

    ("hiring", "Offer lower salary than requested",
     lambda: {"gender": random.choice(["female","male"]),
               "negotiation_style": random.choice(["assertive","collaborative","passive"]),
               "market_rate": "yes"}),

    ("hiring", "Not shortlist candidate for senior role",
     lambda: {"years_experience": random.randint(5,20),
               "industry_gaps": random.choice(["none","1 year","3 years"]),
               "disability_disclosed": random.choice(["yes","no"])}),

    ("hiring", "Reject candidate based on social media review",
     lambda: {"social_media_posts": random.choice(["political views","personal photos","none found"]),
               "job_relevance": random.choice(["low","medium","high"])}),

    # ── WORKPLACE ───────────────────────────────────────────────────────────
    ("workplace", "Deny promotion to employee",
     lambda: {"performance_rating": random.choice(["exceeds","meets","below"]),
               "gender": random.choice(["female","male"]),
               "years_at_company": random.randint(1,10)}),

    ("workplace", "Assign lower-profile project to employee",
     lambda: {"ethnicity": random.choice(["Hispanic","White","Black","Asian"]),
               "seniority": random.choice(["junior","mid","senior"])}),

    ("workplace", "Place employee on performance improvement plan",
     lambda: {"pregnancy_status": random.choice(["pregnant","not pregnant"]),
               "performance_score": random.randint(40, 80),
               "manager_feedback": random.choice(["positive","mixed","negative"])}),

    ("workplace", "Deny remote work request",
     lambda: {"disability": random.choice(["yes","no"]),
               "role_type": random.choice(["individual contributor","manager","support"]),
               "performance": random.choice(["strong","average"])}),

    ("workplace", "Terminate employee contract",
     lambda: {"age": random.randint(30, 65),
               "performance": random.choice(["poor","adequate"]),
               "protected_class": random.choice(["veteran","none","caregiver"])}),

    ("workplace", "Deny flexible hours for employee",
     lambda: {"family_status": random.choice(["single parent","caregiver","no dependents"]),
               "role": "customer support",
               "team_impact": random.choice(["low","medium","high"])}),

    # ── FINANCE ─────────────────────────────────────────────────────────────
    ("finance", "Reject loan application",
     lambda: {"credit_score": random.randint(500, 800),
               "zip_code": random.choice(["90210","10001","60620","77001"]),
               "annual_income": random.randint(30000, 120000)}),

    ("finance", "Deny mortgage application",
     lambda: {"race": random.choice(["Black","White","Hispanic","Asian"]),
               "income": random.randint(50000, 200000),
               "debt_to_income": round(random.uniform(0.1, 0.55), 2)}),

    ("finance", "Set higher insurance premium",
     lambda: {"zip_code": random.choice(["90001","10001","77002"]),
               "age": random.randint(18, 70),
               "gender": random.choice(["female","male"])}),

    ("finance", "Flag transaction as fraudulent",
     lambda: {"country_of_origin": random.choice(["Nigeria","India","Russia","USA"]),
               "transaction_amount": random.randint(500, 10000),
               "account_age_days": random.randint(10, 1000)}),

    ("finance", "Deny credit card limit increase",
     lambda: {"payment_history": random.choice(["perfect","1 late","3 late"]),
               "income": random.randint(25000, 100000),
               "marital_status": random.choice(["single","married","divorced"])}),

    ("finance", "Approve high-interest payday loan",
     lambda: {"income": random.randint(15000, 35000),
               "financial_literacy": random.choice(["low","medium"]),
               "urgency": random.choice(["medical","rent","food"])}),

    # ── HEALTHCARE ──────────────────────────────────────────────────────────
    ("healthcare", "Deprioritize patient for surgery",
     lambda: {"age": random.randint(50, 85),
               "insurance_type": random.choice(["medicaid","private","none"]),
               "severity": random.choice(["moderate","high"])}),

    ("healthcare", "Recommend different treatment than standard",
     lambda: {"race": random.choice(["Black","White","Hispanic"]),
               "pain_level_reported": random.randint(5, 10),
               "prior_opioid_use": random.choice(["yes","no"])}),

    ("healthcare", "Allocate scarce ICU bed",
     lambda: {"age": random.randint(30, 85),
               "disability": random.choice(["yes","no"]),
               "survival_probability": round(random.uniform(0.3, 0.9), 2)}),

    ("healthcare", "Deny mental health coverage",
     lambda: {"diagnosis": random.choice(["depression","anxiety","PTSD"]),
               "employment_status": random.choice(["employed","unemployed"]),
               "prior_claims": random.randint(0, 5)}),

    # ── POLICY ──────────────────────────────────────────────────────────────
    ("policy", "Implement facial recognition for employee timekeeping",
     lambda: {"workforce_composition": random.choice(["diverse","majority white","majority minority"]),
               "accuracy_rate": random.choice(["92%","97%","85% on dark skin"])}),

    ("policy", "Mandate random drug testing for all employees",
     lambda: {"industry": random.choice(["finance","transportation","tech"]),
               "union_status": random.choice(["unionized","non-union"]),
               "prior_incidents": random.randint(0, 5)}),

    ("policy", "Enforce English-only workplace communication policy",
     lambda: {"workforce_languages": random.choice(["Spanish dominant","mixed","English dominant"]),
               "safety_relevance": random.choice(["low","high"])}),

    ("policy", "Implement AI-based performance monitoring",
     lambda: {"monitoring_scope": random.choice(["keystrokes","emails","video","location"]),
               "employee_consent": random.choice(["required","not required"]),
               "transparency": random.choice(["full","partial","none"])}),

    # ── PERSONAL ────────────────────────────────────────────────────────────
    ("personal", "Accept high-paying job that requires relocating family",
     lambda: {"family_impact": random.choice(["spouse career pause","kids school change","elderly parent"]),
               "salary_increase": f"{random.randint(20,80)}%",
               "reversibility": random.choice(["easy","difficult"])}),

    ("personal", "Report colleague's misconduct to HR",
     lambda: {"evidence_strength": random.choice(["strong","moderate","weak"]),
               "relationship": random.choice(["close friend","acquaintance","rival"]),
               "retaliation_risk": random.choice(["low","high"])}),

    ("personal", "Decline to donate organ to family member",
     lambda: {"health_risk_to_donor": random.choice(["low","moderate","high"]),
               "relationship": random.choice(["sibling","parent","distant relative"]),
               "alternatives_available": random.choice(["yes","no"])}),

    # ── OTHER ────────────────────────────────────────────────────────────────
    ("other", "Deploy AI system without human oversight",
     lambda: {"decision_impact": random.choice(["financial","legal","medical","social"]),
               "error_rate": f"{random.randint(1,15)}%",
               "appeal_process": random.choice(["yes","no"])}),

    ("other", "Share user data with third-party advertisers",
     lambda: {"consent_obtained": random.choice(["yes","no","buried in ToS"]),
               "data_sensitivity": random.choice(["location","health","financial","browsing"]),
               "opt_out_available": random.choice(["yes","no"])}),

    ("other", "Use unpaid intern labor for core business functions",
     lambda: {"educational_value": random.choice(["high","low","none"]),
               "intern_compensation": random.choice(["none","stipend","course credit"]),
               "market_rate": "$25/hr"}),
]


# ── Builder ───────────────────────────────────────────────────────────────────

def build_record(category: str, decision: str, context: dict, output: dict) -> dict:
    """Format a single training record."""
    user_msg = f"Category: {category}\nDecision: {decision}\nContext: {json.dumps(context)}"
    return {
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_msg},
            {"role": "assistant","content": json.dumps(output, indent=2)},
        ],
        # Also store flat version for easy inspection
        "meta": {"category": category, "decision": decision,
                  "risk_flags": output["risk_flags"],
                  "confidence_score": output["confidence_score"]},
    }


def generate(n_per_scenario: int = 3, output_dir: str = "ml/data") -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    records = []

    total = len(SCENARIOS) * n_per_scenario
    pbar = tqdm(total=total, desc="Generating")

    for category, decision, ctx_fn in SCENARIOS:
        for _ in range(n_per_scenario):
            context = ctx_fn()
            output = call_teacher(decision, context, category)
            if output:
                records.append(build_record(category, decision, context, output))
            time.sleep(0.3)   # gentle rate limiting
            pbar.update(1)

    pbar.close()
    random.shuffle(records)

    split = int(len(records) * 0.9)
    train, eval_ = records[:split], records[split:]

    for fname, data in [("train.jsonl", train), ("eval.jsonl", eval_)]:
        path = Path(output_dir) / fname
        with open(path, "w") as f:
            for r in data:
                f.write(json.dumps(r) + "\n")
        print(f"Saved {len(data)} records → {path}")

    print(f"\nTotal: {len(records)} examples  ({len(train)} train / {len(eval_)} eval)")
    print("Risk flag distribution:")
    all_flags = [f for r in records for f in r["meta"]["risk_flags"]]
    from collections import Counter
    for flag, count in Counter(all_flags).most_common():
        print(f"  {flag}: {count}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=3,
                        help="Samples per scenario template (default 3 → ~90 total)")
    parser.add_argument("--output", default="ml/data")
    args = parser.parse_args()
    generate(n_per_scenario=args.n, output_dir=args.output)
