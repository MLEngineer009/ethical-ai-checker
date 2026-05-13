"""
Notification business logic — decides what to send and to whom.

Called by send_notifications.py (Railway cron) once per day.

Three notification types:
  welcome       — first login, never sent before
  gap_reminder  — system has FAIL/PARTIAL articles, not reminded in 30 days
  countdown     — weekly EU AI Act deadline email for users with high-risk systems
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from . import database
from . import email_service

logger = logging.getLogger(__name__)

# EU AI Act high-risk deadline
_DEADLINE = datetime(2026, 8, 1, tzinfo=timezone.utc)

# Article labels for email display
_ART_LABELS = {
    "art_4":  "Art. 4",
    "art_5":  "Art. 5",
    "art_6":  "Art. 6",
    "art_9":  "Art. 9",
    "art_10": "Art. 10",
    "art_11": "Art. 11",
    "art_12": "Art. 12",
    "art_13": "Art. 13",
    "art_14": "Art. 14",
    "art_15": "Art. 15",
    "art_17": "Art. 17",
    "art_25": "Art. 25",
    "art_27": "Art. 27",
    "art_30": "Art. 30",
    "art_33": "Art. 33",
}


def _days_until_deadline() -> int:
    return max(0, (_DEADLINE - datetime.now(timezone.utc)).days)


def _compliance_for_user(google_sub: str) -> List[Dict[str, Any]]:
    """Return compliance results for all AI systems belonging to this user."""
    from .compliance_engine import compute_compliance
    systems = database.get_ai_systems(google_sub)
    stats   = database.get_audit_stats_for_system(google_sub)
    results = []
    for system in systems:
        try:
            compliance = compute_compliance(system, stats)
            results.append({
                "system_id":   system["system_id"],
                "system_name": system["system_name"],
                "company_name": system["company_name"],
                "risk_tier":   system["risk_tier"],
                "score":       compliance["overall_score"],
                "verdict":     compliance["verdict"],
                "articles":    compliance["articles"],
            })
        except Exception as e:
            logger.warning("Compliance check failed for system %s: %s", system.get("system_id"), e)
    return results


def send_welcome(user: Dict) -> bool:
    if database.was_notification_sent(user["google_sub"], "welcome", within_days=36500):
        return False  # only ever send once
    html = email_service.welcome_html(
        name=user["name"],
        unsubscribe_token=user["unsubscribe_token"] or "",
    )
    sent = email_service.send(user["email"], email_service.welcome_subject(), html)
    if sent:
        database.log_notification(user["google_sub"], "welcome", user["email"])
    return sent


def send_gap_reminders(user: Dict) -> int:
    """Send one gap reminder per system with unresolved FAIL/PARTIAL. Returns count sent."""
    sent_count = 0
    results = _compliance_for_user(user["google_sub"])

    for r in results:
        if r["verdict"] in ("ready", "prohibited"):
            continue  # nothing to remind about

        system_id = r["system_id"]
        if database.was_notification_sent(
            user["google_sub"], "gap_reminder", system_id=system_id, within_days=30
        ):
            continue

        articles   = r["articles"]
        fails      = [
            {"article": _ART_LABELS.get(k, k), "title": v["title"].replace("Article ?? — ", "").split(" — ", 1)[-1]}
            for k, v in articles.items() if v["status"] == "fail"
        ]
        partials   = [
            {"article": _ART_LABELS.get(k, k), "title": v["title"].split(" — ", 1)[-1]}
            for k, v in articles.items() if v["status"] == "partial"
        ]

        if not fails and not partials:
            continue

        # Estimate days unresolved from system created_at
        system_list = database.get_ai_systems(user["google_sub"])
        system      = next((s for s in system_list if s["system_id"] == system_id), {})
        created_at  = system.get("created_at", "")
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            days_unresolved = (datetime.now(timezone.utc) - created).days
        except Exception:
            days_unresolved = 0

        html = email_service.gap_reminder_html(
            name=user["name"],
            system_name=r["system_name"],
            company_name=r["company_name"],
            fails=fails,
            partials=partials,
            score=r["score"],
            days_unresolved=days_unresolved,
            unsubscribe_token=user["unsubscribe_token"] or "",
        )
        subject = email_service.gap_reminder_subject(
            r["system_name"], len(fails), len(partials)
        )
        if email_service.send(user["email"], subject, html):
            database.log_notification(
                user["google_sub"], "gap_reminder", user["email"], system_id=system_id
            )
            sent_count += 1

    return sent_count


def send_countdown(user: Dict) -> bool:
    """Send weekly EU AI Act countdown email if user has any high-risk systems."""
    if database.was_notification_sent(user["google_sub"], "countdown", within_days=7):
        return False

    results   = _compliance_for_user(user["google_sub"])
    high_risk = [r for r in results if r["risk_tier"] == "high"]
    if not high_risk:
        return False  # only send to users with high-risk systems

    days = _days_until_deadline()
    html = email_service.countdown_html(
        name=user["name"],
        days_remaining=days,
        systems=high_risk,
        unsubscribe_token=user["unsubscribe_token"] or "",
    )
    subject = email_service.countdown_subject(days)
    sent = email_service.send(user["email"], subject, html)
    if sent:
        database.log_notification(user["google_sub"], "countdown", user["email"])
    return sent


def run_all(dry_run: bool = False) -> Dict[str, int]:
    """
    Main entry point for the daily cron job.
    Returns counts of each notification type sent.
    """
    database.init_db()
    users_list = database.get_all_notification_users()

    totals = {"welcome": 0, "gap_reminder": 0, "countdown": 0, "users_checked": len(users_list)}
    logger.info("Notification run — %d users to check (dry_run=%s)", len(users_list), dry_run)

    for user in users_list:
        if dry_run:
            logger.info("DRY RUN — would process user %s", user["email"].split("@")[0] + "@…")
            continue

        try:
            if send_welcome(user):
                totals["welcome"] += 1
        except Exception as e:
            logger.error("Welcome failed for %s: %s", user["google_sub"], e)

        try:
            totals["gap_reminder"] += send_gap_reminders(user)
        except Exception as e:
            logger.error("Gap reminder failed for %s: %s", user["google_sub"], e)

        try:
            if send_countdown(user):
                totals["countdown"] += 1
        except Exception as e:
            logger.error("Countdown failed for %s: %s", user["google_sub"], e)

    logger.info("Notification run complete — %s", totals)
    return totals
