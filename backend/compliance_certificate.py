"""
EU AI Act Compliance Readiness Certificate — PDF generator.

Two-page certificate:
  Page 1 — Formal certificate with Pragma seal, decorative border, verdict
  Page 2 — Detailed article-by-article assessment + system profile

This is a compliance *readiness* report, not a legal certification by a
notified body. It documents that the system meets Pragma's implementation
of EU AI Act Articles 9–14 as of the issue date.
"""

import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.graphics.shapes import (
    Drawing, Circle, String, Line, Rect, Wedge,
)
from reportlab.graphics import renderPDF

# ── Brand palette ──────────────────────────────────────────────────────────────
PURPLE      = colors.HexColor("#764ba2")
PURPLE_DARK = colors.HexColor("#4a2875")
PURPLE_LIGHT= colors.HexColor("#9b6fc8")
BLUE        = colors.HexColor("#667eea")
BLUE_LIGHT  = colors.HexColor("#a0aff8")
GOLD        = colors.HexColor("#c9a227")
GOLD_LIGHT  = colors.HexColor("#e8cc6a")
GREEN       = colors.HexColor("#1a7a4a")
GREEN_LIGHT = colors.HexColor("#d4f0e2")
AMBER       = colors.HexColor("#b45309")
AMBER_LIGHT = colors.HexColor("#fef3c7")
RED         = colors.HexColor("#991b1b")
RED_LIGHT   = colors.HexColor("#fee2e2")
CREAM       = colors.HexColor("#fdfaf4")
OFF_WHITE   = colors.HexColor("#f8f4ef")
BORDER_GOLD = colors.HexColor("#b8960c")
MID_GRAY    = colors.HexColor("#6b7280")
DARK_GRAY   = colors.HexColor("#1f2937")
LIGHT_GRAY  = colors.HexColor("#f3f4f6")

LOGO_PATH = str(Path(__file__).parent.parent / "mobile" / "assets" / "icon.png")

STATUS_COLOR = {
    "pass":    (GREEN,       GREEN_LIGHT,  "✓  PASS"),
    "partial": (AMBER,       AMBER_LIGHT,  "~  PARTIAL"),
    "fail":    (RED,         RED_LIGHT,    "✗  FAIL"),
}

VERDICT_PALETTE = {
    "ready":     (colors.HexColor("#14532d"), colors.HexColor("#bbf7d0"),
                  colors.HexColor("#dcfce7"), "COMPLIANCE READY"),
    "partial":   (colors.HexColor("#78350f"), colors.HexColor("#fde68a"),
                  colors.HexColor("#fef3c7"), "PARTIALLY COMPLIANT"),
    "not_ready": (colors.HexColor("#7f1d1d"), colors.HexColor("#fca5a5"),
                  colors.HexColor("#fee2e2"), "NOT READY"),
}

PAGE_W, PAGE_H = LETTER


# ── Styles ────────────────────────────────────────────────────────────────────

def _s():
    return {
        "org_name": ParagraphStyle(
            "org_name", fontSize=28, textColor=PURPLE_DARK,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            spaceBefore=0, spaceAfter=4, leading=34,
        ),
        "system_name": ParagraphStyle(
            "system_name", fontSize=16, textColor=DARK_GRAY,
            fontName="Helvetica", alignment=TA_CENTER,
            spaceBefore=0, spaceAfter=0, leading=20,
        ),
        "cert_heading": ParagraphStyle(
            "cert_heading", fontSize=13, textColor=PURPLE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            spaceBefore=0, spaceAfter=6, letterSpacing=2,
        ),
        "cert_body": ParagraphStyle(
            "cert_body", fontSize=11, textColor=DARK_GRAY,
            fontName="Helvetica", alignment=TA_CENTER,
            leading=18, spaceAfter=0,
        ),
        "meta": ParagraphStyle(
            "meta", fontSize=8.5, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER, leading=13,
        ),
        "cert_id": ParagraphStyle(
            "cert_id", fontSize=8, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        # Page 2 styles
        "p2_heading": ParagraphStyle(
            "p2_heading", fontSize=13, textColor=PURPLE_DARK,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
        ),
        "p2_body": ParagraphStyle(
            "p2_body", fontSize=9.5, textColor=DARK_GRAY,
            fontName="Helvetica", leading=14, spaceAfter=3,
        ),
        "p2_label": ParagraphStyle(
            "p2_label", fontSize=8.5, textColor=MID_GRAY,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "p2_evidence": ParagraphStyle(
            "p2_evidence", fontSize=8.5, textColor=MID_GRAY,
            fontName="Helvetica-Oblique", leading=13,
        ),
        "p2_article": ParagraphStyle(
            "p2_article", fontSize=10, textColor=DARK_GRAY,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "p2_meta": ParagraphStyle(
            "p2_meta", fontSize=8, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER, leading=12,
        ),
    }


# ── Canvas decorators ─────────────────────────────────────────────────────────

def _draw_cert_border(canvas, doc):
    """Decorative double border with corner ornaments for page 1."""
    canvas.saveState()
    w, h = PAGE_W, PAGE_H
    m = 0.28 * inch

    # Outer rectangle — gold
    canvas.setStrokeColor(BORDER_GOLD)
    canvas.setLineWidth(2.5)
    canvas.rect(m, m, w - 2 * m, h - 2 * m)

    # Inner rectangle — purple, inset
    i = m + 0.12 * inch
    canvas.setStrokeColor(PURPLE)
    canvas.setLineWidth(0.8)
    canvas.rect(i, i, w - 2 * i, h - 2 * i)

    # Thin line between — gold
    mid = m + 0.06 * inch
    canvas.setStrokeColor(GOLD_LIGHT)
    canvas.setLineWidth(0.4)
    canvas.rect(mid, mid, w - 2 * mid, h - 2 * mid)

    # Corner diamond ornaments at outer border corners
    cs = [
        (m, m), (w - m, m), (m, h - m), (w - m, h - m),
    ]
    r = 0.055 * inch
    canvas.setFillColor(BORDER_GOLD)
    canvas.setStrokeColor(BORDER_GOLD)
    for cx, cy in cs:
        # Diamond: draw as rotated square
        canvas.saveState()
        canvas.translate(cx, cy)
        canvas.rotate(45)
        canvas.rect(-r * 0.7, -r * 0.7, r * 1.4, r * 1.4, fill=1)
        canvas.restoreState()

    # Mid-side small diamond ornaments
    mids = [
        (w / 2, m), (w / 2, h - m),
        (m, h / 2), (w - m, h / 2),
    ]
    r2 = 0.035 * inch
    for cx, cy in mids:
        canvas.saveState()
        canvas.translate(cx, cy)
        canvas.rotate(45)
        canvas.rect(-r2 * 0.7, -r2 * 0.7, r2 * 1.4, r2 * 1.4, fill=1)
        canvas.restoreState()

    # Subtle background tint inside the inner border
    canvas.setFillColor(CREAM)
    canvas.setStrokeColor(colors.white)
    canvas.rect(i + 0.01, i + 0.01, w - 2 * i - 0.02, h - 2 * i - 0.02,
                fill=1, stroke=0)

    canvas.restoreState()


def _draw_detail_header(canvas, doc):
    """Lightweight header/footer for page 2."""
    canvas.saveState()
    w, h = PAGE_W, PAGE_H

    # Top bar
    canvas.setFillColor(PURPLE_DARK)
    canvas.rect(0, h - 0.45 * inch, w, 0.45 * inch, fill=1, stroke=0)

    # "PRAGMA" wordmark in top bar
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(w / 2, h - 0.28 * inch, "PRAGMA  ·  COMPLIANCE ASSESSMENT")

    # Bottom bar
    canvas.setFillColor(PURPLE_DARK)
    canvas.rect(0, 0, w, 0.35 * inch, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(
        w / 2, 0.13 * inch,
        "EU AI Act Compliance Readiness Report  ·  pragma.ai  ·  "
        "Not a legal certification by a notified body"
    )

    canvas.restoreState()


# ── Pragma logo helper ─────────────────────────────────────────────────────────

def _draw_logo(canvas, x, y, size=0.55 * inch):
    """Draw the Pragma icon if available, otherwise draw a styled 'P' monogram."""
    if os.path.exists(LOGO_PATH):
        canvas.drawImage(
            LOGO_PATH, x - size / 2, y - size / 2, size, size,
            mask="auto", preserveAspectRatio=True,
        )
    else:
        # Fallback monogram circle
        r = size / 2
        canvas.setFillColor(PURPLE)
        canvas.circle(x, y, r, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", int(size * 22))
        canvas.drawCentredString(x, y - size * 0.12, "P")


# ── Score ring (drawn inline on canvas, not a flowable) ──────────────────────

def _verdict_ring(canvas, cx, cy, score_pct: int, verdict: str):
    """Draw a circular score ring with verdict text in the center."""
    palette = VERDICT_PALETTE.get(verdict, VERDICT_PALETTE["not_ready"])
    text_color, ring_color, _ , label = palette

    R = 0.72 * inch   # outer radius
    r = 0.52 * inch   # inner radius (ring thickness)

    # Background circle
    canvas.setFillColor(colors.HexColor("#f0eef8"))
    canvas.circle(cx, cy, R + 0.04 * inch, fill=1, stroke=0)

    # Gray track
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.setLineWidth(R - r)
    canvas.circle(cx, cy, (R + r) / 2, fill=0, stroke=1)

    # Colored arc for the score
    if score_pct > 0:
        from reportlab.graphics.shapes import ArcPath
        import math
        angle_span = 360 * score_pct / 100
        start = 90   # start from top
        # Draw arc using canvas arc
        canvas.setStrokeColor(ring_color)
        canvas.setLineWidth(R - r)
        canvas.setLineCap(1)
        # Use wedge approximation with many small lines
        steps = max(int(angle_span / 2), 1)
        prev_x = cx + ((R + r) / 2) * math.cos(math.radians(start))
        prev_y = cy + ((R + r) / 2) * math.sin(math.radians(start))
        canvas.setStrokeColor(ring_color)
        canvas.setLineWidth(R - r)
        p = canvas.beginPath()
        for step in range(steps + 1):
            angle = math.radians(start + angle_span * step / steps)
            nx = cx + ((R + r) / 2) * math.cos(angle)
            ny = cy + ((R + r) / 2) * math.sin(angle)
            if step == 0:
                p.moveTo(nx, ny)
            else:
                p.lineTo(nx, ny)
        canvas.drawPath(p, stroke=1, fill=0)

    # Inner white circle (creates the ring effect)
    canvas.setFillColor(colors.white)
    canvas.circle(cx, cy, r, fill=1, stroke=0)

    # Score percentage — large
    canvas.setFillColor(text_color)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawCentredString(cx, cy + 0.10 * inch, f"{score_pct}%")

    # Label below score
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GRAY)
    canvas.drawCentredString(cx, cy - 0.08 * inch, "SCORE")

    # Verdict label curved above ring
    canvas.setFillColor(text_color)
    canvas.setFont("Helvetica-Bold", 7.5)
    # Split label into two lines if needed
    words = label.split()
    if len(words) > 2:
        line1 = " ".join(words[:2])
        line2 = " ".join(words[2:])
        canvas.drawCentredString(cx, cy - 0.28 * inch, line1)
        canvas.drawCentredString(cx, cy - 0.40 * inch, line2)
    else:
        canvas.drawCentredString(cx, cy - 0.32 * inch, label)


# ── Page 1 builder ────────────────────────────────────────────────────────────

def _build_page1(canvas, compliance: Dict, certificate_id: str):
    """Draw page 1 entirely on the canvas (gives full layout control)."""
    canvas.saveState()
    _draw_cert_border(canvas, None)

    now = datetime.now(timezone.utc)
    issued   = now.strftime("%B %d, %Y")
    valid_dt = now.replace(year=now.year + 1).strftime("%B %d, %Y")

    w, h = PAGE_W, PAGE_H
    inner_x  = 0.65 * inch
    inner_w  = w - 1.30 * inch
    cx       = w / 2

    y = h - 0.72 * inch

    # ── Pragma logo ──────────────────────────────────────────────────────────
    _draw_logo(canvas, cx, y, size=0.60 * inch)
    y -= 0.42 * inch

    # ── PRAGMA wordmark ──────────────────────────────────────────────────────
    canvas.setFillColor(PURPLE_DARK)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(cx, y, "PRAGMA")
    y -= 0.18 * inch

    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(cx, y, "A I   C O M P L I A N C E   F I R E W A L L")
    y -= 0.22 * inch

    # ── Gold divider ─────────────────────────────────────────────────────────
    canvas.setStrokeColor(BORDER_GOLD)
    canvas.setLineWidth(1.2)
    canvas.line(inner_x + 0.8 * inch, y, cx + inner_w / 2 - 0.8 * inch, y)
    y -= 0.22 * inch

    # ── Certificate title ────────────────────────────────────────────────────
    canvas.setFillColor(PURPLE)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawCentredString(cx, y, "CERTIFICATE OF COMPLIANCE READINESS")
    y -= 0.16 * inch

    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawCentredString(cx, y, "European Union Artificial Intelligence Act  ·  Articles 9 – 14")
    y -= 0.30 * inch

    # ── Gold divider ─────────────────────────────────────────────────────────
    canvas.setStrokeColor(BORDER_GOLD)
    canvas.setLineWidth(0.6)
    dw = inner_w * 0.7
    canvas.line(cx - dw / 2, y, cx + dw / 2, y)
    y -= 0.32 * inch

    # ── Formal certificate language ───────────────────────────────────────────
    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica-Oblique", 10)
    canvas.drawCentredString(cx, y, "This is to certify that")
    y -= 0.40 * inch

    # ── Company name ─────────────────────────────────────────────────────────
    company = compliance.get("company_name", "—")
    canvas.setFillColor(PURPLE_DARK)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawCentredString(cx, y, company)
    y -= 0.28 * inch

    # ── AI System name ────────────────────────────────────────────────────────
    system = compliance.get("system_name", "—")
    canvas.setFillColor(DARK_GRAY)
    canvas.setFont("Helvetica", 14)
    canvas.drawCentredString(cx, y, system)
    y -= 0.24 * inch

    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica-Oblique", 10)
    canvas.drawCentredString(cx, y,
        "has demonstrated readiness for compliance with the requirements of the")
    y -= 0.20 * inch
    canvas.setFont("Helvetica-Bold", 10.5)
    canvas.setFillColor(DARK_GRAY)
    canvas.drawCentredString(cx, y,
        "EU Artificial Intelligence Act — Articles 9 through 14")
    y -= 0.18 * inch
    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica-Oblique", 10)
    canvas.drawCentredString(cx, y, f"as assessed by Pragma on {issued}")
    y -= 0.30 * inch

    # ── Gold divider ─────────────────────────────────────────────────────────
    canvas.setStrokeColor(BORDER_GOLD)
    canvas.setLineWidth(0.6)
    canvas.line(cx - dw / 2, y, cx + dw / 2, y)
    y -= 0.50 * inch

    # ── Score ring + stats block ──────────────────────────────────────────────
    score_pct = int(compliance.get("overall_score", 0) * 100)
    verdict   = compliance.get("verdict", "not_ready")
    ring_cy   = y - 0.60 * inch
    _verdict_ring(canvas, cx, ring_cy, score_pct, verdict)

    # Stats columns beside the ring
    passes   = compliance.get("passes", 0)
    partials = compliance.get("partials", 0)
    fails    = compliance.get("fails", 0)

    stat_col_x = cx + 1.05 * inch
    stat_items = [
        (str(passes),   "Articles Passed", GREEN),
        (str(partials), "Partial",          AMBER),
        (str(fails),    "Not Met",          RED),
    ]
    sy = ring_cy + 0.35 * inch
    for val, label, col in stat_items:
        canvas.setFillColor(col)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(stat_col_x, sy, val)
        canvas.setFillColor(MID_GRAY)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(stat_col_x, sy - 0.18 * inch, label)
        sy -= 0.52 * inch

    # Risk tier badge left of ring
    tier_col_x = cx - 1.05 * inch
    tier        = compliance.get("risk_tier_label", "—")
    canvas.setFillColor(PURPLE_DARK)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(tier_col_x, ring_cy + 0.28 * inch, "RISK TIER")
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(PURPLE)
    # Word-wrap if needed
    for idx, word in enumerate(tier.split()):
        canvas.drawCentredString(tier_col_x, ring_cy + 0.12 * inch - idx * 0.16 * inch, word)

    y = ring_cy - 0.85 * inch

    # ── Thin divider ─────────────────────────────────────────────────────────
    canvas.setStrokeColor(BORDER_GOLD)
    canvas.setLineWidth(0.6)
    canvas.line(cx - dw / 2, y, cx + dw / 2, y)
    y -= 0.28 * inch

    # ── Certificate metadata row ──────────────────────────────────────────────
    meta_items = [
        ("Certificate ID", certificate_id),
        ("Issue Date",     issued),
        ("Valid Until",    valid_dt),
    ]
    col_w = inner_w / 3
    for i, (label, value) in enumerate(meta_items):
        mx = inner_x + col_w * i + col_w / 2
        canvas.setFillColor(MID_GRAY)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString(mx, y, label.upper())
        canvas.setFillColor(DARK_GRAY)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(mx, y - 0.16 * inch, value)

    y -= 0.36 * inch

    # ── Thin divider ─────────────────────────────────────────────────────────
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.setLineWidth(0.5)
    canvas.line(inner_x, y, inner_x + inner_w, y)
    y -= 0.20 * inch

    # ── Issued by Pragma + signature line ────────────────────────────────────
    sig_col_x = cx - 1.4 * inch
    canvas.setStrokeColor(DARK_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(sig_col_x - 0.7 * inch, y, sig_col_x + 0.7 * inch, y)
    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(sig_col_x, y - 0.14 * inch, "Issued by Pragma")

    # Pragma seal right side
    seal_x = cx + 1.4 * inch
    _draw_logo(canvas, seal_x, y - 0.08 * inch, size=0.36 * inch)
    canvas.setFillColor(PURPLE_DARK)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(seal_x, y - 0.33 * inch, "PRAGMA SEAL")

    y -= 0.45 * inch

    # ── Disclaimer ───────────────────────────────────────────────────────────
    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica", 6.5)
    disclaimer = (
        "This certificate documents compliance readiness against Pragma's implementation of EU AI Act Articles 9–14. "
        "It is not a legal certification by a notified body. High-risk AI systems require formal conformity "
        "assessment before EU deployment. Valid for one year from issue date."
    )
    # Simple word-wrap at ~115 chars per line
    words = disclaimer.split()
    line, lines = [], []
    for word in words:
        if len(" ".join(line + [word])) > 115:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    for ln in lines:
        canvas.drawCentredString(cx, y, ln)
        y -= 0.12 * inch

    canvas.restoreState()


# ── Page 2 builder (Platypus) ─────────────────────────────────────────────────

def _build_page2_story(compliance: Dict, certificate_id: str, s: Dict):
    story = []

    story.append(Spacer(1, 0.15 * inch))

    # Section heading
    story.append(Paragraph("Article-by-Article Compliance Assessment", s["p2_heading"]))

    # System info table
    stats  = compliance.get("stats", {})
    cats   = stats.get("categories", [])
    info_rows = [
        ["Company",               compliance.get("company_name", "—")],
        ["AI System",             compliance.get("system_name", "—")],
        ["Risk Tier",             compliance.get("risk_tier_label", "—")],
        ["Use Case Category",     cats[0] if cats else "—"],
        ["Evaluations Logged",    str(stats.get("total", 0))],
        ["HITL Overrides",        str(stats.get("hitl_overrides", 0))],
        ["Proxy Variables Caught",str(stats.get("proxy_vars_caught", 0))],
        ["Certificate ID",        certificate_id],
    ]
    tbl = Table(
        [[Paragraph(f"<b>{k}</b>", s["p2_label"]),
          Paragraph(str(v), s["p2_body"])] for k, v in info_rows],
        colWidths=[1.9 * inch, 5.6 * inch],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_GRAY),
        ("ROWPADDING",   (0, 0), (-1, -1), 5),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND",   (0, 0), (0, -1), colors.HexColor("#ede9f8")),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("EU AI Act — Articles 9 through 14", s["p2_heading"]))

    articles = compliance.get("articles", {})
    for key, article in articles.items():
        status = article.get("status", "fail")
        fg, bg, icon_label = STATUS_COLOR.get(status, (MID_GRAY, LIGHT_GRAY, "?"))

        title       = article.get("title", key)
        description = article.get("description", "")
        requirement = article.get("requirement", "")
        evidence    = article.get("evidence", "")

        # Status badge cell
        badge_tbl = Table(
            [[Paragraph(f'<font color="white"><b>{icon_label}</b></font>', s["p2_body"])]],
            colWidths=[1.15 * inch],
        )
        badge_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), fg),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",  (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ]))

        # Detail cell
        detail_tbl = Table([
            [Paragraph(title, s["p2_article"])],
            [Paragraph(description, s["p2_body"])],
            [Paragraph(f"<b>Requirement:</b> {requirement}", s["p2_evidence"])],
            [Paragraph(f"<b>Evidence:</b> <i>{evidence}</i>", s["p2_evidence"])],
        ], colWidths=[6.35 * inch])
        detail_tbl.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))

        row_tbl = Table([[badge_tbl, detail_tbl]], colWidths=[1.15 * inch, 6.35 * inch])
        row_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("ROWPADDING",    (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(row_tbl)
        story.append(Spacer(1, 0.07 * inch))

    story.append(Spacer(1, 0.12 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "This document is generated by Pragma (pragma.ai). It constitutes a compliance readiness assessment, not a "
        "legal certification. High-risk AI systems as defined by the EU AI Act require conformity assessment by a "
        "notified body prior to EU market placement. Renew this report annually or after material system changes.",
        s["p2_meta"],
    ))
    return story


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_certificate(compliance: Dict[str, Any], certificate_id: str) -> bytes:
    """Generate a two-page PDF compliance certificate and return bytes."""
    buffer = io.BytesIO()
    s = _s()

    # We use a custom canvas class to intercept page events
    class CertCanvas:
        pass

    # Build with BaseDocTemplate so we can attach per-page canvas hooks
    doc = BaseDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    # Page 1 — blank frame (we draw everything manually in onPage)
    p1_frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        PAGE_W - doc.leftMargin - doc.rightMargin,
        PAGE_H - doc.topMargin - doc.bottomMargin,
        id="p1",
    )

    # Page 2 — normal content frame below the header bar
    p2_frame = Frame(
        0.65 * inch, 0.55 * inch,
        PAGE_W - 1.30 * inch,
        PAGE_H - 0.45 * inch - 0.55 * inch,  # leave room for header bar
        id="p2",
    )

    _compliance_ref = compliance
    _cert_id_ref    = certificate_id

    def on_page1(canvas, doc):
        _build_page1(canvas, _compliance_ref, _cert_id_ref)

    def on_page2(canvas, doc):
        _draw_detail_header(canvas, doc)

    t1 = PageTemplate(id="cert",   frames=[p1_frame], onPage=on_page1)
    t2 = PageTemplate(id="detail", frames=[p2_frame], onPage=on_page2)
    doc.addPageTemplates([t1, t2])

    # Story: page 1 is all canvas — just push a page break, then page 2 content
    story = [
        NextPageTemplate("detail"),
        PageBreak(),
    ] + _build_page2_story(compliance, certificate_id, s)

    doc.build(story)
    return buffer.getvalue()
