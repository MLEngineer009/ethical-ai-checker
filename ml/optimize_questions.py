"""
Pragma — Question Signal Optimizer
────────────────────────────────────
Analyzes request_logs + analysis_feedback to rank which context questions
produce the highest-quality model responses. Outputs a ranked signal report
and optionally rewrites backend/questions.py with the optimized ordering.

How signal is computed per (category, question_key):
  Δconfidence   = avg_confidence_WITH_key  - avg_confidence_WITHOUT_key
  Δapproval     = approval_rate_WITH_key   - approval_rate_WITHOUT_key
  signal_score  = Δconfidence + Δapproval   (range: -2.0 → +2.0)

Questions with signal_score > 0.05 are valuable — keep / promote.
Questions with signal_score < 0     are noise   — deprioritize / remove.

Usage:
    python ml/optimize_questions.py
    python ml/optimize_questions.py --min_samples 50 --apply
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Ensure we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import database
from backend.questions import QUESTIONS, VERSION


# ── DB helpers ────────────────────────────────────────────────────────────────

def load_request_logs():
    """Load all request_logs rows as dicts."""
    with database._engine.connect() as conn:
        rows = conn.execute(database.request_logs.select()).fetchall()
    return [dict(r._mapping) for r in rows]


def load_feedback():
    """Load all analysis_feedback rows as dicts."""
    with database._engine.connect() as conn:
        rows = conn.execute(database.analysis_feedback.select()).fetchall()
    return [dict(r._mapping) for r in rows]


# ── Signal computation ────────────────────────────────────────────────────────

def compute_signal(logs: list, feedback: list, min_samples: int) -> dict:
    """
    Returns:
      {
        category: {
          question_key: {
            "n_with": int,
            "n_without": int,
            "avg_confidence_with": float,
            "avg_confidence_without": float,
            "approval_with": float | None,
            "approval_without": float | None,
            "signal_score": float,
          }
        }
      }
    """
    # Build feedback lookup: anon_id+timestamp → rating
    # We use category + provider as a loose join key
    # (exact join requires request_id on feedback, future improvement)
    feedback_by_cat: dict = defaultdict(list)
    for f in feedback:
        feedback_by_cat[f["category"]].append(f["rating"])

    # Per-category per-key: collect confidence scores
    # keyed as [category][key] = {"with": [], "without": []}
    buckets: dict = defaultdict(lambda: defaultdict(lambda: {"with": [], "without": []}))

    known_keys: dict = {cat: {q["key"] for q in qs} for cat, qs in QUESTIONS.items()}

    for row in logs:
        cat = row.get("category", "other")
        if cat not in known_keys:
            continue
        try:
            ctx_keys = set(json.loads(row.get("context_keys") or "[]"))
        except (json.JSONDecodeError, TypeError):
            continue
        confidence = row.get("confidence") or 0.0

        for key in known_keys[cat]:
            bucket = "with" if key in ctx_keys else "without"
            buckets[cat][key][bucket].append(confidence)

    # Build feedback approval per category
    approval_by_cat: dict = {}
    for cat, ratings in feedback_by_cat.items():
        if ratings:
            approval_by_cat[cat] = sum(1 for r in ratings if r == 1) / len(ratings)

    # Compute signal scores
    result: dict = {}
    for cat, keys in known_keys.items():
        result[cat] = {}
        for key in keys:
            b = buckets[cat][key]
            n_with    = len(b["with"])
            n_without = len(b["without"])

            if n_with < min_samples:
                # Not enough data — mark as unranked
                result[cat][key] = {
                    "n_with": n_with,
                    "n_without": n_without,
                    "avg_confidence_with": None,
                    "avg_confidence_without": None,
                    "approval_with": None,
                    "approval_without": None,
                    "signal_score": None,
                    "unranked": True,
                }
                continue

            avg_with    = sum(b["with"])    / n_with    if n_with    else 0.0
            avg_without = sum(b["without"]) / n_without if n_without else 0.0
            delta_conf  = avg_with - avg_without

            # Approval signal: simplified — use category-level approval as proxy
            # (future: join on request_id for per-request signal)
            approval = approval_by_cat.get(cat)
            delta_approval = 0.0  # placeholder until per-request join is available

            signal = round(delta_conf + delta_approval, 4)

            result[cat][key] = {
                "n_with": n_with,
                "n_without": n_without,
                "avg_confidence_with": round(avg_with, 3),
                "avg_confidence_without": round(avg_without, 3),
                "approval_with": approval,
                "approval_without": approval,
                "signal_score": signal,
                "unranked": False,
            }
    return result


# ── Report printing ───────────────────────────────────────────────────────────

def print_report(signal: dict):
    print(f"\n{'='*64}")
    print(f"  Pragma — Question Signal Report  (questions v{VERSION})")
    print(f"{'='*64}\n")

    for cat, keys in signal.items():
        ranked   = [(k, v) for k, v in keys.items() if not v.get("unranked")]
        unranked = [(k, v) for k, v in keys.items() if v.get("unranked")]

        if not ranked and not unranked:
            continue

        print(f"── {cat.upper()} {'─'*(50-len(cat))}")

        if ranked:
            ranked.sort(key=lambda x: x[1]["signal_score"], reverse=True)
            print(f"  {'Question key':<30} {'n_with':>7} {'Δconf':>7} {'signal':>8}")
            print(f"  {'─'*30} {'─'*7} {'─'*7} {'─'*8}")
            for key, v in ranked:
                flag = "  ✅ keep" if v["signal_score"] > 0.05 else ("  ⚠ low" if v["signal_score"] >= 0 else "  ❌ drop")
                print(f"  {key:<30} {v['n_with']:>7} {v['avg_confidence_with']-v['avg_confidence_without']:>+7.3f} {v['signal_score']:>8.4f}{flag}")
        if unranked:
            print(f"\n  Insufficient data (< min_samples):")
            for key, v in unranked:
                print(f"    {key}  (n={v['n_with']})")
        print()


# ── Optional: reorder questions.py by signal ─────────────────────────────────

def apply_optimized_ordering(signal: dict):
    """
    Reorder questions within each category by signal_score (desc).
    Unranked questions are appended at the end in original order.
    Bumps the VERSION in questions.py.
    """
    from backend import questions as qmod
    import re

    questions_path = Path(__file__).parent.parent / "backend" / "questions.py"
    src = questions_path.read_text()

    # Bump patch version
    major, minor, patch = [int(x) for x in qmod.VERSION.split(".")]
    new_version = f"{major}.{minor}.{patch + 1}"
    src = re.sub(r'VERSION = "[^"]+"', f'VERSION = "{new_version}"', src)

    questions_path.write_text(src)
    print(f"✅ VERSION bumped {qmod.VERSION} → {new_version}")
    print("   Reorder questions.py manually based on the signal report above.")
    print("   (Auto-rewrite of QUESTIONS dict is a future enhancement.)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rank Pragma context questions by signal value")
    parser.add_argument("--min_samples", type=int, default=20,
                        help="Minimum requests with a question key to compute signal (default: 20)")
    parser.add_argument("--apply", action="store_true",
                        help="Bump VERSION in questions.py after printing report")
    parser.add_argument("--json", action="store_true",
                        help="Output raw signal data as JSON instead of formatted report")
    args = parser.parse_args()

    database.init_db()

    print("Loading request logs and feedback...")
    logs     = load_request_logs()
    feedback = load_feedback()
    print(f"  {len(logs)} requests · {len(feedback)} feedback ratings")

    if not logs:
        print("\nNo data yet. Run some evaluations first, then re-run this script.")
        return

    signal = compute_signal(logs, feedback, args.min_samples)

    if args.json:
        print(json.dumps(signal, indent=2))
    else:
        print_report(signal)

    if args.apply:
        apply_optimized_ordering(signal)


if __name__ == "__main__":
    main()
