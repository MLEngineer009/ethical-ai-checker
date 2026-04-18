"""Unit tests for backend/regulations.py — regulatory reference mapping."""

import pytest
from backend.regulations import get_regulatory_refs


class TestGetRegulatoryRefs:
    def test_returns_list(self):
        result = get_regulatory_refs(["bias"], "hiring")
        assert isinstance(result, list)

    def test_empty_flags_returns_empty(self):
        result = get_regulatory_refs([], "hiring")
        assert result == []

    def test_unknown_flag_returns_empty(self):
        result = get_regulatory_refs(["nonexistent_flag"], "hiring")
        assert result == []

    def test_each_ref_has_required_fields(self):
        refs = get_regulatory_refs(["bias"], "hiring")
        assert len(refs) > 0
        for ref in refs:
            assert "law" in ref
            assert "jurisdiction" in ref
            assert "description" in ref
            assert "url" in ref
            assert "triggered_by" in ref

    def test_triggered_by_matches_flag(self):
        refs = get_regulatory_refs(["discrimination"], "hiring")
        for ref in refs:
            assert ref["triggered_by"] == "discrimination"

    def test_hiring_bias_includes_eeoc(self):
        refs = get_regulatory_refs(["bias"], "hiring")
        laws = [r["law"] for r in refs]
        assert any("EEOC" in law or "Title VII" in law for law in laws)

    def test_hiring_bias_includes_eu_ai_act(self):
        refs = get_regulatory_refs(["bias"], "hiring")
        laws = [r["law"] for r in refs]
        assert any("EU AI Act" in law for law in laws)

    def test_finance_bias_includes_ecoa(self):
        refs = get_regulatory_refs(["bias"], "finance")
        laws = [r["law"] for r in refs]
        assert any("ECOA" in law for law in laws)

    def test_healthcare_transparency_includes_hipaa(self):
        refs = get_regulatory_refs(["transparency"], "healthcare")
        laws = [r["law"] for r in refs]
        assert any("HIPAA" in law for law in laws)

    def test_no_duplicate_laws_for_single_flag(self):
        refs = get_regulatory_refs(["bias"], "hiring")
        law_names = [r["law"] for r in refs]
        assert len(law_names) == len(set(law_names))

    def test_no_duplicate_laws_for_multiple_flags(self):
        # bias and discrimination share some laws — should still be deduplicated
        refs = get_regulatory_refs(["bias", "discrimination"], "hiring")
        law_names = [r["law"] for r in refs]
        assert len(law_names) == len(set(law_names))

    def test_multiple_flags_returns_more_refs(self):
        single = get_regulatory_refs(["bias"], "hiring")
        multi = get_regulatory_refs(["bias", "transparency"], "hiring")
        assert len(multi) >= len(single)

    def test_unknown_category_falls_back_to_other(self):
        refs_unknown = get_regulatory_refs(["bias"], "nonexistent_category")
        refs_other = get_regulatory_refs(["bias"], "other")
        # Both should return same results (fallback to "other")
        assert {r["law"] for r in refs_unknown} == {r["law"] for r in refs_other}

    def test_all_categories_return_refs_for_bias(self):
        categories = ["hiring", "workplace", "finance", "healthcare", "policy", "personal", "other"]
        for cat in categories:
            refs = get_regulatory_refs(["bias"], cat)
            # personal/other may have fewer but should still return something
            assert isinstance(refs, list)

    def test_personal_category_includes_gdpr(self):
        refs = get_regulatory_refs(["bias"], "personal")
        laws = [r["law"] for r in refs]
        assert any("GDPR" in law for law in laws)

    def test_policy_transparency_includes_eo14110(self):
        refs = get_regulatory_refs(["transparency"], "policy")
        laws = [r["law"] for r in refs]
        assert any("14110" in law or "Executive Order" in law for law in laws)

    def test_url_is_non_empty_string(self):
        refs = get_regulatory_refs(["bias"], "hiring")
        for ref in refs:
            assert isinstance(ref["url"], str)
            assert ref["url"].startswith("http")

    def test_jurisdiction_values_are_known(self):
        all_flags = ["bias", "discrimination", "fairness", "transparency", "harm"]
        refs = get_regulatory_refs(all_flags, "hiring")
        valid_jurisdictions = {"US", "EU", "US (California)"}
        for ref in refs:
            assert ref["jurisdiction"] in valid_jurisdictions

    def test_harm_flag_hiring_returns_refs(self):
        refs = get_regulatory_refs(["harm"], "hiring")
        assert len(refs) > 0

    def test_fairness_flag_finance_returns_refs(self):
        refs = get_regulatory_refs(["fairness"], "finance")
        assert len(refs) > 0

    def test_personal_fairness_returns_empty(self):
        # personal category has no fairness refs defined
        refs = get_regulatory_refs(["fairness"], "personal")
        assert refs == []
