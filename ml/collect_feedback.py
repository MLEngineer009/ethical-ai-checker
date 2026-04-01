"""
Pragma Model Retraining Flywheel
──────────────────────────────────
Reads user feedback from the database and:

1. Shows which categories the Pragma model is underperforming in
   (low approval rate = users thumbs-down those analyses)

2. Generates targeted training data for weak categories by calling
   Claude (teacher) on MORE examples in those categories.

3. Merges new examples into the existing training set so the next
   fine-tuning run (ml/train.py) automatically improves on weak spots.

This closes the loop:
  User feedback → weak category detection → more targeted data → retrain → better model

Usage:
    DATABASE_URL=postgresql://... ANTHROPIC_API_KEY=sk-ant-... \\
        python ml/collect_feedback.py --threshold 0.7 --extra_per_weak 10

    --threshold      Approval rate below which a category is considered "weak" (default 0.70)
    --extra_per_weak How many new examples to generate per weak category (default 10)
    --dry_run        Print the plan without calling the API or writing files
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# ── Make sure backend is importable ──────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from backend import database


# ── Teacher (same prompt as generate_data.py) ─────────────────────────────────

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

# Category-specific scenario templates for targeted generation
# These match the categories in generate_data.py but are separate so we can
# call them independently for weak-category retraining.
CATEGORY_TEMPLATES = {
    "hiring": [
        ("Reject candidate based on automated screening", lambda: {
            "screening_tool": "AI resume parser",
            "match_score": __import__("random").randint(30, 70),
            "gender": __import__("random").choice(["female", "male", "non-binary"]),
        }),
        ("Rescind job offer after background check", lambda: {
            "reason": __import__("random").choice(["criminal record", "credit history", "social media"]),
            "job_relevance": __import__("random").choice(["low", "medium", "high"]),
            "time_since_incident": __import__("random").choice(["1 year", "5 years", "10 years"]),
        }),
    ],
    "workplace": [
        ("Exclude employee from key meetings", lambda: {
            "reason_given": __import__("random").choice(["performance", "not a fit", "no reason"]),
            "protected_class": __import__("random").choice(["yes", "no"]),
            "seniority": __import__("random").choice(["junior", "senior"]),
        }),
        ("Reassign employee after medical leave", lambda: {
            "leave_type": __import__("random").choice(["maternity", "mental health", "surgery"]),
            "role_change": __import__("random").choice(["lateral", "demotion", "same"]),
            "performance_history": __import__("random").choice(["strong", "average"]),
        }),
    ],
    "finance": [
        ("Decline small business loan", lambda: {
            "owner_ethnicity": __import__("random").choice(["Black", "White", "Hispanic", "Asian"]),
            "business_revenue": __import__("random").randint(50000, 500000),
            "years_operating": __import__("random").randint(1, 10),
        }),
        ("Charge higher interest rate to new customer", lambda: {
            "credit_score": __import__("random").randint(600, 780),
            "zip_code_income_bracket": __import__("random").choice(["low", "medium", "high"]),
            "account_type": __import__("random").choice(["checking", "savings"]),
        }),
    ],
    "healthcare": [
        ("Delay referral to specialist", lambda: {
            "insurance_type": __import__("random").choice(["medicaid", "private", "none"]),
            "wait_time_weeks": __import__("random").randint(4, 20),
            "condition_severity": __import__("random").choice(["mild", "moderate", "severe"]),
        }),
        ("Recommend lifestyle changes instead of medication", lambda: {
            "patient_race": __import__("random").choice(["Black", "White", "Hispanic"]),
            "bmi": __import__("random").randint(25, 40),
            "pain_reported": __import__("random").randint(4, 9),
        }),
    ],
    "policy": [
        ("Remove employee privacy protections for productivity monitoring", lambda: {
            "monitoring_type": __import__("random").choice(["screen recording", "location", "keystrokes"]),
            "legal_review": __import__("random").choice(["done", "not done"]),
            "employee_notification": __import__("random").choice(["yes", "no"]),
        }),
        ("Implement zero-tolerance attendance policy", lambda: {
            "affected_groups": __import__("random").choice(["caregivers", "disabled", "general"]),
            "remote_option": __import__("random").choice(["available", "not available"]),
            "exceptions": __import__("random").choice(["none", "medical only", "manager discretion"]),
        }),
    ],
    "personal": [
        ("Cut off contact with a family member", lambda: {
            "reason": __import__("random").choice(["abuse", "disagreement", "lifestyle"]),
            "impact_on_others": __import__("random").choice(["children affected", "none", "extended family"]),
            "reversibility": __import__("random").choice(["easy", "difficult"]),
        }),
        ("Take credit for a colleague's idea", lambda: {
            "relationship": __import__("random").choice(["peer", "direct report", "contractor"]),
            "idea_impact": __import__("random").choice(["low", "high"]),
            "colleague_awareness": __import__("random").choice(["aware", "unaware"]),
        }),
    ],
    "other": [
        ("Use customer data to train internal AI without consent", lambda: {
            "data_type": __import__("random").choice(["behavioral", "purchase history", "communications"]),
            "anonymized": __import__("random").choice(["yes", "partial", "no"]),
            "opt_out_available": __import__("random").choice(["yes", "no"]),
        }),
    ],
}


def call_teacher(decision: str, context: dict, category: str) -> dict | None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
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
        return json.loads(text[start:end])
    except Exception as e:
        print(f"  Teacher error: {e}")
        return None


def build_record(category: str, decision: str, context: dict, output: dict) -> dict:
    user_msg = f"Category: {category}\nDecision: {decision}\nContext: {json.dumps(context)}"
    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": json.dumps(output, indent=2)},
        ],
        "meta": {
            "category": category, "decision": decision,
            "risk_flags": output.get("risk_flags", []),
            "confidence_score": output.get("confidence_score", 0.5),
            "source": "flywheel",
        },
    }


def run(threshold: float, extra_per_weak: int, dry_run: bool, data_dir: str) -> None:
    database.init_db()
    stats = database.get_feedback_stats()

    print(f"\nFeedback summary: {stats['total']} total ratings\n")

    if stats["total"] == 0:
        print("No feedback collected yet. Run the app and collect some user ratings first.")
        return

    # ── Identify weak categories ────────────────────────────────────────────
    weak = []
    print(f"{'Category':<15} {'Approval':>10} {'Up':>6} {'Down':>6} {'Status'}")
    print("-" * 50)
    for cat, counts in sorted(stats["by_category"].items()):
        rate = counts["approval_rate"]
        status = "WEAK ⚠" if rate < threshold else "OK ✓"
        print(f"{cat:<15} {rate:>10.1%} {counts['up']:>6} {counts['down']:>6}  {status}")
        if rate < threshold:
            weak.append(cat)

    print()

    if not weak:
        print(f"All categories above {threshold:.0%} approval threshold. No extra data needed.")
        return

    print(f"Weak categories needing more training data: {', '.join(weak)}\n")

    if dry_run:
        for cat in weak:
            templates = CATEGORY_TEMPLATES.get(cat, [])
            print(f"  Would generate {extra_per_weak} examples for '{cat}' "
                  f"using {len(templates)} template(s)")
        print("\n(dry-run — no API calls made, no files written)")
        return

    # ── Generate targeted training data for weak categories ──────────────────
    import random
    new_records = []
    for cat in weak:
        templates = CATEGORY_TEMPLATES.get(cat, [])
        if not templates:
            print(f"  No templates defined for '{cat}' — skipping")
            continue
        print(f"Generating {extra_per_weak} examples for weak category: {cat}")
        for i in range(extra_per_weak):
            decision, ctx_fn = random.choice(templates)
            context = ctx_fn()
            output = call_teacher(decision, context, cat)
            if output:
                new_records.append(build_record(cat, decision, context, output))
                print(f"  [{i+1}/{extra_per_weak}] OK — confidence={output.get('confidence_score', '?'):.2f}")
            time.sleep(0.3)

    if not new_records:
        print("No new records generated.")
        return

    # ── Append to existing training data ─────────────────────────────────────
    train_path = Path(data_dir) / "train.jsonl"
    with open(train_path, "a") as f:
        for r in new_records:
            f.write(json.dumps(r) + "\n")

    print(f"\nAppended {len(new_records)} new examples to {train_path}")
    print("Next step: re-run ml/train.py to fine-tune Pragma model on updated dataset.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pragma retraining flywheel")
    parser.add_argument("--threshold",       type=float, default=0.70,
                        help="Approval rate below which a category is 'weak' (default 0.70)")
    parser.add_argument("--extra_per_weak",  type=int,   default=10,
                        help="New examples to generate per weak category (default 10)")
    parser.add_argument("--data_dir",        default="ml/data")
    parser.add_argument("--dry_run",         action="store_true",
                        help="Print plan without calling API or writing files")
    args = parser.parse_args()

    run(
        threshold      = args.threshold,
        extra_per_weak = args.extra_per_weak,
        dry_run        = args.dry_run,
        data_dir       = args.data_dir,
    )
