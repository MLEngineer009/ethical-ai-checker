"""
Pragma Model Client
────────────────────
Calls the Pragma model. Supports two backends:

  1. Ollama (local)        — OLLAMA_MODEL=qwen2.5:1.5b (or any ollama model)
                             Runs on your machine. No account needed. Works now.

  2. HuggingFace API       — CUSTOM_MODEL_REPO=yourname/pragma-ethics-v1
                             Fine-tuned model on HF Hub. Production path.

Priority: Ollama → HuggingFace → disabled (falls through to Claude in orchestrator)

If neither is configured, this module is a no-op and the orchestrator
continues to Claude/OpenAI.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CustomModelClient:

    def __init__(self):
        self._client = None
        self._backend: str = "none"

        ollama_model = os.getenv("OLLAMA_MODEL", "").strip()
        hf_repo      = os.getenv("CUSTOM_MODEL_REPO", "").strip()
        hf_token     = os.getenv("HF_TOKEN", "").strip() or None
        ollama_url   = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")

        # ── Try Ollama first (local, no account needed) ───────────────────────
        if ollama_model:
            try:
                import httpx  # already in requirements via httpx
                # quick connectivity check
                r = httpx.get(f"{ollama_url}/api/tags", timeout=3)
                if r.status_code == 200:
                    self._client = {"type": "ollama", "model": ollama_model, "url": ollama_url}
                    self._backend = "ollama"
                    logger.info("Pragma model → Ollama (%s @ %s)", ollama_model, ollama_url)
                else:
                    logger.warning("Ollama reachable but returned %s", r.status_code)
            except Exception as e:
                logger.warning("Ollama not reachable (%s) — trying HF API", e)

        # ── Try HuggingFace Inference API ─────────────────────────────────────
        if self._client is None and hf_repo:
            try:
                from huggingface_hub import InferenceClient
                self._client = InferenceClient(model=hf_repo, token=hf_token)
                self._backend = "hf"
                logger.info("Pragma model → HuggingFace (%s)", hf_repo)
            except ImportError:
                logger.warning("huggingface_hub not installed — pip install huggingface_hub")

        if self._client is None:
            logger.debug("No Pragma model configured (set OLLAMA_MODEL or CUSTOM_MODEL_REPO)")

    @property
    def available(self) -> bool:
        return self._client is not None

    def evaluate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        try:
            if self._backend == "ollama":
                return self._call_ollama(system_prompt, user_prompt, max_tokens, temperature)
            else:
                return self._call_hf(system_prompt, user_prompt, max_tokens, temperature)
        except Exception as e:
            logger.warning("Pragma model inference error: %s", e)
            return None

    def _call_ollama(self, system_prompt: str, user_prompt: str,
                     max_tokens: int, temperature: float) -> Optional[Dict[str, Any]]:
        import httpx
        url   = self._client["url"]
        model = self._client["model"]

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        r = httpx.post(f"{url}/api/chat", json=payload, timeout=60)
        r.raise_for_status()
        text = r.json()["message"]["content"]
        return _parse_response(text)

    def _call_hf(self, system_prompt: str, user_prompt: str,
                 max_tokens: int, temperature: float) -> Optional[Dict[str, Any]]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        response = self._client.chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=temperature,
        )
        text = response.choices[0].message.content or ""
        return _parse_response(text)


def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= start:
        logger.debug("Pragma model: no JSON in output: %r", text[:100])
        return None
    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError as e:
        logger.debug("Pragma model: JSON parse error: %s", e)
        return None

    required = {
        "kantian_analysis", "utilitarian_analysis", "virtue_ethics_analysis",
        "risk_flags", "confidence_score", "recommendation",
    }
    if not required.issubset(data):
        logger.debug("Pragma model: missing fields %s", required - set(data.keys()))
        return None

    try:
        data["confidence_score"] = min(1.0, max(0.0, float(data["confidence_score"])))
    except (TypeError, ValueError):
        data["confidence_score"] = 0.5

    if isinstance(data["risk_flags"], list):
        data["risk_flags"] = [str(f) for f in data["risk_flags"]]
    else:
        data["risk_flags"] = []

    return data
