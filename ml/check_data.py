"""Quick check on generated training data quality."""
import json
from pathlib import Path
from collections import Counter

data_dir = Path(__file__).parent / "data"

for fname in ("train.jsonl", "eval.jsonl"):
    path = data_dir / fname
    if not path.exists():
        print(f"{fname}: not found yet")
        continue
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    categories = Counter(r["meta"]["category"] for r in records)
    flags = Counter(f for r in records for f in r["meta"]["risk_flags"])
    avg_conf = sum(r["meta"]["confidence_score"] for r in records) / len(records)
    print(f"\n{fname}: {len(records)} records")
    print(f"  Categories: {dict(categories)}")
    print(f"  Risk flags: {dict(flags)}")
    print(f"  Avg confidence: {avg_conf:.2f}")
