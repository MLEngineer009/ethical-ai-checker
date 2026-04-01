"""
LoRA fine-tuning script for the Pragma student model.

Designed to run on Google Colab (free T4 GPU) or any CUDA machine.

Usage (Colab):
    !pip install transformers peft trl datasets accelerate bitsandbytes huggingface_hub
    !python ml/train.py --hf_repo YOUR_HF_USERNAME/pragma-ethics-v1

Required env vars:
    HF_TOKEN — HuggingFace token with write access (set in Colab secrets)

Steps:
    1. Upload ml/data/train.jsonl and ml/data/eval.jsonl to Colab
    2. Run this script
    3. Model is pushed to HuggingFace Hub automatically
"""

import argparse
import json
import os
from pathlib import Path

# ── Guard: these packages are only needed at training time ────────────────────
try:
    import torch
    from datasets import Dataset
    from huggingface_hub import login
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from trl import SFTTrainer, SFTConfig
except ImportError as e:
    raise SystemExit(
        f"Missing training dependency: {e}\n"
        "Run: pip install transformers peft trl datasets accelerate bitsandbytes huggingface_hub"
    )


# ── Defaults ──────────────────────────────────────────────────────────────────

BASE_MODEL = "microsoft/Phi-3-mini-4k-instruct"   # 3.8B — fits in T4 (16 GB)
# Alternative if Phi-3 gives OOM: "meta-llama/Llama-3.2-3B-Instruct"

LORA_CONFIG = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,               # rank — higher = more capacity, more VRAM
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["qkv_proj", "o_proj", "gate_up_proj", "down_proj"],  # Phi-3
    bias="none",
)


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _record_to_text(record: dict, tokenizer) -> str:
    """
    Convert a training record (messages format) to a single string
    using the model's chat template.
    """
    messages = record["messages"]
    # Use apply_chat_template if available, else format manually
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
    # Fallback: manual formatting
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        parts.append(f"<|{role}|>\n{content}<|end|>")
    return "\n".join(parts)


def build_dataset(jsonl_path: str, tokenizer) -> Dataset:
    records = _load_jsonl(jsonl_path)
    texts = [_record_to_text(r, tokenizer) for r in records]
    return Dataset.from_dict({"text": texts})


# ── Training ──────────────────────────────────────────────────────────────────

def train(
    base_model: str,
    train_path: str,
    eval_path: str,
    hf_repo: str,
    output_dir: str = "ml/checkpoints",
    num_epochs: int = 3,
    batch_size: int = 2,
    grad_accum: int = 8,
    max_seq_len: int = 1024,
    lr: float = 2e-4,
) -> None:
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise SystemExit("Set HF_TOKEN env var to your HuggingFace write token.")
    login(token=hf_token)

    print(f"Loading base model: {base_model}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model.config.pretraining_tp = 1

    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    print("Building datasets...")
    train_ds = build_dataset(train_path, tokenizer)
    eval_ds  = build_dataset(eval_path,  tokenizer)
    print(f"  Train: {len(train_ds)} examples")
    print(f"  Eval:  {len(eval_ds)} examples")

    sft_config = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        gradient_checkpointing=True,
        optim="paged_adamw_32bit",
        learning_rate=lr,
        weight_decay=0.001,
        fp16=True,
        bf16=False,
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=10,
        max_seq_length=max_seq_len,
        dataset_text_field="text",
        packing=False,
        push_to_hub=True,
        hub_model_id=hf_repo,
        hub_token=hf_token,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=sft_config,
        tokenizer=tokenizer,
    )

    print("Starting training...")
    trainer.train()

    print(f"Pushing adapter to HuggingFace Hub: {hf_repo}")
    trainer.push_to_hub()
    tokenizer.push_to_hub(hf_repo, token=hf_token)

    print(f"\nDone! Model available at: https://huggingface.co/{hf_repo}")
    print("Next step: set CUSTOM_MODEL_REPO env var in Railway dashboard to this repo ID.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Pragma student model via LoRA")
    parser.add_argument("--base_model",  default=BASE_MODEL)
    parser.add_argument("--train",       default="ml/data/train.jsonl")
    parser.add_argument("--eval",        default="ml/data/eval.jsonl")
    parser.add_argument("--hf_repo",     required=True,
                        help="HuggingFace repo ID, e.g. yourname/pragma-ethics-v1")
    parser.add_argument("--output_dir",  default="ml/checkpoints")
    parser.add_argument("--epochs",      type=int,   default=3)
    parser.add_argument("--batch_size",  type=int,   default=2)
    parser.add_argument("--grad_accum",  type=int,   default=8)
    parser.add_argument("--max_seq_len", type=int,   default=1024)
    parser.add_argument("--lr",          type=float, default=2e-4)
    args = parser.parse_args()

    train(
        base_model  = args.base_model,
        train_path  = args.train,
        eval_path   = args.eval,
        hf_repo     = args.hf_repo,
        output_dir  = args.output_dir,
        num_epochs  = args.epochs,
        batch_size  = args.batch_size,
        grad_accum  = args.grad_accum,
        max_seq_len = args.max_seq_len,
        lr          = args.lr,
    )
