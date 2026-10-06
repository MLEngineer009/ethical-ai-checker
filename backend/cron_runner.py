"""
Standalone cron runner — executes law agent + activates pending rules.

Railway cron setup (Settings → Cron Jobs):
  Schedule: 0 6 * * *
  Command:  python -m backend.cron_runner

Requires same env vars as the main backend:
  ANTHROPIC_API_KEY, DATABASE_URL, RESEND_API_KEY, ADMIN_EMAIL
"""

import logging
import sys
from pathlib import Path

# Load .env so local runs work without Railway injecting env vars
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [cron] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    from . import database, law_agent

    logger.info("Cron: initialising database")
    database.init_db()

    logger.info("Cron: running law agent sweep")
    stats = law_agent.run()
    logger.info("Cron: sweep complete — %s", stats)

    logger.info("Cron: activating pending rules")
    activated = law_agent.activate_pending()
    logger.info("Cron: activated %d rule(s)", activated)

    logger.info("Cron: done")


if __name__ == "__main__":
    main()
