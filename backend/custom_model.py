"""
Custom model client — calls the fine-tuned Pragma student model
hosted on HuggingFace Inference API.

Set env vars:
    CUSTOM_MODEL_REPO  — HuggingFace repo ID, e.g. "yourname/pragma-ethics-v1"
    HF_TOKEN           — HuggingFace token (optional for public repos)

If CUSTOM_MODEL_REPO is not set, this module is a no-op and the orchestrator
continues to use Claude/OpenAI.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CustomModelClient:
    """
    Wraps the HuggingFace Inference API for the fine-tuned student model.
    Returns None on any error so the orchestrator can fall through to Claude.
    """

    def __init__(self):
        self._repo_id: Optional[str] = os.getenv("CUSTOM_MODEL_REPO", "").strip() or None
        self._hf_token: Optional[str] = os.getenv("HF_TOKEN", "").strip() or None
        self._client = None

        if self._repo_id:
            try:
                from huggingface_hub import InferenceClient
                self._client = InferenceClient(
                    model=self._repo_id,
                    token=self._hf_token,
                )
                logger.info("Custom model client ready: %s", self._repo_id)
            except ImportError:
                logger.warning(
                    "huggingface_hub not installed — custom model disabled. "
                    "Run: pip install huggingface_hub"
                )
        else:
            logger.debug("CUSTOM_MODEL_REPO not set — custom model disabled")

    @property
    def available(self) -> bool:
        return self._client is not None

    def evaluate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """
        Call the fine-tuned model. Returns parsed dict or None on failure.
        """
        if not self._client:
            return None

        messages = [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_prompt},
        ]

        try:
            response = self._client.chat_completion(
                messages=messages,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            )
            text = response.choices[0].message.content or ""
            return _parse_response(text)
        except Exception as e:
            logger.warning("Custom model inference error: %s", e)
            return None


def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from model output."""
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= start:
        logger.debug("Custom model: no JSON found in output: %r", text[:100])
        return None
    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError as e:
        logger.debug("Custom model: JSON parse error: %s", e)
        return None

    required = {
        "kantian_analysis", "utilitarian_analysis", "virtue_ethics_analysis",
        "risk_flags", "confidence_score", "recommendation",
    }
    if not required.issubset(data):
        missing = required - set(data.keys())
        logger.debug("Custom model: missing fields %s", missing)
        return None

    # Sanitize confidence score
    try:
        data["confidence_score"] = min(1.0, max(0.0, float(data["confidence_score"])))
    except (TypeError, ValueError):
        data["confidence_score"] = 0.5

    # Ensure risk_flags is a list of strings
    if isinstance(data["risk_flags"], list):
        data["risk_flags"] = [str(f) for f in data["risk_flags"]]
    else:
        data["risk_flags"] = []

    return data
