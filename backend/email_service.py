"""
Email service — Resend integration with HTML templates.

Set RESEND_API_KEY and EMAIL_FROM in environment.
EMAIL_FROM defaults to "Pragma <notifications@usepragma.ai>".

Templates:
  welcome         — sent on first Google login
  gap_reminder    — 30-day nudge for systems with PARTIAL / FAIL articles
  countdown       — weekly EU AI Act deadline countdown
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FROM    = os.getenv("EMAIL_FROM", "Pragma <notifications@usepragma.ai>")
_APP_URL = os.getenv("APP_URL", "https://virtuous-fulfillment-production-05d3.up.railway.app")

# EU AI Act key deadlines
_EUAIA_HIGH_RISK_DATE = "1 August 2026"


def _resend_client():
    import resend
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError("RESEND_API_KEY is not set")
    resend.api_key = key
    return resend


def send(to: str, subject: str, html: str) -> bool:
    """Send a single email. Returns True on success, False on error."""
    try:
        rs = _resend_client()
        rs.Emails.send({"from": _FROM, "to": to, "subject": subject, "html": html})
        logger.info("Email sent — to=%s subject=%r", to.split("@")[0] + "@…", subject)
        return True
    except Exception as e:
        logger.error("Email send failed — to=%s error=%s", to, e)
        return False


# ── Base layout ────────────────────────────────────────────────────────────────

def _layout(name: str, body: str, unsubscribe_token: str) -> str:
    unsub_url = f"{_APP_URL}/notifications/unsubscribe?token={unsubscribe_token}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pragma</title>
</head>
<body style="margin:0;padding:0;background:#0a0b0f;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0b0f;padding:40px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="padding:0 0 24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#111318;border:1px solid #1e2232;border-radius:10px;padding:20px 28px;">
                  <span style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px;">🛡️ Pragma</span>
                  <span style="font-size:12px;color:rgba(255,255,255,0.4);margin-left:10px;">AI Compliance Firewall</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#111318;border:1px solid #1e2232;border-radius:10px;padding:32px 28px;">
            <p style="margin:0 0 8px 0;font-size:14px;color:rgba(255,255,255,0.5);">Hi {name},</p>
            {body}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 0 0 0;text-align:center;">
            <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.25);line-height:1.6;">
              Pragma · AI Compliance Firewall<br>
              <a href="{unsub_url}" style="color:rgba(255,255,255,0.25);text-decoration:underline;">Unsubscribe</a>
              &nbsp;·&nbsp;
              <a href="{_APP_URL}" style="color:rgba(255,255,255,0.25);text-decoration:underline;">Open app</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Shared components ──────────────────────────────────────────────────────────

def _btn(label: str, url: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" style="margin:24px 0 0 0;">'
        f'<tr><td style="background:#6366f1;border-radius:8px;">'
        f'<a href="{url}" style="display:inline-block;padding:12px 24px;font-size:14px;'
        f'font-weight:600;color:#fff;text-decoration:none;letter-spacing:0.1px;">{label}</a>'
        f'</td></tr></table>'
    )


def _article_row(article: str, title: str, status: str) -> str:
    colors = {
        "pass":    ("#22c55e", "PASS"),
        "partial": ("#f59e0b", "PARTIAL"),
        "fail":    ("#ef4444", "FAIL"),
    }
    color, label = colors.get(status, ("#6b7280", status.upper()))
    return (
        f'<tr>'
        f'<td style="padding:8px 0;border-bottom:1px solid #1e2232;font-size:13px;color:rgba(255,255,255,0.7);">'
        f'<b style="color:#fff;">{article}</b> — {title}</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #1e2232;text-align:right;">'
        f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
        f'border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;">{label}</span>'
        f'</td></tr>'
    )


# ── Template: welcome ──────────────────────────────────────────────────────────

def welcome_html(name: str, unsubscribe_token: str) -> str:
    body = f"""
<h2 style="margin:0 0 16px 0;font-size:22px;font-weight:800;color:#fff;line-height:1.2;">
  Welcome to Pragma
</h2>
<p style="margin:0 0 16px 0;font-size:15px;color:rgba(255,255,255,0.7);line-height:1.6;">
  You're now set up to assess your AI systems against the full
  <strong style="color:#fff;">EU AI Act (Regulation EU 2024/1689)</strong> —
  15 articles, evidence-based scoring, and a downloadable compliance certificate.
</p>

<div style="background:#0d0e14;border:1px solid #1e2232;border-radius:8px;padding:20px;margin:20px 0;">
  <p style="margin:0 0 12px 0;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.4);">
    Get started in 3 steps
  </p>
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="padding:6px 0;font-size:13px;color:rgba(255,255,255,0.75);">
        <span style="color:#6366f1;font-weight:700;">1.</span>&nbsp;
        Register your AI system — takes 5 minutes
      </td>
    </tr>
    <tr>
      <td style="padding:6px 0;font-size:13px;color:rgba(255,255,255,0.75);">
        <span style="color:#6366f1;font-weight:700;">2.</span>&nbsp;
        Run your first decision evaluation to activate Arts. 9, 12, 13, 14
      </td>
    </tr>
    <tr>
      <td style="padding:6px 0;font-size:13px;color:rgba(255,255,255,0.75);">
        <span style="color:#6366f1;font-weight:700;">3.</span>&nbsp;
        Download your compliance certificate for auditors and investors
      </td>
    </tr>
  </table>
</div>

<div style="background:#1a1033;border:1px solid rgba(99,102,241,0.3);border-radius:8px;padding:16px;margin:20px 0;">
  <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.7);line-height:1.6;">
    ⏰ <strong style="color:#fff;">EU AI Act deadline:</strong>
    High-risk AI obligations apply from <strong style="color:#a78bfa;">{_EUAIA_HIGH_RISK_DATE}</strong>.
    Systems in credit, hiring, healthcare, and law enforcement need to be compliant by then.
  </p>
</div>

{_btn("Open Pragma →", _APP_URL)}
"""
    return _layout(name, body, unsubscribe_token)


def welcome_subject() -> str:
    return "Welcome to Pragma — your EU AI Act compliance dashboard"


# ── Template: gap reminder ─────────────────────────────────────────────────────

def gap_reminder_html(
    name: str,
    system_name: str,
    company_name: str,
    fails: List[Dict[str, Any]],
    partials: List[Dict[str, Any]],
    score: float,
    days_unresolved: int,
    unsubscribe_token: str,
) -> str:
    score_pct = round(score * 100)
    score_color = "#22c55e" if score >= 0.9 else "#f59e0b" if score >= 0.6 else "#ef4444"

    fail_rows = "".join(
        _article_row(a.get("article", ""), a.get("title", ""), "fail") for a in fails
    )
    partial_rows = "".join(
        _article_row(a.get("article", ""), a.get("title", ""), "partial") for a in partials
    )

    body = f"""
<h2 style="margin:0 0 6px 0;font-size:20px;font-weight:800;color:#fff;line-height:1.2;">
  {system_name} has unresolved compliance gaps
</h2>
<p style="margin:0 0 20px 0;font-size:13px;color:rgba(255,255,255,0.45);">
  {company_name} · {days_unresolved} days unresolved
</p>

<div style="background:#0d0e14;border:1px solid #1e2232;border-radius:8px;padding:16px 20px;margin:0 0 20px 0;display:flex;align-items:center;">
  <span style="font-size:28px;font-weight:800;color:{score_color};">{score_pct}%</span>
  <span style="font-size:13px;color:rgba(255,255,255,0.5);margin-left:10px;">overall compliance score</span>
</div>

{'<p style="margin:0 0 8px 0;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#ef4444;">Failing articles</p><table width="100%" cellpadding="0" cellspacing="0">' + fail_rows + '</table>' if fails else ''}

{'<p style="margin:20px 0 8px 0;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#f59e0b;">Partial articles — add evidence to upgrade to PASS</p><table width="100%" cellpadding="0" cellspacing="0">' + partial_rows + '</table>' if partials else ''}

<div style="background:#1a1033;border:1px solid rgba(99,102,241,0.3);border-radius:8px;padding:14px 16px;margin:20px 0 0 0;">
  <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.7);line-height:1.6;">
    ⏰ EU AI Act high-risk obligations apply from
    <strong style="color:#a78bfa;">{_EUAIA_HIGH_RISK_DATE}</strong>.
    Resolve these gaps before the deadline.
  </p>
</div>

{_btn("Fix compliance gaps →", _APP_URL)}
"""
    return _layout(name, body, unsubscribe_token)


def gap_reminder_subject(system_name: str, fail_count: int, partial_count: int) -> str:
    issues = fail_count + partial_count
    return f"⚠ {system_name} has {issues} compliance {'gap' if issues == 1 else 'gaps'} to resolve"


# ── Template: countdown ────────────────────────────────────────────────────────

def countdown_html(
    name: str,
    days_remaining: int,
    systems: List[Dict[str, Any]],
    unsubscribe_token: str,
) -> str:
    urgency_color = "#ef4444" if days_remaining < 60 else "#f59e0b" if days_remaining < 120 else "#6366f1"

    system_rows = ""
    for s in systems:
        score_pct = round(s.get("score", 0) * 100)
        sc = "#22c55e" if score_pct >= 90 else "#f59e0b" if score_pct >= 60 else "#ef4444"
        system_rows += (
            f'<tr>'
            f'<td style="padding:8px 0;border-bottom:1px solid #1e2232;font-size:13px;color:#fff;">'
            f'{s.get("system_name","")}</td>'
            f'<td style="padding:8px 0;border-bottom:1px solid #1e2232;font-size:13px;'
            f'color:rgba(255,255,255,0.5);">{s.get("company_name","")}</td>'
            f'<td style="padding:8px 0;border-bottom:1px solid #1e2232;text-align:right;">'
            f'<span style="color:{sc};font-weight:700;">{score_pct}%</span></td>'
            f'</tr>'
        )

    body = f"""
<h2 style="margin:0 0 6px 0;font-size:20px;font-weight:800;color:#fff;line-height:1.2;">
  EU AI Act deadline: <span style="color:{urgency_color};">{days_remaining} days remaining</span>
</h2>
<p style="margin:0 0 20px 0;font-size:14px;color:rgba(255,255,255,0.6);line-height:1.5;">
  High-risk AI obligations (Arts. 9–15, 17, 25, 27, 30, 33) apply from
  <strong style="color:#fff;">{_EUAIA_HIGH_RISK_DATE}</strong>.
  Systems in credit scoring, hiring, healthcare, and law enforcement must be compliant by then.
</p>

<p style="margin:0 0 8px 0;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.4);">
  Your registered systems
</p>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px 0;">
  <tr>
    <td style="padding:6px 0;font-size:11px;color:rgba(255,255,255,0.3);font-weight:600;text-transform:uppercase;border-bottom:1px solid #1e2232;">System</td>
    <td style="padding:6px 0;font-size:11px;color:rgba(255,255,255,0.3);font-weight:600;text-transform:uppercase;border-bottom:1px solid #1e2232;">Company</td>
    <td style="padding:6px 0;font-size:11px;color:rgba(255,255,255,0.3);font-weight:600;text-transform:uppercase;border-bottom:1px solid #1e2232;text-align:right;">Score</td>
  </tr>
  {system_rows}
</table>

{_btn("Review compliance status →", _APP_URL)}
"""
    return _layout(name, body, unsubscribe_token)


def countdown_subject(days_remaining: int) -> str:
    return f"⏰ EU AI Act deadline: {days_remaining} days — check your compliance status"
