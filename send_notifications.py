#!/usr/bin/env python3
"""
Daily notification cron script — run via Railway cron or locally.

Railway cron setup (railway.toml):
  [[cron]]
  name = "daily-notifications"
  schedule = "0 9 * * *"          # 09:00 UTC every day
  command = "python send_notifications.py"

Local usage:
  python send_notifications.py            # live run
  python send_notifications.py --dry-run  # preview without sending
  python send_notifications.py --welcome-only   # only send welcome emails
"""

import argparse
import logging
import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Send Pragma notification emails")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent without actually sending")
    parser.add_argument("--welcome-only", action="store_true",
                        help="Only send welcome emails (skip gap reminders and countdown)")
    parser.add_argument("--user", metavar="EMAIL",
                        help="Only process this specific user email (for testing)")
    args = parser.parse_args()

    if not os.getenv("RESEND_API_KEY") and not args.dry_run:
        logger.error("RESEND_API_KEY is not set — run with --dry-run or set the env var")
        sys.exit(1)

    from backend.notifications import run_all
    from backend import database

    if args.user:
        # Single-user mode for testing
        database.init_db()
        all_users = database.get_all_notification_users()
        target    = next((u for u in all_users if u["email"] == args.user), None)
        if not target:
            logger.error("User not found: %s", args.user)
            sys.exit(1)
        from backend.notifications import send_welcome, send_gap_reminders, send_countdown
        logger.info("Processing single user: %s", args.user)
        if not args.dry_run:
            send_welcome(target)
            if not args.welcome_only:
                send_gap_reminders(target)
                send_countdown(target)
        else:
            logger.info("DRY RUN — would process %s", args.user)
        return

    totals = run_all(dry_run=args.dry_run)
    logger.info(
        "Done — users_checked=%d welcome=%d gap_reminder=%d countdown=%d",
        totals["users_checked"], totals["welcome"],
        totals["gap_reminder"], totals["countdown"],
    )


if __name__ == "__main__":
    main()
