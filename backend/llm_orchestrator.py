"""
Pragma Model Orchestrator
─────────────────────────
The Pragma model is our competitive moat — a domain-specific ethical reasoning
model trained entirely on structured ethical analysis. It improves every training
cycle via the user-feedback flywheel (see ml/collect_feedback.py).

Production provider chain:
  1. Pragma model  — our fine-tuned model (HF Inference API); primary in production
  2. Claude        — fallback while Pragma model is still being trained/improved
  3. OpenAI        — fallback if Claude is rate-limited or out of credits
  4. Mock          — last resort; clearly signals no model is configured

Claude and OpenAI are OFFLINE teachers: they generate labelled training data
(ml/generate_data.py) and are not meant to be the long-term production path.
The goal is to phase them out of production as the Pragma model matures.
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
                result["provider"] = "pragma"
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

        # --- Heuristic fallback ---
        logger.warning("No LLM available — returning heuristic mock response")
        from .risk_detector import detect_all_risks
        flags = detect_all_risks(decision, context)
        return self._mock_response(decision=decision, flags=flags)

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
    def _mock_response(decision: str = "", flags: list = []) -> Dict[str, Any]:
        """Heuristic-driven fallback — gives realistic responses without an LLM."""
        has_risk = len(flags) >= 2
        flag_str = ", ".join(flags) if flags else "none detected"

        if has_risk:
            kantian = (
                f"This decision raises serious ethical concerns under Kantian ethics. "
                f"Detected risks ({flag_str}) suggest the decision may treat individuals as means rather than ends, "
                f"violating the categorical imperative to act only according to principles you could will to be universal law."
            )
            utilitarian = (
                f"From a utilitarian standpoint, this decision is likely to cause net harm. "
                f"The identified risk factors ({flag_str}) indicate potential discriminatory outcomes "
                f"that reduce overall wellbeing and could expose the organization to significant legal and reputational costs."
            )
            virtue = (
                f"A person of good character would not make this decision as stated. "
                f"The presence of {flag_str} risks reflects a failure of the virtues of fairness, justice, and integrity "
                f"that should guide responsible decision-making."
            )
            confidence = 0.85
            recommendation = (
                f"This decision should not proceed without revision. Remove or justify any criteria linked to "
                f"{flag_str}. Ensure the decision is based solely on objective, relevant factors and document "
                f"your reasoning to demonstrate compliance with applicable regulations."
            )
        else:
            kantian = (
                "This decision appears consistent with Kantian ethics. It treats individuals with respect "
                "and does not appear to use morally impermissible means to achieve its end."
            )
            utilitarian = (
                "From a utilitarian perspective, this decision appears reasonable. "
                "No significant harm to affected parties is evident from the available information."
            )
            virtue = (
                "This decision reflects the kind of judgment a fair and conscientious person would make. "
                "No obvious violations of fairness, honesty, or integrity are apparent."
            )
            confidence = 0.3
            recommendation = (
                "No significant risks detected. Proceed with standard documentation practices "
                "and ensure decision criteria are recorded for audit purposes."
            )

        return {
            "kantian_analysis": kantian,
            "utilitarian_analysis": utilitarian,
            "virtue_ethics_analysis": virtue,
            "risk_flags": flags,
            "confidence_score": confidence,
            "recommendation": recommendation,
            "provider": "pragma",
        }
