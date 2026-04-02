"""Tests for backend.custom_model — CustomModelClient."""

import json
from unittest.mock import MagicMock, patch

import pytest

import backend.custom_model as cm_module
from backend.custom_model import CustomModelClient, _parse_response


# ── _parse_response ───────────────────────────────────────────────────────────

VALID_JSON = {
    "kantian_analysis": "ok",
    "utilitarian_analysis": "ok",
    "virtue_ethics_analysis": "ok",
    "risk_flags": ["bias", "fairness"],
    "confidence_score": 0.8,
    "recommendation": "proceed",
}


class TestParseResponse:
    def test_valid_json_string(self):
        text = json.dumps(VALID_JSON)
        result = _parse_response(text)
        assert result is not None
        assert result["confidence_score"] == 0.8
        assert result["risk_flags"] == ["bias", "fairness"]

    def test_json_embedded_in_prose(self):
        text = f"Here is the analysis:\n{json.dumps(VALID_JSON)}\nEnd."
        result = _parse_response(text)
        assert result is not None
        assert result["recommendation"] == "proceed"

    def test_missing_required_field_returns_none(self):
        bad = dict(VALID_JSON)
        del bad["recommendation"]
        result = _parse_response(json.dumps(bad))
        assert result is None

    def test_no_json_returns_none(self):
        assert _parse_response("no json here") is None

    def test_invalid_json_returns_none(self):
        assert _parse_response("{not valid json}") is None

    def test_confidence_clamped_high(self):
        data = dict(VALID_JSON, confidence_score=5.0)
        result = _parse_response(json.dumps(data))
        assert result["confidence_score"] == 1.0

    def test_confidence_clamped_low(self):
        data = dict(VALID_JSON, confidence_score=-1.0)
        result = _parse_response(json.dumps(data))
        assert result["confidence_score"] == 0.0

    def test_confidence_bad_type_defaults(self):
        data = dict(VALID_JSON, confidence_score="bad")
        result = _parse_response(json.dumps(data))
        assert result["confidence_score"] == 0.5

    def test_risk_flags_non_list_becomes_empty(self):
        data = dict(VALID_JSON, risk_flags="bias")
        result = _parse_response(json.dumps(data))
        assert result["risk_flags"] == []

    def test_risk_flags_items_cast_to_str(self):
        data = dict(VALID_JSON, risk_flags=[1, 2, "bias"])
        result = _parse_response(json.dumps(data))
        assert result["risk_flags"] == ["1", "2", "bias"]


# ── CustomModelClient ─────────────────────────────────────────────────────────

_NO_MODEL = {"CUSTOM_MODEL_REPO": "", "OLLAMA_MODEL": ""}


class TestCustomModelClientDisabled:
    def test_not_available_when_repo_not_set(self):
        with patch.dict("os.environ", _NO_MODEL, clear=False):
            client = CustomModelClient()
        assert not client.available

    def test_evaluate_returns_none_when_disabled(self):
        with patch.dict("os.environ", _NO_MODEL, clear=False):
            client = CustomModelClient()
        result = client.evaluate("sys", "user")
        assert result is None


class TestCustomModelClientEnabled:
    def _make_mock_client(self, content: str):
        """Build a mock InferenceClient whose chat_completion returns content."""
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_hf_client = MagicMock()
        mock_hf_client.chat_completion.return_value = mock_response
        return mock_hf_client

    _HF_ENV = {"CUSTOM_MODEL_REPO": "user/model", "OLLAMA_MODEL": ""}

    def test_available_when_repo_set(self):
        mock_cls = MagicMock(return_value=MagicMock())
        with patch.dict("os.environ", self._HF_ENV, clear=False):
            with patch.dict("sys.modules", {"huggingface_hub": MagicMock(InferenceClient=mock_cls)}):
                client = CustomModelClient()
        assert client.available

    def test_evaluate_returns_parsed_dict(self):
        mock_cls = MagicMock(return_value=self._make_mock_client(json.dumps(VALID_JSON)))
        with patch.dict("os.environ", self._HF_ENV, clear=False):
            with patch.dict("sys.modules", {"huggingface_hub": MagicMock(InferenceClient=mock_cls)}):
                client = CustomModelClient()
                result = client.evaluate("system prompt", "user prompt")
        assert result is not None
        assert result["kantian_analysis"] == "ok"

    def test_evaluate_returns_none_on_parse_failure(self):
        mock_cls = MagicMock(return_value=self._make_mock_client("not json"))
        with patch.dict("os.environ", self._HF_ENV, clear=False):
            with patch.dict("sys.modules", {"huggingface_hub": MagicMock(InferenceClient=mock_cls)}):
                client = CustomModelClient()
                result = client.evaluate("system prompt", "user prompt")
        assert result is None

    def test_evaluate_returns_none_on_inference_error(self):
        mock_hf_client = MagicMock()
        mock_hf_client.chat_completion.side_effect = RuntimeError("connection refused")
        mock_cls = MagicMock(return_value=mock_hf_client)
        with patch.dict("os.environ", self._HF_ENV, clear=False):
            with patch.dict("sys.modules", {"huggingface_hub": MagicMock(InferenceClient=mock_cls)}):
                client = CustomModelClient()
                result = client.evaluate("system prompt", "user prompt")
        assert result is None

    def test_import_error_disables_client(self):
        """If huggingface_hub is not installed, client silently disables."""
        import sys
        orig = sys.modules.get("huggingface_hub")
        sys.modules["huggingface_hub"] = None  # type: ignore
        try:
            with patch.dict("os.environ", self._HF_ENV, clear=False):
                client = CustomModelClient()
            assert not client.available
        finally:
            if orig is None:
                sys.modules.pop("huggingface_hub", None)
            else:
                sys.modules["huggingface_hub"] = orig
