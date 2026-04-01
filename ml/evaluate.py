"""
Evaluate the fine-tuned student model against the teacher (Claude).

Computes:
  - JSON parse success rate
  - Risk flag overlap (Jaccard similarity)
  - Confidence score correlation
  - Recommendation BLEU (optional, needs sacrebleu)

Usage:
    python ml/evaluate.py \
        --student_repo yourname/pragma-ethics-v1 \
        --eval ml/data/eval.jsonl
"""

import argparse
import json
import os
from pathlib import Path


def _load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _parse_output(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def _jaccard(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def run_student(repo_id: str, messages: list[dict], hf_token: str | None) -> str:
    """Run inference on the student model via HF Inference API."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        raise SystemExit("pip install huggingface_hub")

    client = InferenceClient(model=repo_id, token=hf_token)
    response = client.chat_completion(
        messages=[{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "assistant"],
        max_new_tokens=512,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def evaluate(student_repo: str, eval_path: str, limit: int = 0) -> None:
    hf_token = os.environ.get("HF_TOKEN")
    records = _load_jsonl(eval_path)
    if limit:
        records = records[:limit]

    parse_ok = 0
    jaccard_sum = 0.0
    conf_diffs = []
    n = len(records)

    print(f"Evaluating {n} examples against student: {student_repo}\n")

    for i, record in enumerate(records):
        messages = record["messages"]
        teacher_out = json.loads(messages[-1]["content"])  # assistant message

        # Remove last assistant message; student must generate it
        inference_msgs = [m for m in messages if m["role"] != "assistant"]

        try:
            student_text = run_student(student_repo, inference_msgs, hf_token)
        except Exception as e:
            print(f"  [{i+1}/{n}] Inference error: {e}")
            continue

        student_out = _parse_output(student_text)
        if student_out is None:
            print(f"  [{i+1}/{n}] Parse FAIL — raw: {student_text[:80]!r}")
            continue

        parse_ok += 1
        j = _jaccard(teacher_out.get("risk_flags", []), student_out.get("risk_flags", []))
        jaccard_sum += j

        t_conf = float(teacher_out.get("confidence_score", 0.5))
        s_conf = float(student_out.get("confidence_score", 0.5))
        conf_diffs.append(abs(t_conf - s_conf))

        print(f"  [{i+1}/{n}] OK | risk_jaccard={j:.2f} | conf_delta={abs(t_conf-s_conf):.2f}")

    print(f"\n{'='*50}")
    print(f"Examples:          {n}")
    print(f"JSON parse rate:   {parse_ok/n*100:.1f}%  ({parse_ok}/{n})")
    if parse_ok:
        print(f"Risk flag Jaccard: {jaccard_sum/parse_ok:.3f}  (1.0 = perfect match)")
        print(f"Confidence MAE:    {sum(conf_diffs)/len(conf_diffs):.3f}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--student_repo", required=True,
                        help="HuggingFace repo ID of the fine-tuned model")
    parser.add_argument("--eval",   default="ml/data/eval.jsonl")
    parser.add_argument("--limit",  type=int, default=0,
                        help="Evaluate only N examples (0 = all)")
    args = parser.parse_args()
    evaluate(args.student_repo, args.eval, args.limit)
