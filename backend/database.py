"""Database layer — SQLite for local dev/tests, PostgreSQL for production.

Set DATABASE_URL env var to switch to PostgreSQL:
  postgresql://user:password@host:port/dbname   (Railway sets this automatically)

Tables:
  request_logs      — one row per evaluate-decision call (metadata only, no PII)
  analysis_feedback — thumbs up/down on analyses; drives the Pragma model retraining flywheel
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import (
    Column, Float, Integer, String,
    MetaData, Table, create_engine, inspect, text,
)

# ── Engine setup ──────────────────────────────────────────────────────────────

def _make_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        # Railway uses postgres:// — SQLAlchemy 2.x requires postgresql://
        return url.replace("postgres://", "postgresql://", 1)
    # Local dev / tests: SQLite file
    data_dir = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
    data_dir.mkdir(exist_ok=True)
    return f"sqlite:///{data_dir}/metadata.db"


_engine = create_engine(_make_url(), pool_pre_ping=True)
_meta   = MetaData()

# ── Tables ────────────────────────────────────────────────────────────────────

request_logs = Table(
    "request_logs", _meta,
    Column("id",              Integer, primary_key=True, autoincrement=True),
    Column("anon_id",         String,  nullable=False),
    Column("timestamp",       String,  nullable=False),
    Column("context_keys",    String,  nullable=False),
    Column("decision_words",  Integer, nullable=False),
    Column("provider",        String,  nullable=False),
    Column("confidence",      Float,   nullable=False),
    Column("risk_count",      Integer, nullable=False),
    Column("risk_categories", String,  nullable=False),
    Column("category",        String,  nullable=False, server_default="other"),
)


analysis_feedback = Table(
    "analysis_feedback", _meta,
    Column("id",              Integer, primary_key=True, autoincrement=True),
    Column("anon_id",         String,  nullable=False),
    Column("timestamp",       String,  nullable=False),
    Column("rating",          Integer, nullable=False),   # 1 = thumbs up, -1 = thumbs down
    Column("category",        String,  nullable=False, server_default="other"),
    Column("provider",        String,  nullable=False),   # which model produced this
    Column("model_version",   String,  nullable=False, server_default="unknown"),
    Column("confidence",      Float,   nullable=False),
    Column("risk_categories", String,  nullable=False),   # JSON list
)


# ── Public API ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    _meta.create_all(_engine, checkfirst=True)
    # Migration: add category column to pre-existing request_logs tables
    insp = inspect(_engine)
    cols = [c["name"] for c in insp.get_columns("request_logs")]
    if "category" not in cols:
        with _engine.begin() as conn:
            conn.execute(text("ALTER TABLE request_logs ADD COLUMN category VARCHAR DEFAULT 'other'"))


def anon_id(google_sub: str) -> str:
    """One-way hash of the session subject — not reversible, not PII."""
    return hashlib.sha256(f"pragma:{google_sub}".encode()).hexdigest()[:16]


def log_request(
    google_sub: str,
    decision: str,
    context: Dict[str, Any],
    provider: str,
    confidence: float,
    risk_flags: List[str],
    category: str = "other",
) -> None:
    """Store anonymous metadata only — no decision text, no context values."""
    with _engine.begin() as conn:
        conn.execute(request_logs.insert().values(
            anon_id         = anon_id(google_sub),
            timestamp       = datetime.now(timezone.utc).isoformat(),
            context_keys    = json.dumps(sorted(context.keys())),
            decision_words  = len(decision.split()),
            provider        = provider,
            confidence      = round(confidence, 3),
            risk_count      = len(risk_flags),
            risk_categories = json.dumps(sorted(risk_flags)),
            category        = category,
        ))


def log_feedback(
    google_sub: str,
    rating: int,
    category: str,
    provider: str,
    model_version: str,
    confidence: float,
    risk_flags: List[str],
) -> None:
    """
    Store a thumbs up (rating=1) or thumbs down (rating=-1) on an analysis.
    Drives the Pragma model retraining flywheel — no decision text or context stored.
    """
    if rating not in (1, -1):
        raise ValueError("rating must be 1 (up) or -1 (down)")
    with _engine.begin() as conn:
        conn.execute(analysis_feedback.insert().values(
            anon_id         = anon_id(google_sub),
            timestamp       = datetime.now(timezone.utc).isoformat(),
            rating          = rating,
            category        = category,
            provider        = provider,
            model_version   = model_version,
            confidence      = round(confidence, 3),
            risk_categories = json.dumps(sorted(risk_flags)),
        ))


def get_feedback_stats() -> Dict[str, Any]:
    """
    Aggregate feedback by category and provider — used by the flywheel script
    to identify which categories need more training data.
    """
    with _engine.connect() as conn:
        rows = conn.execute(analysis_feedback.select()).fetchall()

    if not rows:
        return {"total": 0, "by_category": {}, "by_provider": {}}

    by_category: Dict[str, Dict] = {}
    by_provider: Dict[str, Dict] = {}

    for r in rows:
        # Category breakdown
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"up": 0, "down": 0}
        if r.rating == 1:
            by_category[cat]["up"] += 1
        else:
            by_category[cat]["down"] += 1

        # Provider breakdown
        prov = r.provider
        if prov not in by_provider:
            by_provider[prov] = {"up": 0, "down": 0}
        if r.rating == 1:
            by_provider[prov]["up"] += 1
        else:
            by_provider[prov]["down"] += 1

    # Compute approval rate per category
    for cat, counts in by_category.items():
        total = counts["up"] + counts["down"]
        counts["approval_rate"] = round(counts["up"] / total, 3) if total else 0.0
        counts["total"] = total

    for prov, counts in by_provider.items():
        total = counts["up"] + counts["down"]
        counts["approval_rate"] = round(counts["up"] / total, 3) if total else 0.0
        counts["total"] = total

    return {
        "total": len(rows),
        "by_category": by_category,
        "by_provider": by_provider,
    }


def get_stats(google_sub: str) -> Dict[str, Any]:
    """Return aggregate usage stats — no raw text, no PII."""
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        rows = conn.execute(
            request_logs.select()
            .where(request_logs.c.anon_id == aid)
            .order_by(request_logs.c.id.desc())
            .limit(20)
        ).fetchall()

    if not rows:
        return {"total_requests": 0, "history": []}

    history = [
        {
            "timestamp":       r.timestamp,
            "context_keys":    json.loads(r.context_keys),
            "decision_words":  r.decision_words,
            "provider":        r.provider,
            "confidence":      r.confidence,
            "risk_count":      r.risk_count,
            "risk_categories": json.loads(r.risk_categories),
            "category":        r.category,
        }
        for r in rows
    ]
    return {"total_requests": len(rows), "history": history}
