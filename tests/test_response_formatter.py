"""Unit tests for backend/response_formatter.py."""

import pytest
from backend.response_formatter import validate_response_schema, format_response


VALID = {
    "kantian_analysis": "Analysis text",
    "utilitarian_analysis": "Util text",
    "virtue_ethics_analysis": "Virtue text",
    "risk_flags": ["bias"],
    "confidence_score": 0.8,
    "recommendation": "Do this",
}


class TestValidateResponseSchema:
    def test_valid_response_passes(self):
        assert validate_response_schema(VALID) is True

    def test_zero_confidence_is_valid(self):
        data = {**VALID, "confidence_score": 0.0}
        assert validate_response_schema(data) is True

    def test_one_confidence_is_valid(self):
        data = {**VALID, "confidence_score": 1.0}
        assert validate_response_schema(data) is True

    def test_empty_risk_flags_is_valid(self):
        assert validate_response_schema({**VALID, "risk_flags": []}) is True

    def test_missing_kantian_fails(self):
        data = {k: v for k, v in VALID.items() if k != "kantian_analysis"}
        assert validate_response_schema(data) is False

    def test_missing_utilitarian_fails(self):
        data = {k: v for k, v in VALID.items() if k != "utilitarian_analysis"}
        assert validate_response_schema(data) is False

    def test_missing_virtue_fails(self):
        data = {k: v for k, v in VALID.items() if k != "virtue_ethics_analysis"}
        assert validate_response_schema(data) is False

    def test_missing_risk_flags_fails(self):
        data = {k: v for k, v in VALID.items() if k != "risk_flags"}
        assert validate_response_schema(data) is False

    def test_missing_confidence_fails(self):
        data = {k: v for k, v in VALID.items() if k != "confidence_score"}
        assert validate_response_schema(data) is False

    def test_missing_recommendation_fails(self):
        data = {k: v for k, v in VALID.items() if k != "recommendation"}
        assert validate_response_schema(data) is False

    def test_wrong_type_kantian_fails(self):
        assert validate_response_schema({**VALID, "kantian_analysis": 123}) is False

    def test_wrong_type_risk_flags_fails(self):
        assert validate_response_schema({**VALID, "risk_flags": "bias"}) is False

    def test_confidence_above_1_fails(self):
        assert validate_response_schema({**VALID, "confidence_score": 1.1}) is False

    def test_confidence_below_0_fails(self):
        assert validate_response_schema({**VALID, "confidence_score": -0.1}) is False

    def test_integer_confidence_is_valid(self):
        assert validate_response_schema({**VALID, "confidence_score": 1}) is True


class TestFormatResponse:
    def test_valid_input_passes_through(self):
        result = format_response(VALID)
        assert result["kantian_analysis"] == VALID["kantian_analysis"]
        assert result["confidence_score"] == VALID["confidence_score"]
        assert result["risk_flags"] == VALID["risk_flags"]

    def test_missing_fields_use_defaults(self):
        result = format_response({})
        assert result["kantian_analysis"] == ""
        assert result["utilitarian_analysis"] == ""
        assert result["virtue_ethics_analysis"] == ""
        assert result["risk_flags"] == []
        assert result["confidence_score"] == 0.5
        assert result["recommendation"] == ""

    def test_confidence_clamped_above_1(self):
        result = format_response({**VALID, "confidence_score": 5.0})
        assert result["confidence_score"] == 1.0

    def test_confidence_clamped_below_0(self):
        result = format_response({**VALID, "confidence_score": -2.0})
        assert result["confidence_score"] == 0.0

    def test_risk_flags_non_list_becomes_empty(self):
        result = format_response({**VALID, "risk_flags": "bias"})
        assert result["risk_flags"] == []

    def test_risk_flags_items_converted_to_str(self):
        result = format_response({**VALID, "risk_flags": [1, 2, "bias"]})
        assert result["risk_flags"] == ["1", "2", "bias"]

    def test_non_string_analysis_converted(self):
        result = format_response({**VALID, "kantian_analysis": 42})
        assert result["kantian_analysis"] == "42"

    def test_extra_keys_preserved_in_output(self):
        data = {**VALID, "provider": "claude"}
        result = format_response(data)
        # format_response only returns the 6 keys
        assert "kantian_analysis" in result
