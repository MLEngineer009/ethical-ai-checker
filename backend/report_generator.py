"""PDF report generator for ethical decision analysis."""

import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand colours
PURPLE = colors.HexColor("#764ba2")
BLUE = colors.HexColor("#667eea")
RED = colors.HexColor("#cc3333")
RED_BG = colors.HexColor("#ffeeee")
LIGHT_GRAY = colors.HexColor("#f9f9f9")
DARK_GRAY = colors.HexColor("#333333")
MID_GRAY = colors.HexColor("#666666")

RISK_SEVERITY_COLOR = {
    "bias": colors.HexColor("#e74c3c"),
    "discrimination": colors.HexColor("#c0392b"),
    "fairness": colors.HexColor("#e67e22"),
    "transparency": colors.HexColor("#f39c12"),
    "harm": colors.HexColor("#8e44ad"),
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            fontSize=22,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=11,
            textColor=colors.HexColor("#ddddff"),
            alignment=TA_CENTER,
            fontName="Helvetica",
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontSize=13,
            textColor=PURPLE,
            fontName="Helvetica-Bold",
            spaceBefore=14,
            spaceAfter=6,
            borderPad=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10,
            textColor=DARK_GRAY,
            fontName="Helvetica",
            leading=15,
            spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "label",
            fontSize=9,
            textColor=MID_GRAY,
            fontName="Helvetica-Bold",
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "meta",
            fontSize=9,
            textColor=MID_GRAY,
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "recommendation": ParagraphStyle(
            "recommendation",
            fontSize=10,
            textColor=DARK_GRAY,
            fontName="Helvetica",
            leading=15,
            leftIndent=10,
        ),
    }


def generate_pdf(
    decision: str,
    context: Dict[str, Any],
    analysis: Dict[str, Any],
) -> bytes:
    """Generate a PDF report and return it as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
    )

    s = _styles()
    story = []

    # ── Header banner ───────────────────────────────────────────────────────
    header_data = [
        [Paragraph("Ethical AI Decision Report", s["title"])],
        [Paragraph("AI-Powered Ethical Reasoning &amp; Risk Detection", s["subtitle"])],
    ]
    header_table = Table(header_data, colWidths=[7 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PURPLE),
        ("ROWPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 18),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    # ── Report metadata ──────────────────────────────────────────────────────
    provider = analysis.get("provider", "claude").upper()
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(f"Generated: {generated} &nbsp;|&nbsp; Provider: {provider}", s["meta"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 10))

    # ── Decision & Context ──────────────────────────────────────────────────
    story.append(Paragraph("Decision Being Evaluated", s["section_header"]))
    story.append(Paragraph(decision, s["body"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Context Provided", s["section_header"]))
    ctx_rows = [[Paragraph(f"<b>{k}</b>", s["label"]), Paragraph(str(v), s["body"])]
                for k, v in context.items()]
    if ctx_rows:
        ctx_table = Table(ctx_rows, colWidths=[2 * inch, 5 * inch])
        ctx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
            ("ROWPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(ctx_table)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#eeeeee")))

    # ── Ethical Framework Analyses ──────────────────────────────────────────
    frameworks = [
        ("📖  Kantian Ethics", "kantian_analysis",
         "Fairness, universality, and duty-based reasoning."),
        ("⚖️  Utilitarianism", "utilitarian_analysis",
         "Maximising overall benefit and minimising harm."),
        ("🎯  Virtue Ethics", "virtue_ethics_analysis",
         "Character, integrity, and moral excellence."),
    ]

    story.append(Paragraph("Ethical Framework Analysis", s["section_header"]))
    story.append(Spacer(1, 4))

    for title, key, tagline in frameworks:
        text = analysis.get(key, "No analysis available.")
        framework_data = [
            [Paragraph(f"<b>{title}</b>", s["section_header"]),
             Paragraph(f"<i>{tagline}</i>", s["label"])],
            [Paragraph(text, s["body"]), ""],
        ]
        fw_table = Table(framework_data, colWidths=[3.5 * inch, 3.5 * inch])
        fw_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0eef8")),
            ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GRAY),
            ("SPAN", (0, 1), (1, 1)),
            ("ROWPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTBORDERPADDING", (0, 0), (-1, -1), 4),
            ("LINEAFTER", (0, 0), (0, 0), 1, BLUE),
        ]))
        story.append(fw_table)
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#eeeeee")))
    story.append(Spacer(1, 6))

    # ── Risk Flags ──────────────────────────────────────────────────────────
    story.append(Paragraph("⚠️  Risk Detection", s["section_header"]))
    risk_flags: List[str] = analysis.get("risk_flags", [])
    if risk_flags:
        flag_cells = []
        row = []
        for i, flag in enumerate(risk_flags):
            flag_color = RISK_SEVERITY_COLOR.get(flag.lower(), RED)
            cell = Paragraph(
                f'<font color="{flag_color.hexval()}" size="9"><b>{flag.upper()}</b></font>',
                s["body"],
            )
            row.append(cell)
            if len(row) == 3:
                flag_cells.append(row)
                row = []
        if row:
            while len(row) < 3:
                row.append("")
            flag_cells.append(row)

        flag_table = Table(flag_cells, colWidths=[2.33 * inch] * 3)
        flag_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), RED_BG),
            ("ROWPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ffcccc")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(flag_table)
    else:
        story.append(Paragraph("✅ No significant risks detected.", s["body"]))

    story.append(Spacer(1, 10))

    # ── Confidence Score ────────────────────────────────────────────────────
    story.append(Paragraph("Confidence Score", s["section_header"]))
    score = analysis.get("confidence_score", 0.5)
    pct = int(score * 100)
    bar_width = 6 * inch
    filled = bar_width * score

    bar_data = [[f"{pct}%  confidence in this assessment"]]
    bar_table = Table(bar_data, colWidths=[bar_width])
    bar_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("ROWPADDING", (0, 0), (-1, -1), 10),
        ("COLWIDTH", (0, 0), (0, 0), filled),
    ]))
    story.append(bar_table)
    story.append(Spacer(1, 10))

    # ── Recommendation ──────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#eeeeee")))
    story.append(Spacer(1, 6))
    story.append(Paragraph("💡  Recommendation", s["section_header"]))

    recommendation = analysis.get("recommendation", "No recommendation available.")
    for line in recommendation.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), s["recommendation"]))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 16))

    # ── Footer ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This report was generated by the Ethical AI Decision Checker. "
        "It is intended to assist human decision-making, not replace it. "
        "Always consult qualified legal and ethical professionals for high-stakes decisions.",
        s["meta"],
    ))

    doc.build(story)
    return buffer.getvalue()
