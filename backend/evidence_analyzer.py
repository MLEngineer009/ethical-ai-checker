"""
AI-powered evidence analysis for EU AI Act compliance.

Two capabilities:
  1. Document extraction — parse an uploaded file and extract compliance evidence
  2. Interview scoring   — evaluate structured Q&A answers per article

Both use Claude via the Anthropic SDK and return a standardised EvidenceResult.
"""

import io
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_DOC_CHARS = 12_000  # ~3 k tokens — enough for most compliance documents


# ── Internal helpers ──────────────────────────────────────────────────────────

def _client():
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=key)


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages)
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}") from e


def _extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _extract_pdf_text(data)
    if name.endswith((".txt", ".md", ".csv")):
        return data.decode("utf-8", errors="replace")
    raise ValueError(
        f"Unsupported file type '{filename}'. Supported: .pdf, .txt, .md, .csv"
    )


def _parse_json_response(text: str) -> Dict:
    """Extract JSON from Claude response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


def _call_claude(prompt: str) -> Dict:
    client = _client()
    resp = client.messages.create(
        model=_MODEL,
        max_tokens=600,
        system=(
            "You are a senior EU AI Act compliance expert. "
            "You respond only with valid JSON — no prose, no markdown fences."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json_response(resp.content[0].text)


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_document(
    article_key: str,
    article_title: str,
    article_requirement: str,
    filename: str,
    file_data: bytes,
) -> Dict[str, Any]:
    """
    Extract compliance evidence from an uploaded document.

    Returns:
      {
        "notes":       str   — 1-2 sentence summary suitable for the evidence field,
        "date":        str   — YYYY-MM-DD or "",
        "verdict":     str   — "pass" | "partial" | "insufficient",
        "explanation": str   — 2-3 sentences explaining the verdict,
        "confidence":  float — 0.0–1.0,
      }
    """
    try:
        raw_text = _extract_text(filename, file_data)
    except ValueError as e:
        return {
            "notes": "",
            "date": "",
            "verdict": "insufficient",
            "explanation": str(e),
            "confidence": 0.0,
        }

    doc_excerpt = raw_text[:_MAX_DOC_CHARS]
    if len(raw_text) > _MAX_DOC_CHARS:
        doc_excerpt += "\n\n[Document truncated — first 12 000 characters shown]"

    prompt = f"""Analyse this document submitted as evidence for EU AI Act compliance.

Article: {article_key.upper()} — {article_title}
Legal requirement: {article_requirement}

Document (filename: {filename}):
<document>
{doc_excerpt}
</document>

Return a JSON object with exactly these fields:
{{
  "notes":       "1-2 sentence summary of what the document proves, suitable for an evidence notes field",
  "date":        "most relevant date found in the document in YYYY-MM-DD format, or empty string",
  "verdict":     "pass" | "partial" | "insufficient",
  "explanation": "2-3 sentences explaining your verdict and what specifically satisfies or falls short of the requirement",
  "confidence":  0.0 to 1.0
}}

Verdict guidance:
- "pass"         — document clearly and specifically satisfies the article requirement
- "partial"      — document addresses the requirement but has gaps (missing detail, outdated, incomplete)
- "insufficient" — document does not address this requirement or is unrelated"""

    try:
        result = _call_claude(prompt)
        result.setdefault("confidence", 0.7)
        logger.info(
            "Document analysis — article=%s file=%s verdict=%s confidence=%.2f",
            article_key, filename, result.get("verdict"), result.get("confidence"),
        )
        return result
    except Exception as e:
        logger.exception("Document analysis failed — article=%s file=%s", article_key, filename)
        return {
            "notes": "",
            "date": "",
            "verdict": "insufficient",
            "explanation": f"Analysis failed: {e}",
            "confidence": 0.0,
        }


def score_interview(
    article_key: str,
    article_title: str,
    article_requirement: str,
    questions_and_answers: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Score structured interview answers for an article.

    `questions_and_answers` is a list of {question, answer} dicts.

    Returns:
      {
        "notes":    str        — 1-2 sentence evidence summary,
        "verdict":  str        — "pass" | "partial" | "fail",
        "feedback": str        — specific feedback on strengths and gaps,
        "missing":  List[str]  — list of things that need to be addressed,
      }
    """
    qa_lines = "\n".join(
        f"Q: {qa['question']}\nA: {qa['answer'].strip() or '(no answer provided)'}"
        for qa in questions_and_answers
    )

    prompt = f"""Evaluate these interview answers for EU AI Act compliance.

Article: {article_key.upper()} — {article_title}
Legal requirement: {article_requirement}

Interview responses:
{qa_lines}

Return a JSON object with exactly these fields:
{{
  "notes":    "1-2 sentence summary of the evidence the answers provide, suitable for an evidence notes field",
  "verdict":  "pass" | "partial" | "fail",
  "feedback": "2-3 sentences of specific feedback — what is strong and what is missing",
  "missing":  ["specific thing 1 that needs to be addressed", "specific thing 2", ...]
}}

Verdict guidance:
- "pass"    — answers demonstrate clear, documented, evidenced compliance
- "partial" — answers show intent and partial compliance but lack specifics, dates, or documentation
- "fail"    — answers reveal significant gaps or the activity has not been carried out

If any answer is empty or clearly evasive, weight that heavily toward "partial" or "fail".
Keep "missing" list empty if verdict is "pass"."""

    try:
        result = _call_claude(prompt)
        result.setdefault("missing", [])
        logger.info(
            "Interview scored — article=%s verdict=%s",
            article_key, result.get("verdict"),
        )
        return result
    except Exception as e:
        logger.exception("Interview scoring failed — article=%s", article_key)
        return {
            "notes": "",
            "verdict": "fail",
            "feedback": f"Scoring failed: {e}",
            "missing": ["Analysis could not be completed — please try again"],
        }
