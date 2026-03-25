"""Unit tests for backend/llm_orchestrator.py — LLM clients are mocked."""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import anthropic
from openai import RateLimitError as OpenAIRateLimitError

from backend.llm_orchestrator import (
    _deep,
    _parse_response,
    _normalize,
    _build_user_prompt,
    LLMOrchestrator,
)


# ── Helper function tests ──────────────────────────────────────────────────────

class TestDeep:
    def test_single_key(self):
        assert _deep({"a": 1}, "a") == 1

    def test_nested_keys(self):
        assert _deep({"a": {"b": {"c": 99}}}, "a", "b", "c") == 99

    def test_missing_key_returns_none(self):
        assert _deep({"a": 1}, "b") is None

    def test_non_dict_mid_path_returns_none(self):
        assert _deep({"a": "string"}, "a", "b") is None

    def test_empty_dict(self):
        assert _deep({}, "a") is None


class TestParseResponse:
    def test_valid_json_extracted(self):
        data = {
            "kantian_analysis": "K", "utilitarian_analysis": "U",
            "virtue_ethics_analysis": "V", "risk_flags": ["bias"],
            "confidence_score": 0.9, "recommendation": "Go ahead",
        }
        text = f"Some preamble\n{json.dumps(data)}\nSome suffix"
        result = _parse_response(text)
        assert result["kantian_analysis"] == "K"
        assert result["confidence_score"] == 0.9

    def test_invalid_json_returns_fallback(self):
        result = _parse_response("this is not json at all")
        assert result["kantian_analysis"] != ""
        assert result["confidence_score"] == 0.5

    def test_empty_string_returns_fallback(self):
        result = _parse_response("")
        assert isinstance(result, dict)
        assert result["confidence_score"] == 0.5

    def test_markdown_wrapped_json_extracted(self):
        data = {"kantian_analysis": "K", "utilitarian_analysis": "U",
                "virtue_ethics_analysis": "V", "risk_flags": [],
                "confidence_score": 0.7, "recommendation": "OK"}
        text = f"```json\n{json.dumps(data)}\n```"
        result = _parse_response(text)
        assert result["kantian_analysis"] == "K"


class TestNormalize:
    def _base(self, **overrides):
        base = {
            "kantian_analysis": "K", "utilitarian_analysis": "U",
            "virtue_ethics_analysis": "V", "risk_flags": ["bias"],
            "confidence_score": 0.8, "recommendation": "R",
        }
        base.update(overrides)
        return base

    def test_flat_structure_passed_through(self):
        result = _normalize(self._base())
        assert result["kantian_analysis"] == "K"
        assert result["utilitarian_analysis"] == "U"

    def test_nested_framework_analyses_extracted(self):
        data = {
            "framework_analyses": {
                "kantian_ethics": {"analysis": "Nested K"},
                "utilitarianism": {"analysis": "Nested U"},
                "virtue_ethics": {"analysis": "Nested V"},
            },
            "risk_flags": [],
            "confidence_score": 0.5,
            "recommendation": "R",
        }
        result = _normalize(data)
        assert result["kantian_analysis"] == "Nested K"
        assert result["utilitarian_analysis"] == "Nested U"
        assert result["virtue_ethics_analysis"] == "Nested V"

    def test_risk_flags_dict_becomes_list(self):
        result = _normalize(self._base(risk_flags={"bias": True, "fairness": True}))
        assert isinstance(result["risk_flags"], list)
        assert "bias" in result["risk_flags"]

    def test_risk_flags_list_stays_list(self):
        result = _normalize(self._base(risk_flags=["bias", "fairness"]))
        assert result["risk_flags"] == ["bias", "fairness"]

    def test_risk_flags_invalid_becomes_empty(self):
        result = _normalize(self._base(risk_flags=None))
        assert result["risk_flags"] == []

    def test_confidence_clamped_high(self):
        result = _normalize(self._base(confidence_score=5.0))
        assert result["confidence_score"] == 1.0

    def test_confidence_clamped_low(self):
        result = _normalize(self._base(confidence_score=-1.0))
        assert result["confidence_score"] == 0.0

    def test_confidence_invalid_type_defaults_to_half(self):
        result = _normalize(self._base(confidence_score="bad"))
        assert result["confidence_score"] == 0.5

    def test_recommendation_dict_merged_to_string(self):
        rec = {"action": "Do X", "mitigation_steps": ["Step 1", "Step 2"]}
        result = _normalize(self._base(recommendation=rec))
        assert "Do X" in result["recommendation"]
        assert "Step 1" in result["recommendation"]

    def test_nested_confidence_extracted(self):
        data = {
            "kantian_analysis": "K", "utilitarian_analysis": "U",
            "virtue_ethics_analysis": "V", "risk_flags": [],
            "overall_assessment": {"confidence_score": 0.77},
            "recommendation": "R",
        }
        result = _normalize(data)
        assert result["confidence_score"] == pytest.approx(0.77)


class TestBuildUserPrompt:
    def test_contains_decision(self):
        prompt = _build_user_prompt("Reject candidate", {"gender": "female"})
        assert "Reject candidate" in prompt

    def test_contains_context_json(self):
        prompt = _build_user_prompt("Hire", {"role": "engineer"})
        assert "engineer" in prompt


# ── LLMOrchestrator tests ─────────────────────────────────────────────────────

def _make_orchestrator(claude=None, openai=None):
    """Create an orchestrator with injected mock clients."""
    orch = LLMOrchestrator.__new__(LLMOrchestrator)
    orch._claude = claude
    orch._openai = openai
    orch._claude_model = "claude-opus-4-6"
    orch._openai_model = "gpt-4o-mini"
    orch._max_tokens = 1000
    return orch


def _valid_llm_result():
    return {
        "kantian_analysis": "K", "utilitarian_analysis": "U",
        "virtue_ethics_analysis": "V", "risk_flags": ["bias"],
        "confidence_score": 0.85, "recommendation": "Proceed carefully",
    }


class TestOrchestratorEvaluate:
    def test_claude_success(self):
        orch = _make_orchestrator(claude=MagicMock())
        with patch.object(orch, "_call_claude", return_value=_valid_llm_result()):
            result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "claude"
        assert result["kantian_analysis"] == "K"

    def test_claude_rate_limit_falls_back_to_openai(self):
        orch = _make_orchestrator(claude=MagicMock(), openai=MagicMock())
        with patch.object(orch, "_call_claude", side_effect=anthropic.RateLimitError.__new__(anthropic.RateLimitError)):
            with patch.object(orch, "_call_openai", return_value=_valid_llm_result()):
                result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "openai"

    def test_claude_internal_error_falls_back_to_openai(self):
        orch = _make_orchestrator(claude=MagicMock(), openai=MagicMock())
        err = anthropic.InternalServerError.__new__(anthropic.InternalServerError)
        with patch.object(orch, "_call_claude", side_effect=err):
            with patch.object(orch, "_call_openai", return_value=_valid_llm_result()):
                result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "openai"

    def test_claude_auth_error_falls_back_to_openai(self):
        orch = _make_orchestrator(claude=MagicMock(), openai=MagicMock())
        err = anthropic.AuthenticationError.__new__(anthropic.AuthenticationError)
        with patch.object(orch, "_call_claude", side_effect=err):
            with patch.object(orch, "_call_openai", return_value=_valid_llm_result()):
                result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "openai"

    def test_both_fail_returns_mock(self):
        orch = _make_orchestrator(claude=MagicMock(), openai=MagicMock())
        err_c = anthropic.RateLimitError.__new__(anthropic.RateLimitError)
        err_o = Exception("openai down")
        with patch.object(orch, "_call_claude", side_effect=err_c):
            with patch.object(orch, "_call_openai", side_effect=err_o):
                result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "mock"
        assert result["confidence_score"] == 0.0

    def test_no_clients_returns_mock(self):
        orch = _make_orchestrator(claude=None, openai=None)
        result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "mock"

    def test_openai_rate_limit_returns_mock(self):
        orch = _make_orchestrator(claude=None, openai=MagicMock())
        # Build a minimal OpenAI RateLimitError
        response_mock = MagicMock()
        response_mock.status_code = 429
        err = OpenAIRateLimitError("rate limited", response=response_mock, body={})
        with patch.object(orch, "_call_openai", side_effect=err):
            result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "mock"

    def test_mock_response_structure(self):
        result = LLMOrchestrator._mock_response()
        for key in ("kantian_analysis", "utilitarian_analysis", "virtue_ethics_analysis",
                    "risk_flags", "confidence_score", "recommendation", "provider"):
            assert key in result
        assert result["provider"] == "mock"

    def test_claude_not_configured_skips_to_openai(self):
        orch = _make_orchestrator(claude=None, openai=MagicMock())
        with patch.object(orch, "_call_openai", return_value=_valid_llm_result()):
            result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "openai"


class TestCallClaude:
    def _make_stream(self, text):
        block = MagicMock()
        block.type = "text"
        block.text = text
        response = MagicMock()
        response.content = [block]
        stream_ctx = MagicMock()
        stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.get_final_message = MagicMock(return_value=response)
        return stream_ctx

    def test_extracts_text_from_response(self):
        data = {"kantian_analysis": "K", "utilitarian_analysis": "U",
                "virtue_ethics_analysis": "V", "risk_flags": [],
                "confidence_score": 0.9, "recommendation": "R"}
        import json
        stream = self._make_stream(json.dumps(data))
        orch = _make_orchestrator(claude=MagicMock())
        orch._claude.messages.stream = MagicMock(return_value=stream)
        result = orch._call_claude("test prompt")
        assert result["kantian_analysis"] == "K"

    def test_empty_content_returns_fallback(self):
        response = MagicMock()
        response.content = []  # no text blocks
        stream_ctx = MagicMock()
        stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.get_final_message = MagicMock(return_value=response)
        orch = _make_orchestrator(claude=MagicMock())
        orch._claude.messages.stream = MagicMock(return_value=stream_ctx)
        result = orch._call_claude("test prompt")
        assert isinstance(result, dict)
        assert "confidence_score" in result


class TestCallOpenAI:
    def _make_openai_response(self, text):
        choice = MagicMock()
        choice.message.content = text
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_extracts_text_from_response(self):
        import json
        data = {"kantian_analysis": "OK", "utilitarian_analysis": "U",
                "virtue_ethics_analysis": "V", "risk_flags": ["fairness"],
                "confidence_score": 0.7, "recommendation": "R"}
        orch = _make_orchestrator(openai=MagicMock())
        orch._openai.chat.completions.create = MagicMock(
            return_value=self._make_openai_response(json.dumps(data))
        )
        result = orch._call_openai("test prompt")
        assert result["kantian_analysis"] == "OK"

    def test_none_content_returns_fallback(self):
        orch = _make_orchestrator(openai=MagicMock())
        orch._openai.chat.completions.create = MagicMock(
            return_value=self._make_openai_response(None)
        )
        result = orch._call_openai("test prompt")
        assert isinstance(result, dict)


import httpx as _httpx

def _make_bad_request(msg: str) -> anthropic.BadRequestError:
    req = _httpx.Request("GET", "http://test")
    resp = _httpx.Response(400, request=req)
    return anthropic.BadRequestError(msg, response=resp, body=None)


class TestBadRequestCreditFallback:
    def test_credit_exhausted_falls_back_to_openai(self):
        orch = _make_orchestrator(claude=MagicMock(), openai=MagicMock())
        err = _make_bad_request("credit balance is too low")
        with patch.object(orch, "_call_claude", side_effect=err):
            with patch.object(orch, "_call_openai", return_value=_valid_llm_result()):
                result = orch.evaluate("decision", {"x": 1})
        assert result["provider"] == "openai"

    def test_bad_request_non_credit_reraises(self):
        orch = _make_orchestrator(claude=MagicMock(), openai=MagicMock())
        err = _make_bad_request("some other error message")
        with patch.object(orch, "_call_claude", side_effect=err):
            with pytest.raises(anthropic.BadRequestError):
                orch.evaluate("decision", {"x": 1})
