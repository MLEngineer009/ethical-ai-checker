"""
EU AI Act Compliance Readiness Certificate — PDF generator.

Generates a Pragma-issued compliance readiness certificate for a registered
AI system. This is a compliance *readiness* report, not a legal certification
by a notified body. It documents that the system meets Pragma's implementation
of EU AI Act Articles 9–14 as of the issue date.
"""

import io
from datetime import datetime, timezone
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# Brand colours
PURPLE     = colors.HexColor("#764ba2")
PURPLE_MID = colors.HexColor("#9b59b6")
BLUE       = colors.HexColor("#667eea")
GREEN      = colors.HexColor("#27ae60")
AMBER      = colors.HexColor("#f39c12")
RED        = colors.HexColor("#e74c3c")
DARK       = colors.HexColor("#1a1a2e")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
MID_GRAY   = colors.HexColor("#666666")
DARK_GRAY  = colors.HexColor("#333333")

STATUS_COLOR = {"pass": GREEN, "partial": AMBER, "fail": RED}
STATUS_ICON  = {"pass": "✓  PASS", "partial": "~  PARTIAL", "fail": "✗  FAIL"}


def _styles():
    return {
        "cert_title": ParagraphStyle(
            "cert_title", fontSize=26, textColor=colors.white,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4,
        ),
        "cert_sub": ParagraphStyle(
            "cert_sub", fontSize=11, textColor=colors.HexColor("#ddddff"),
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "section_header": ParagraphStyle(
            "section_header", fontSize=12, textColor=PURPLE,
            fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", fontSize=10, textColor=DARK_GRAY,
            fontName="Helvetica", leading=15, spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "label", fontSize=9, textColor=MID_GRAY,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "meta", fontSize=9, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "verdict": ParagraphStyle(
            "verdict", fontSize=18, textColor=colors.white,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "cert_id": ParagraphStyle(
            "cert_id", fontSize=9, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=2,
        ),
        "article_title": ParagraphStyle(
            "article_title", fontSize=10, textColor=DARK_GRAY,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "article_desc": ParagraphStyle(
            "article_desc", fontSize=9, textColor=MID_GRAY,
            fontName="Helvetica", leading=13,
        ),
        "evidence": ParagraphStyle(
            "evidence", fontSize=9, textColor=DARK_GRAY,
            fontName="Helvetica-Oblique", leading=13,
        ),
    }


def _verdict_color(verdict: str) -> colors.Color:
    return {"ready": GREEN, "partial": AMBER, "not_ready": RED}.get(verdict, MID_GRAY)


def generate_certificate(compliance: Dict[str, Any], certificate_id: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.5 * inch, bottomMargin=0.75 * inch,
    )
    s = _styles()
    story = []

    # ── Header banner ────────────────────────────────────────────────────────
    header_data = [
        [Paragraph("Pragma", s["cert_title"])],
        [Paragraph("EU AI Act Compliance Readiness Certificate", s["cert_sub"])],
    ]
    header = Table(header_data, colWidths=[7 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PURPLE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 20),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
        ("ROWPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header)
    story.append(Spacer(1, 10))

    # ── Certificate ID & dates ───────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    issued  = now.strftime("%B %d, %Y")
    valid   = now.replace(year=now.year + 1).strftime("%B %d, %Y")
    story.append(Paragraph(f"Certificate ID: {certificate_id}", s["cert_id"]))
    story.append(Paragraph(f"Issued: {issued}  ·  Valid until: {valid}", s["meta"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 10))

    # ── Verdict banner ───────────────────────────────────────────────────────
    verdict        = compliance.get("verdict", "not_ready")
    verdict_label  = compliance.get("verdict_label", "Not Ready")
    score_pct      = int(compliance.get("overall_score", 0) * 100)
    verdict_color  = _verdict_color(verdict)

    verdict_data = [
        [Paragraph(verdict_label.upper(), s["verdict"])],
        [Paragraph(f"Overall compliance score: {score_pct}%  ·  "
                   f"{compliance.get('passes', 0)} passed  ·  "
                   f"{compliance.get('partials', 0)} partial  ·  "
                   f"{compliance.get('fails', 0)} failed",
                   s["cert_sub"])],
    ]
    verdict_table = Table(verdict_data, colWidths=[7 * inch])
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), verdict_color),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
        ("ROWPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 14))

    # ── System info ──────────────────────────────────────────────────────────
    story.append(Paragraph("AI System Profile", s["section_header"]))
    info_rows = [
        ["Company", compliance.get("company_name", "—")],
        ["AI System", compliance.get("system_name", "—")],
        ["Risk Tier", compliance.get("risk_tier_label", "—")],
        ["Use Case", compliance.get("stats", {}).get("categories", ["—"])[0] if compliance.get("stats", {}).get("categories") else "—"],
        ["Evaluations Logged", str(compliance.get("stats", {}).get("total", 0))],
        ["HITL Overrides", str(compliance.get("stats", {}).get("hitl_overrides", 0))],
        ["Proxy Variables Caught", str(compliance.get("stats", {}).get("proxy_vars_caught", 0))],
    ]
    info_table = Table(
        [[Paragraph(f"<b>{k}</b>", s["label"]), Paragraph(str(v), s["body"])]
         for k, v in info_rows],
        colWidths=[2.2 * inch, 4.8 * inch],
    )
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ROWPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#eeeeee")))

    # ── Per-article checklist ────────────────────────────────────────────────
    story.append(Paragraph("EU AI Act Article-by-Article Assessment", s["section_header"]))

    articles = compliance.get("articles", {})
    for key, article in articles.items():
        status     = article.get("status", "fail")
        sc         = STATUS_COLOR.get(status, MID_GRAY)
        icon       = STATUS_ICON.get(status, "?")
        title      = article.get("title", key)
        desc       = article.get("description", "")
        evidence   = article.get("evidence", "")
        requirement = article.get("requirement", "")

        badge_data = [[Paragraph(f'<font color="white"><b>{icon}</b></font>', s["body"])]]
        badge = Table(badge_data, colWidths=[1.3 * inch])
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), sc),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWPADDING", (0, 0), (-1, -1), 8),
        ]))

        detail_data = [
            [Paragraph(title, s["article_title"])],
            [Paragraph(desc, s["article_desc"])],
            [Paragraph(f"<b>Requirement:</b> {requirement}", s["article_desc"])],
            [Paragraph(f"<i>Evidence: {evidence}</i>", s["evidence"])],
        ]
        detail = Table(detail_data, colWidths=[5.5 * inch])
        detail.setStyle(TableStyle([
            ("ROWPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        row_table = Table([[badge, detail]], colWidths=[1.3 * inch, 5.7 * inch])
        row_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWPADDING", (0, 0), (-1, -1), 0),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("LEFTPADDING", (1, 0), (1, 0), 10),
        ]))
        story.append(row_table)
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 8))

    # ── Disclaimer ───────────────────────────────────────────────────────────
    story.append(Paragraph(
        "This certificate is issued by Pragma and documents compliance readiness against Pragma's implementation "
        "of EU AI Act Articles 9–14. It is not a legal certification by a notified body under the EU AI Act. "
        "High-risk AI systems require formal conformity assessment before deployment in the EU. "
        "This report is valid for one year from the issue date and should be renewed after material system changes.",
        s["meta"],
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Pragma · pragma.ai · Certificate {certificate_id}",
        s["meta"],
    ))

    doc.build(story)
    return buffer.getvalue()
