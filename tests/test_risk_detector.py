"""Unit tests for risk_detector.py — no external dependencies."""

import pytest
from backend.risk_detector import (
    detect_bias_risks,
    detect_fairness_risks,
    detect_transparency_risks,
    detect_discrimination_risks,
    detect_all_risks,
)


class TestDetectBiasRisks:
    def test_gender_triggers_bias(self):
        assert "bias" in detect_bias_risks({"gender": "female"})

    def test_race_triggers_bias(self):
        assert "bias" in detect_bias_risks({"race": "asian"})

    def test_age_triggers_bias(self):
        assert "bias" in detect_bias_risks({"age": 35})

    def test_zip_code_triggers_bias(self):
        assert "bias" in detect_bias_risks({"zip_code": "90210"})

    def test_religion_triggers_bias(self):
        assert "bias" in detect_bias_risks({"religion": "muslim"})

    def test_disability_triggers_bias(self):
        assert "bias" in detect_bias_risks({"disability": "yes"})

    def test_neutral_context_no_bias(self):
        assert detect_bias_risks({"experience": 5, "education": "bachelors"}) == []

    def test_empty_context_no_bias(self):
        assert detect_bias_risks({}) == []

    def test_bias_flagged_once_even_with_multiple_attributes(self):
        flags = detect_bias_risks({"gender": "female", "race": "asian"})
        assert flags.count("bias") == 1

    def test_case_insensitive_detection(self):
        # Attribute values are lowercased via str(context)
        assert "bias" in detect_bias_risks({"Gender": "Female"})


class TestDetectFairnessRisks:
    def test_reject_keyword_triggers_fairness(self):
        assert "fairness" in detect_fairness_risks("Reject the application", {})

    def test_exclude_keyword_triggers_fairness(self):
        assert "fairness" in detect_fairness_risks("Exclude this candidate", {})

    def test_ban_keyword_triggers_fairness(self):
        assert "fairness" in detect_fairness_risks("Ban them from competing", {})

    def test_group_language_all_triggers_fairness(self):
        assert "fairness" in detect_fairness_risks("all candidates must pass", {})

    def test_group_language_every_triggers_fairness(self):
        assert "fairness" in detect_fairness_risks("every employee should", {})

    def test_neutral_decision_no_fairness(self):
        assert detect_fairness_risks("Approve the application based on merit", {}) == []

    def test_empty_decision_no_fairness(self):
        assert detect_fairness_risks("", {}) == []


class TestDetectTransparencyRisks:
    def test_assume_triggers_transparency(self):
        assert "transparency" in detect_transparency_risks("assume they are qualified", {})

    def test_probably_triggers_transparency(self):
        assert "transparency" in detect_transparency_risks("probably the right choice", {})

    def test_sparse_context_triggers_transparency(self):
        assert "transparency" in detect_transparency_risks("promote", {"role": "manager"})

    def test_sufficient_context_no_transparency(self):
        result = detect_transparency_risks(
            "Promote based on performance",
            {"role": "engineer", "years": 3, "rating": "excellent"},
        )
        assert "transparency" not in result

    def test_empty_decision_sparse_context(self):
        assert "transparency" in detect_transparency_risks("", {"x": 1})

    def test_vague_keyword_triggers(self):
        assert "transparency" in detect_transparency_risks("unclear reasoning here", {})


class TestDetectDiscriminationRisks:
    def test_based_on_gender_pattern(self):
        assert "discrimination" in detect_discrimination_risks(
            "Reject based on gender", {}
        )

    def test_based_on_race_pattern(self):
        assert "discrimination" in detect_discrimination_risks(
            "Decision based on race", {}
        )

    def test_age_based_pattern(self):
        assert "discrimination" in detect_discrimination_risks(
            "Not suitable based on age", {}
        )

    def test_neutral_decision_no_discrimination(self):
        assert detect_discrimination_risks("Promote based on performance review", {}) == []

    def test_empty_decision_no_discrimination(self):
        assert detect_discrimination_risks("", {}) == []


class TestDetectAllRisks:
    def test_returns_sorted_unique_flags(self):
        flags = detect_all_risks("Reject based on gender", {"gender": "female"})
        assert flags == sorted(set(flags))

    def test_no_duplicates(self):
        flags = detect_all_risks("Reject", {"gender": "female"})
        assert len(flags) == len(set(flags))

    def test_all_flags_can_trigger(self):
        flags = detect_all_risks(
            "assume and exclude based on gender",
            {"gender": "female"},
        )
        assert "bias" in flags
        assert "fairness" in flags
        assert "transparency" in flags

    def test_clean_decision_minimal_flags(self):
        flags = detect_all_risks(
            "Approve promotion based on three-year performance record",
            {"years": 3, "rating": "excellent", "role": "senior"},
        )
        # No bias sensitive attributes, no harm keywords
        assert "bias" not in flags

    def test_returns_list(self):
        assert isinstance(detect_all_risks("test", {}), list)
