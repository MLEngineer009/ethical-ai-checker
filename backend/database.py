"""SQLite metadata store — no PII, only aggregate request metadata."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

DB_PATH = Path(__file__).parent.parent / "data" / "metadata.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist, and migrate existing schemas."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                anon_id         TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                context_keys    TEXT NOT NULL,
                decision_words  INTEGER NOT NULL,
                provider        TEXT NOT NULL,
                confidence      REAL NOT NULL,
                risk_count      INTEGER NOT NULL,
                risk_categories TEXT NOT NULL,
                category        TEXT NOT NULL DEFAULT 'other'
            )
        """)
        # Migration: add category column to existing databases
        try:
            conn.execute("ALTER TABLE request_logs ADD COLUMN category TEXT NOT NULL DEFAULT 'other'")
        except Exception:
            pass  # column already exists
        conn.commit()


def anon_id(google_sub: str) -> str:
    """One-way hash of Google subject ID — not reversible, not PII."""
    return hashlib.sha256(f"ethical-ai:{google_sub}".encode()).hexdigest()[:16]


def log_request(
    google_sub: str,
    decision: str,
    context: Dict[str, Any],
    provider: str,
    confidence: float,
    risk_flags: List[str],
    category: str = "other",
) -> None:
    """Store metadata only — no decision text, no context values, no identity."""
    with _connect() as conn:
        conn.execute(
            """INSERT INTO request_logs
               (anon_id, timestamp, context_keys, decision_words, provider, confidence, risk_count, risk_categories, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                anon_id(google_sub),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(sorted(context.keys())),
                len(decision.split()),
                provider,
                round(confidence, 3),
                len(risk_flags),
                json.dumps(sorted(risk_flags)),
                category,
            ),
        )
        conn.commit()


def get_stats(google_sub: str) -> Dict[str, Any]:
    """Return aggregate stats for a user's session — no raw text."""
    aid = anon_id(google_sub)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM request_logs WHERE anon_id = ? ORDER BY timestamp DESC LIMIT 20",
            (aid,)
        ).fetchall()

    total = len(rows)
    if not total:
        return {"total_requests": 0, "history": []}

    history = [
        {
            "timestamp": r["timestamp"],
            "context_keys": json.loads(r["context_keys"]),
            "decision_words": r["decision_words"],
            "provider": r["provider"],
            "confidence": r["confidence"],
            "risk_count": r["risk_count"],
            "risk_categories": json.loads(r["risk_categories"]),
            "category": r["category"],
        }
        for r in rows
    ]
    return {"total_requests": total, "history": history}
