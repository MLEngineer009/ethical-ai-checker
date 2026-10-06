"""
Law Research Agent — daily sweep for new AI hiring regulations.

Sources:
  - Federal Register API (federalregister.gov)
  - EEOC newsroom RSS

Pipeline per finding:
  1. Fetch documents published in the last N days
  2. Claude filters: is this about AI + hiring compliance?
  3. Claude drafts a compliance rule config (JSON — inserted into compliance_rules table)
  4. Finding saved with status=pending, activate_at = now + 24h
  5. Admin email sent: "New rule found — activates in 24h"
  6. activate_pending() runs daily — promotes rules into the live engine
  7. Admin can reject any pending rule via /admin/law-agent/findings/{id}/reject

Environment vars:
  ANTHROPIC_API_KEY          — required
  RESEND_API_KEY             — for email notifications
  ADMIN_EMAIL                — where to send alerts (default: cosmosservicesai@gmail.com)
  LAW_AGENT_ACTIVATION_HOURS — hours before auto-activation (default: 24)
  LAW_AGENT_DAYS_BACK        — how far back to search (default: 7)
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "cosmosservicesai@gmail.com")
ACTIVATION_DELAY_HOURS = int(os.getenv("LAW_AGENT_ACTIVATION_HOURS", "24"))


# ── Source fetchers ───────────────────────────────────────────────────────────

def _fetch_federal_register(days_back: int = 7) -> List[Dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        r = httpx.get(
            "https://www.federalregister.gov/api/v1/articles.json",
            params={
                "conditions[term]": "artificial intelligence hiring employment discrimination",
                "conditions[publication_date][gte]": since,
                "conditions[type][]": ["Rule", "Proposed Rule", "Notice", "Guidance Document"],
                "per_page": 20,
                "order": "newest",
                "fields[]": [
                    "title", "abstract", "publication_date",
                    "html_url", "document_number",
                ],
            },
            timeout=30,
        )
        r.raise_for_status()
        items = []
        for item in r.json().get("results", []):
            items.append({
                "title":            item.get("title", ""),
                "abstract":         item.get("abstract", ""),
                "url":              item.get("html_url", ""),
                "published_date":   item.get("publication_date", ""),
                "source":           "federal_register",
            })
        return items
    except Exception as e:
        logger.error("Federal Register fetch failed: %s", e)
        return []


def _fetch_eeoc_rss(days_back: int = 7) -> List[Dict]:
    try:
        r = httpx.get(
            "https://www.eeoc.gov/newsroom/rss.xml",
            timeout=30,
            headers={"User-Agent": "Pragma-LawAgent/1.0"},
        )
        r.raise_for_status()
        items = []
        for item_text in re.findall(r"<item>(.*?)</item>", r.text, re.DOTALL):
            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", item_text, re.DOTALL)
            link_m  = re.search(r"<link>(.*?)</link>",               item_text, re.DOTALL)
            desc_m  = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>", item_text, re.DOTALL)
            date_m  = re.search(r"<pubDate>(.*?)</pubDate>",         item_text, re.DOTALL)
            if not title_m:
                continue
            title = (title_m.group(1) or title_m.group(2) or "").strip()
            desc  = ""
            if desc_m:
                desc = (desc_m.group(1) or desc_m.group(2) or "").strip()
            items.append({
                "title":          title,
                "abstract":       desc[:1000],
                "url":            (link_m.group(1) or "").strip() if link_m else "",
                "published_date": (date_m.group(1) or "").strip() if date_m else "",
                "source":         "eeoc",
            })
        return items[:15]
    except Exception as e:
        logger.error("EEOC RSS fetch failed: %s", e)
        return []


# ── Claude analysis ───────────────────────────────────────────────────────────

_RELEVANCE_PROMPT = """\
You are a compliance engineer at Pragma, an AI compliance firewall for hiring decisions.

Assess this regulatory document. Respond with JSON only — no markdown, no explanation.

{{
  "relevant": true or false,
  "reason": "one sentence",
  "regulation_name": "short name e.g. EEOC Guidance on AI Hiring 2026",
  "statute_citation": "e.g. 42 U.S.C. § 2000e-2  or  N/A",
  "key_requirement": "one sentence describing the core compliance requirement, or null",
  "jurisdiction": "federal | california | new_york | illinois | other_state | eu | other",
  "category": "hiring | lending | both | other"
}}

Only mark relevant=true if: (1) it specifically concerns AI-assisted hiring/employment decisions AND (2) it creates a new enforceable compliance requirement.

Title: {title}
Summary: {abstract}
Source: {source}
Published: {published_date}
"""

_RULE_DRAFT_PROMPT = """\
You are building a compliance rule for Pragma's rule engine.

The rule will be inserted into a database and loaded at runtime. It must detect a compliance \
violation in AI hiring decisions. Be conservative — only flag clear violations, not edge cases.

Regulation: {regulation_name}
Citation: {statute_citation}
Requirement: {key_requirement}
Jurisdiction: {jurisdiction}

Respond with JSON only — no markdown:

{{
  "rule_key": "snake_case_unique_key_under_50_chars e.g. eeoc_ai_resume_screen_2026",
  "regulation": "Full regulation name with citation",
  "description": "Plain-English description of what this rule checks for",
  "rule_type": "regex",
  "config_json": {{
    "patterns": ["regex or keyword patterns in decision text that trigger this rule"],
    "fields": ["context field names that are red flags e.g. resume_score, ai_ranking"],
    "explanation": "What constitutes a violation under this rule"
  }},
  "default_severity": "FAIL or FLAG",
  "categories": ["hiring"],
  "plain_english": "One sentence a non-lawyer can understand"
}}
"""


def _analyze_finding(finding: Dict, client) -> Optional[Dict]:
    try:
        relevance_prompt = _RELEVANCE_PROMPT.format(
            title=finding.get("title", ""),
            abstract=finding.get("abstract", "")[:800],
            source=finding.get("source", ""),
            published_date=finding.get("published_date", ""),
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": relevance_prompt}],
        )
        analysis = json.loads(msg.content[0].text.strip())

        if not analysis.get("relevant") or analysis.get("category") not in ("hiring", "both"):
            return None

        rule_prompt = _RULE_DRAFT_PROMPT.format(
            regulation_name=analysis["regulation_name"],
            statute_citation=analysis.get("statute_citation", "N/A"),
            key_requirement=analysis.get("key_requirement", ""),
            jurisdiction=analysis.get("jurisdiction", "federal"),
        )

        rule_msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": rule_prompt}],
        )
        rule_config = json.loads(rule_msg.content[0].text.strip())

        return {"analysis": analysis, "rule_config": rule_config}

    except Exception as e:
        logger.error("Claude analysis failed for '%s': %s", finding.get("title"), e)
        return None


# ── Main entry points ─────────────────────────────────────────────────────────

def run(days_back: int | None = None) -> Dict[str, Any]:
    """
    Run the law research agent. Fetch sources, filter with Claude, save pending rules.
    Returns a stats dict.
    """
    from anthropic import Anthropic
    from . import database

    if days_back is None:
        days_back = int(os.getenv("LAW_AGENT_DAYS_BACK", "7"))

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set — law agent cannot run")
        return {"error": "ANTHROPIC_API_KEY not configured", "found": 0, "relevant": 0, "drafted": 0}

    client = Anthropic(api_key=api_key)

    raw_findings: List[Dict] = []
    raw_findings.extend(_fetch_federal_register(days_back))
    raw_findings.extend(_fetch_eeoc_rss(days_back))

    logger.info("Law agent: fetched %d raw findings", len(raw_findings))

    stats: Dict[str, Any] = {
        "found": len(raw_findings),
        "relevant": 0,
        "drafted": 0,
        "skipped_duplicate": 0,
        "new_findings": [],
    }

    now = datetime.now(timezone.utc).isoformat()
    activate_at = (
        datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_DELAY_HOURS)
    ).isoformat()

    for finding in raw_findings:
        url_hash = hashlib.sha256(finding["url"].encode()).hexdigest()[:16]

        if database.law_agent_finding_exists(url_hash):
            stats["skipped_duplicate"] += 1
            continue

        result = _analyze_finding(finding, client)

        if result is None:
            database.save_law_agent_finding({
                "source":         finding["source"],
                "source_url":     finding["url"],
                "url_hash":       url_hash,
                "title":          finding["title"][:500],
                "published_date": finding["published_date"][:50],
                "raw_summary":    finding["abstract"][:2000],
                "relevant":       0,
                "status":         "not_relevant",
                "discovered_at":  now,
            })
            continue

        stats["relevant"] += 1
        analysis    = result["analysis"]
        rule_config = result["rule_config"]

        finding_id = database.save_law_agent_finding({
            "source":           finding["source"],
            "source_url":       finding["url"],
            "url_hash":         url_hash,
            "title":            finding["title"][:500],
            "published_date":   finding["published_date"][:50],
            "raw_summary":      finding["abstract"][:2000],
            "relevant":         1,
            "regulation_name":  analysis.get("regulation_name", ""),
            "statute_citation": analysis.get("statute_citation", ""),
            "key_requirement":  analysis.get("key_requirement", ""),
            "jurisdiction":     analysis.get("jurisdiction", ""),
            "rule_key":         rule_config.get("rule_key", ""),
            "rule_config_json": json.dumps(rule_config),
            "status":           "pending",
            "activate_at":      activate_at,
            "discovered_at":    now,
        })

        stats["drafted"] += 1
        stats["new_findings"].append({
            "id":          finding_id,
            "title":       finding["title"],
            "regulation":  analysis.get("regulation_name", ""),
            "rule_key":    rule_config.get("rule_key", ""),
            "activate_at": activate_at,
        })

        logger.info(
            "Law agent: new finding — '%s' → rule '%s'",
            finding["title"], rule_config.get("rule_key"),
        )

    if stats["new_findings"]:
        try:
            _send_admin_notification(stats["new_findings"])
        except Exception as e:
            logger.error("Admin notification failed: %s", e)

    logger.info("Law agent run complete: %s", {k: v for k, v in stats.items() if k != "new_findings"})
    return stats


def activate_pending(now: Optional[datetime] = None) -> int:
    """
    Promote pending findings whose activate_at has passed into the live compliance_rules table.
    Returns the count of rules activated.
    """
    from . import database

    if now is None:
        now = datetime.now(timezone.utc)

    pending = database.get_pending_law_agent_findings(before=now.isoformat())
    activated = 0

    for finding in pending:
        try:
            rule_config = json.loads(finding["rule_config_json"] or "{}")
            if not rule_config.get("rule_key"):
                continue

            database.upsert_compliance_rule_from_agent({
                "rule_key":        rule_config["rule_key"],
                "regulation":      rule_config.get("regulation", ""),
                "description":     rule_config.get("description", ""),
                "rule_type":       rule_config.get("rule_type", "regex"),
                "config_json":     json.dumps(rule_config.get("config_json", {})),
                "default_severity": rule_config.get("default_severity", "FLAG"),
                "categories":      json.dumps(rule_config.get("categories", ["hiring"])),
            })

            database.activate_law_agent_finding(finding["id"])
            activated += 1
            logger.info("Law agent: activated rule '%s'", rule_config["rule_key"])

        except Exception as e:
            logger.error("Failed to activate finding id=%s: %s", finding.get("id"), e)

    return activated


# ── Email notification ────────────────────────────────────────────────────────

def _send_admin_notification(findings: List[Dict]) -> None:
    try:
        import resend
        resend.api_key = os.getenv("RESEND_API_KEY", "")
        if not resend.api_key:
            return

        rows = "".join(
            f"""<tr>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;">{f['regulation']}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;font-family:monospace;font-size:12px;">{f['rule_key']}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;">{f['activate_at'][:10]}</td>
            </tr>"""
            for f in findings
        )

        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
          <h2 style="color:#7c3aed;">Pragma Law Agent — New Findings</h2>
          <p><strong>{len(findings)}</strong> new AI hiring regulation(s) discovered.
          Rules activate automatically in {ACTIVATION_DELAY_HOURS}h unless rejected.</p>
          <table style="width:100%;border-collapse:collapse;margin:16px 0;">
            <thead>
              <tr style="background:#f5f5f5;">
                <th style="padding:8px 12px;text-align:left;font-size:12px;">Regulation</th>
                <th style="padding:8px 12px;text-align:left;font-size:12px;">Rule Key</th>
                <th style="padding:8px 12px;text-align:left;font-size:12px;">Activates</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
          <p><a href="https://usepragma.co" style="color:#7c3aed;">Review &amp; reject at usepragma.co → Admin → Law Agent</a></p>
          <p style="color:#999;font-size:12px;">Pragma Law Agent · cosmosservicesai@gmail.com</p>
        </div>
        """

        resend.Emails.send({
            "from":    "Pragma <noreply@usepragma.co>",
            "to":      [ADMIN_EMAIL],
            "subject": f"[Pragma] {len(findings)} new hiring rule(s) found — activating {ACTIVATION_DELAY_HOURS}h",
            "html":    html,
        })
    except Exception as e:
        logger.error("_send_admin_notification failed: %s", e)
