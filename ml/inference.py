"""
Pragma Model — Local Inference
──────────────────────────────
Test the fine-tuned model locally before deploying to Railway.

Two modes:
  1. hf-api   — calls HuggingFace Inference API (fastest, needs HF_TOKEN + internet)
  2. local    — loads model weights on your machine (slower, fully offline after download)

Usage:
    # Mode 1 — HF Inference API (default, works right after Colab training)
    HF_TOKEN=hf_... python ml/inference.py \
        --repo yourname/pragma-ethics-v1 \
        --decision "Reject job candidate" \
        --category hiring \
        --context '{"gender": "female", "experience_years": 10}'

    # Mode 2 — Fully local (downloads ~4GB of weights first time)
    python ml/inference.py \
        --repo yourname/pragma-ethics-v1 \
        --mode local \
        --decision "Reject loan application" \
        --category finance \
        --context '{"credit_score": 650, "zip_code": "60620"}'
"""

import argparse
import json
import os
import sys
import time

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


def _parse_output(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def run_hf_api(repo: str, decision: str, category: str, context: dict) -> dict:
    """Call HuggingFace Inference API — fastest, no local GPU needed."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        sys.exit("pip install huggingface_hub")

    hf_token = os.environ.get("HF_TOKEN")
    client = InferenceClient(model=repo, token=hf_token)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Category: {category}\nDecision: {decision}\nContext: {json.dumps(context)}"},
    ]

    print(f"Calling HF Inference API: {repo}")
    t0 = time.time()
    response = client.chat_completion(messages=messages, max_new_tokens=512, temperature=0.1)
    elapsed = time.time() - t0

    text = response.choices[0].message.content or ""
    result = _parse_output(text)
    print(f"Latency: {elapsed:.1f}s")
    return result, text


def run_local(repo: str, decision: str, category: str, context: dict) -> dict:
    """Load model weights locally and run inference. ~4GB RAM, slow on CPU."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
        from peft import PeftModel
    except ImportError:
        sys.exit("pip install transformers peft torch accelerate bitsandbytes")

    hf_token = os.environ.get("HF_TOKEN")
    base_model = "microsoft/Phi-3-mini-4k-instruct"

    print(f"Loading base model: {base_model}")
    print("(First run downloads ~4GB — subsequent runs use cache)")

    # Use 4-bit if CUDA available, else float32 on CPU
    if torch.cuda.is_available():
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            base_model, quantization_config=bnb_config,
            device_map="auto", trust_remote_code=True,
        )
    else:
        print("No CUDA — running on CPU (will be slow, ~30-120s per inference)")
        model = AutoModelForCausalLM.from_pretrained(
            base_model, device_map="cpu", trust_remote_code=True,
            torch_dtype=torch.float32,
        )

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading LoRA adapter: {repo}")
    model = PeftModel.from_pretrained(model, repo, token=hf_token)
    model.eval()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Category: {category}\nDecision: {decision}\nContext: {json.dumps(context)}"},
    ]

    try:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        prompt = f"<|system|>\n{SYSTEM_PROMPT}<|end|>\n<|user|>\nCategory: {category}\nDecision: {decision}\nContext: {json.dumps(context)}<|end|>\n<|assistant|>\n"

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    print("Running inference...")
    t0 = time.time()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.time() - t0

    generated = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    result = _parse_output(generated)
    print(f"Latency: {elapsed:.1f}s")
    return result, generated


def main():
    parser = argparse.ArgumentParser(description="Test the Pragma model locally")
    parser.add_argument("--repo",     required=True, help="HF repo ID, e.g. yourname/pragma-ethics-v1")
    parser.add_argument("--mode",     default="hf-api", choices=["hf-api", "local"],
                        help="hf-api (default) or local (downloads model weights)")
    parser.add_argument("--decision", default="Reject job candidate",
                        help="Decision text to evaluate")
    parser.add_argument("--category", default="hiring",
                        choices=["hiring","workplace","finance","healthcare","policy","personal","other"])
    parser.add_argument("--context",  default='{"gender": "female", "experience_years": 10}',
                        help="JSON context string")
    args = parser.parse_args()

    try:
        context = json.loads(args.context)
    except json.JSONDecodeError as e:
        sys.exit(f"Invalid --context JSON: {e}")

    print(f"\n{'='*60}")
    print(f"Decision:  {args.decision}")
    print(f"Category:  {args.category}")
    print(f"Context:   {context}")
    print(f"Mode:      {args.mode}")
    print(f"{'='*60}\n")

    if args.mode == "hf-api":
        result, raw = run_hf_api(args.repo, args.decision, args.category, context)
    else:
        result, raw = run_local(args.repo, args.decision, args.category, context)

    if result is None:
        print("\n⚠ Could not parse JSON from model output.")
        print("Raw output:")
        print(raw)
        sys.exit(1)

    print("\n✅ Model output parsed successfully:\n")
    print(f"  Kantian:     {result.get('kantian_analysis','')[:120]}...")
    print(f"  Utilitarian: {result.get('utilitarian_analysis','')[:120]}...")
    print(f"  Virtue:      {result.get('virtue_ethics_analysis','')[:120]}...")
    print(f"  Risk flags:  {result.get('risk_flags', [])}")
    print(f"  Confidence:  {result.get('confidence_score', 0):.2f}")
    print(f"  Recommend:   {result.get('recommendation','')[:120]}...")

    print(f"\n{'='*60}")
    print("Model is working. To activate on Railway:")
    print(f"  CUSTOM_MODEL_REPO = {args.repo}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
