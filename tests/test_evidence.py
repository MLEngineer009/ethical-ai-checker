"""Tests for evidence_analyzer and interview_engine modules."""

import io
import pytest
from unittest.mock import patch, MagicMock


# ── interview_engine ───────────────────────────────────────────────────────────

class TestInterviewEngine:
    def test_get_article_questions_known(self):
        from backend.interview_engine import get_article_questions
        info = get_article_questions("art_27")
        assert info is not None
        assert "title" in info
        assert "questions" in info
        assert len(info["questions"]) > 0
        assert "27" in info["title"]

    def test_get_article_questions_unknown(self):
        from backend.interview_engine import get_article_questions
        assert get_article_questions("art_99") is None

    def test_list_interviewable_articles(self):
        from backend.interview_engine import list_interviewable_articles
        keys = list_interviewable_articles()
        assert isinstance(keys, list)
        assert len(keys) >= 6
        for k in ["art_4", "art_17", "art_27", "art_33"]:
            assert k in keys

    def test_each_article_has_required_fields(self):
        from backend.interview_engine import INTERVIEW_ARTICLES
        for key, info in INTERVIEW_ARTICLES.items():
            assert "title" in info, f"{key} missing title"
            assert "requirement" in info, f"{key} missing requirement"
            assert "questions" in info, f"{key} missing questions"
            assert len(info["questions"]) >= 2, f"{key} needs at least 2 questions"
            for q in info["questions"]:
                assert "id" in q and "text" in q, f"{key} question missing id or text"

    def test_art_9_questions_cover_risk_topics(self):
        from backend.interview_engine import get_article_questions
        info = get_article_questions("art_9")
        combined = " ".join(q["text"] for q in info["questions"]).lower()
        assert "risk" in combined
        assert "methodology" in combined or "framework" in combined or "responsible" in combined


# ── evidence_analyzer — _extract_text ─────────────────────────────────────────

class TestExtractText:
    def test_txt_file_decoded(self):
        from backend.evidence_analyzer import _extract_text
        data = b"This is a compliance document."
        result = _extract_text("report.txt", data)
        assert "compliance document" in result

    def test_md_file_decoded(self):
        from backend.evidence_analyzer import _extract_text
        data = b"# FRIA Report\nCompleted 2025-03-01"
        result = _extract_text("fria.md", data)
        assert "FRIA Report" in result

    def test_unsupported_extension_raises(self):
        from backend.evidence_analyzer import _extract_text
        with pytest.raises(ValueError, match="Unsupported file type"):
            _extract_text("document.docx", b"some bytes")

    def test_pdf_extraction_called(self):
        from backend.evidence_analyzer import _extract_text
        fake_pdf = b"%PDF-1.4 fake"
        with patch("backend.evidence_analyzer._extract_pdf_text", return_value="PDF text here") as mock:
            result = _extract_text("report.pdf", fake_pdf)
        mock.assert_called_once_with(fake_pdf)
        assert result == "PDF text here"


# ── evidence_analyzer — analyze_document ──────────────────────────────────────

class TestAnalyzeDocument:
    def _mock_result(self):
        return {
            "notes": "The document confirms a FRIA was conducted in Q1 2026.",
            "date": "2026-01-15",
            "verdict": "pass",
            "explanation": "The document clearly evidences a completed FRIA.",
            "confidence": 0.9,
        }

    def test_returns_pass_verdict_on_success(self):
        from backend.evidence_analyzer import analyze_document
        with patch("backend.evidence_analyzer._extract_text", return_value="doc text"), \
             patch("backend.evidence_analyzer._call_claude", return_value=self._mock_result()):
            result = analyze_document(
                article_key="art_27",
                article_title="Article 27 — FRIA",
                article_requirement="FRIA must be conducted before deployment.",
                filename="fria.txt",
                file_data=b"doc text",
            )
        assert result["verdict"] == "pass"
        assert result["date"] == "2026-01-15"
        assert "FRIA" in result["notes"]
        assert result["confidence"] == 0.9

    def test_returns_insufficient_on_extract_error(self):
        from backend.evidence_analyzer import analyze_document
        with patch("backend.evidence_analyzer._extract_text", side_effect=ValueError("bad file")):
            result = analyze_document(
                article_key="art_27",
                article_title="Article 27 — FRIA",
                article_requirement="req",
                filename="bad.docx",
                file_data=b"",
            )
        assert result["verdict"] == "insufficient"
        assert result["confidence"] == 0.0

    def test_returns_insufficient_on_claude_error(self):
        from backend.evidence_analyzer import analyze_document
        with patch("backend.evidence_analyzer._extract_text", return_value="text"), \
             patch("backend.evidence_analyzer._call_claude", side_effect=Exception("API down")):
            result = analyze_document(
                article_key="art_27",
                article_title="Article 27 — FRIA",
                article_requirement="req",
                filename="doc.txt",
                file_data=b"text",
            )
        assert result["verdict"] == "insufficient"
        assert result["notes"] == ""

    def test_confidence_defaults_when_missing(self):
        from backend.evidence_analyzer import analyze_document
        mock_result = self._mock_result()
        del mock_result["confidence"]
        with patch("backend.evidence_analyzer._extract_text", return_value="text"), \
             patch("backend.evidence_analyzer._call_claude", return_value=mock_result):
            result = analyze_document("art_27", "t", "r", "f.txt", b"t")
        assert "confidence" in result
        assert result["confidence"] == 0.7


# ── evidence_analyzer — score_interview ───────────────────────────────────────

class TestScoreInterview:
    def _mock_result(self):
        return {
            "notes": "Staff completed ISO 42001 training in Q1 2026.",
            "verdict": "pass",
            "feedback": "All answers demonstrate clear, evidenced compliance.",
            "missing": [],
        }

    def _sample_answers(self):
        return [
            {"question": "How many staff?", "answer": "12 staff members"},
            {"question": "What training?", "answer": "ISO 42001 course, 8 hours, Q1 2026"},
        ]

    def test_returns_pass_on_good_answers(self):
        from backend.evidence_analyzer import score_interview
        with patch("backend.evidence_analyzer._call_claude", return_value=self._mock_result()):
            result = score_interview(
                article_key="art_4",
                article_title="Article 4 — AI Literacy",
                article_requirement="Staff must be AI literate.",
                questions_and_answers=self._sample_answers(),
            )
        assert result["verdict"] == "pass"
        assert result["missing"] == []
        assert result["notes"] != ""

    def test_returns_fail_on_claude_error(self):
        from backend.evidence_analyzer import score_interview
        with patch("backend.evidence_analyzer._call_claude", side_effect=Exception("timeout")):
            result = score_interview("art_4", "t", "r", self._sample_answers())
        assert result["verdict"] == "fail"
        assert len(result["missing"]) > 0

    def test_missing_defaults_to_empty_list(self):
        from backend.evidence_analyzer import score_interview
        mock_result = self._mock_result()
        del mock_result["missing"]
        with patch("backend.evidence_analyzer._call_claude", return_value=mock_result):
            result = score_interview("art_4", "t", "r", self._sample_answers())
        assert result["missing"] == []

    def test_partial_verdict_has_feedback(self):
        from backend.evidence_analyzer import score_interview
        mock_result = {
            "notes": "Training mentioned but no date or provider given.",
            "verdict": "partial",
            "feedback": "Training was mentioned but lacks specifics.",
            "missing": ["Training provider and date", "Verification mechanism"],
        }
        with patch("backend.evidence_analyzer._call_claude", return_value=mock_result):
            result = score_interview("art_4", "t", "r", self._sample_answers())
        assert result["verdict"] == "partial"
        assert len(result["missing"]) == 2


# ── evidence_analyzer — _parse_json_response ─────────────────────────────────

class TestParseJsonResponse:
    def test_plain_json(self):
        from backend.evidence_analyzer import _parse_json_response
        result = _parse_json_response('{"verdict": "pass", "notes": "ok"}')
        assert result["verdict"] == "pass"

    def test_strips_markdown_fences(self):
        from backend.evidence_analyzer import _parse_json_response
        text = '```json\n{"verdict": "partial"}\n```'
        result = _parse_json_response(text)
        assert result["verdict"] == "partial"

    def test_strips_plain_code_fences(self):
        from backend.evidence_analyzer import _parse_json_response
        text = '```\n{"verdict": "fail"}\n```'
        result = _parse_json_response(text)
        assert result["verdict"] == "fail"
