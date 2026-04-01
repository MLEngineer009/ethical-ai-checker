"""
LLM Orchestrator — provider chain:
  1. Custom fine-tuned model (HuggingFace Inference API) — if CUSTOM_MODEL_REPO is set
  2. Claude (Anthropic) — primary cloud LLM
  3. OpenAI — fallback when Claude is rate-limited or out of credits
  4. Mock — last resort when all providers are unavailable
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import anthropic
from openai import OpenAI, RateLimitError as OpenAIRateLimitError

from .custom_model import CustomModelClient
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Errors that should trigger a fallback to OpenAI
_CLAUDE_FALLBACK_ERRORS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

_CLAUDE_CREDIT_MSG = "credit balance is too low"


def _build_user_prompt(decision: str, context: Dict[str, Any]) -> str:
    return USER_PROMPT_TEMPLATE.format(
        decision=decision,
        context=json.dumps(context)
    )


def _parse_response(text: str) -> Dict[str, Any]:
    """Extract and normalize JSON from LLM response text into our schema."""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            data = json.loads(text[start:end])
            return _normalize(data)
    except json.JSONDecodeError:
        pass
    return {
        "kantian_analysis": text[:200] if text else "",
        "utilitarian_analysis": "",
        "virtue_ethics_analysis": "",
        "risk_flags": [],
        "confidence_score": 0.5,
        "recommendation": "",
    }


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Claude's rich response format (or OpenAI's simpler format)
    into our fixed API schema.
    """
    # --- Kantian analysis ---
    kantian = (
        data.get("kantian_analysis")
        or _deep(data, "framework_analyses", "kantian_ethics", "analysis")
        or ""
    )

    # --- Utilitarian analysis ---
    utilitarian = (
        data.get("utilitarian_analysis")
        or _deep(data, "framework_analyses", "utilitarianism", "analysis")
        or ""
    )

    # --- Virtue ethics analysis ---
    virtue = (
        data.get("virtue_ethics_analysis")
        or _deep(data, "framework_analyses", "virtue_ethics", "analysis")
        or ""
    )

    # --- Risk flags: list or dict → flat list of strings ---
    raw_flags = data.get("risk_flags", [])
    if isinstance(raw_flags, dict):
        risk_flags = list(raw_flags.keys())
    elif isinstance(raw_flags, list):
        risk_flags = [str(f) for f in raw_flags]
    else:
        risk_flags = []

    # --- Confidence score ---
    confidence = (
        data.get("confidence_score")
        or _deep(data, "overall_assessment", "confidence_score")
        or 0.5
    )
    try:
        confidence = min(1.0, max(0.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    # --- Recommendation: string or structured dict → string ---
    rec = data.get("recommendation", "")
    if isinstance(rec, dict):
        action = rec.get("action", "")
        steps = rec.get("mitigation_steps", [])
        rec = action
        if steps:
            rec += "\n\n" + "\n".join(steps)
    rec = str(rec)

    return {
        "kantian_analysis": kantian,
        "utilitarian_analysis": utilitarian,
        "virtue_ethics_analysis": virtue,
        "risk_flags": risk_flags,
        "confidence_score": confidence,
        "recommendation": rec,
    }


def _deep(data: Dict, *keys: str) -> Any:
    """Safely traverse nested dict keys."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


class LLMOrchestrator:
    """
    Calls Claude (primary). Falls back to OpenAI when Claude is rate-limited
    or has insufficient credits. Returns which provider was used so callers
    can surface that to users/logs.
    """

    def __init__(self):
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")

        self._claude_model = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
        self._openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self._max_tokens = int(os.getenv("LLM_MAX_TOKENS", "16000"))

        self._custom = CustomModelClient()
        self._claude: Optional[anthropic.Anthropic] = (
            anthropic.Anthropic(api_key=anthropic_key) if anthropic_key else None
        )
        self._openai: Optional[OpenAI] = (
            OpenAI(api_key=openai_key)
            if openai_key and openai_key != "your-openai-key-here"
            else None
        )

    def evaluate(self, decision: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns analysis dict with an extra 'provider' key indicating
        which LLM was used: 'claude', 'openai', or 'mock'.
        """
        user_prompt = _build_user_prompt(decision, context)

        # --- Try custom fine-tuned model (fastest, cheapest) ---
        if self._custom.available:
            result = self._custom.evaluate(SYSTEM_PROMPT, user_prompt)
            if result is not None:
                result["provider"] = "custom"
                logger.info("Request handled by custom model (%s)", os.getenv("CUSTOM_MODEL_REPO", ""))
                return result
            logger.warning("Custom model returned None — falling back to Claude")

        # --- Try Claude ---
        if self._claude:
            try:
                result = self._call_claude(user_prompt)
                result["provider"] = "claude"
                logger.info("Request handled by Claude (%s)", self._claude_model)
                return result
            except _CLAUDE_FALLBACK_ERRORS as e:
                logger.warning("Claude unavailable (%s: %s) — falling back to OpenAI", type(e).__name__, e)
            except anthropic.BadRequestError as e:
                if _CLAUDE_CREDIT_MSG in str(e).lower():
                    logger.warning("Claude credits exhausted — falling back to OpenAI")
                else:
                    raise
            except anthropic.AuthenticationError:
                logger.warning("Claude auth failed — falling back to OpenAI")

        # --- Try OpenAI ---
        if self._openai:
            try:
                result = self._call_openai(user_prompt)
                result["provider"] = "openai"
                logger.info("Request handled by OpenAI (%s)", self._openai_model)
                return result
            except OpenAIRateLimitError:
                logger.error("OpenAI also rate-limited — returning mock response")
            except Exception as e:
                logger.error("OpenAI error: %s", e)

        # --- Mock fallback ---
        logger.warning("No LLM available — returning mock response")
        return self._mock_response()

    def _call_claude(self, user_prompt: str) -> Dict[str, Any]:
        with self._claude.messages.stream(
            model=self._claude_model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            response = stream.get_final_message()

        text = next(
            (block.text for block in response.content if block.type == "text"), ""
        )
        return _parse_response(text)

    def _call_openai(self, user_prompt: str) -> Dict[str, Any]:
        response = self._openai.chat.completions.create(
            model=self._openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        text = response.choices[0].message.content or ""
        return _parse_response(text)

    @staticmethod
    def _mock_response() -> Dict[str, Any]:
        return {
            "kantian_analysis": "Unable to connect to LLM. Please configure a valid API key with sufficient credits.",
            "utilitarian_analysis": "Unable to connect to LLM. Please configure a valid API key with sufficient credits.",
            "virtue_ethics_analysis": "Unable to connect to LLM. Please configure a valid API key with sufficient credits.",
            "risk_flags": [],
            "confidence_score": 0.0,
            "recommendation": "No LLM available. Add credits to Anthropic or provide an OpenAI API key.",
            "provider": "mock",
        }
