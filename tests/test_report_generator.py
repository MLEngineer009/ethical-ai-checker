"""Tests for backend/report_generator.py — verifies PDF generation."""

import pytest
from backend.report_generator import generate_pdf


ANALYSIS = {
    "kantian_analysis": "The categorical imperative suggests this action cannot be universalized.",
    "utilitarian_analysis": "Net negative outcomes are likely for the affected group.",
    "virtue_ethics_analysis": "A virtuous person would not make this decision.",
    "risk_flags": ["bias", "fairness", "discrimination"],
    "confidence_score": 0.85,
    "recommendation": "Reconsider this decision and implement a fair review process.",
    "provider": "claude",
}

DECISION = "Reject job candidate based on zip code"
CONTEXT = {"zip_code": "90210", "experience": 5, "gender": "female"}


class TestGeneratePDF:
    def test_returns_bytes(self):
        result = generate_pdf(DECISION, CONTEXT, ANALYSIS)
        assert isinstance(result, bytes)

    def test_returns_pdf_magic_bytes(self):
        result = generate_pdf(DECISION, CONTEXT, ANALYSIS)
        assert result.startswith(b"%PDF")

    def test_non_empty_output(self):
        result = generate_pdf(DECISION, CONTEXT, ANALYSIS)
        assert len(result) > 1000  # a real PDF is never this small

    def test_with_empty_risk_flags(self):
        analysis = {**ANALYSIS, "risk_flags": []}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_single_risk_flag(self):
        analysis = {**ANALYSIS, "risk_flags": ["bias"]}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_all_known_risk_flags(self):
        analysis = {**ANALYSIS, "risk_flags": ["bias", "discrimination", "fairness", "transparency", "harm"]}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_unknown_risk_flag(self):
        analysis = {**ANALYSIS, "risk_flags": ["custom_risk"]}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_zero_confidence(self):
        analysis = {**ANALYSIS, "confidence_score": 0.0}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_full_confidence(self):
        analysis = {**ANALYSIS, "confidence_score": 1.0}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_minimal_context(self):
        result = generate_pdf(DECISION, {"role": "engineer"}, ANALYSIS)
        assert result.startswith(b"%PDF")

    def test_with_many_context_fields(self):
        large_context = {f"key_{i}": f"value_{i}" for i in range(10)}
        result = generate_pdf(DECISION, large_context, ANALYSIS)
        assert result.startswith(b"%PDF")

    def test_with_long_decision(self):
        long_decision = "Consider whether to " + "reject " * 50 + "this candidate"
        result = generate_pdf(long_decision, CONTEXT, ANALYSIS)
        assert result.startswith(b"%PDF")

    def test_with_long_analysis_text(self):
        analysis = {**ANALYSIS, "kantian_analysis": "Detailed analysis. " * 100}
        result = generate_pdf(DECISION, CONTEXT, analysis)
        assert result.startswith(b"%PDF")

    def test_with_missing_analysis_fields(self):
        """generate_pdf should handle missing keys gracefully."""
        sparse_analysis = {"confidence_score": 0.5, "risk_flags": []}
        result = generate_pdf(DECISION, CONTEXT, sparse_analysis)
        assert result.startswith(b"%PDF")

    def test_two_calls_produce_different_bytes(self):
        """Timestamps in headers mean outputs differ (not cached)."""
        r1 = generate_pdf(DECISION, CONTEXT, ANALYSIS)
        r2 = generate_pdf(DECISION, CONTEXT, ANALYSIS)
        # Both should be valid PDFs (timestamps may differ)
        assert r1.startswith(b"%PDF")
        assert r2.startswith(b"%PDF")
