"""Database layer — SQLite for local dev/tests, PostgreSQL for production.

Set DATABASE_URL env var to switch to PostgreSQL:
  postgresql://user:password@host:port/dbname   (Railway sets this automatically)

Tables:
  request_logs      — one row per evaluate-decision call (metadata only, no PII)
  analysis_feedback — thumbs up/down on analyses; drives the Pragma model retraining flywheel
  waitlist          — email addresses from the landing page for follow-up
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


waitlist = Table(
    "waitlist", _meta,
    Column("id",        Integer, primary_key=True, autoincrement=True),
    Column("email",     String,  nullable=False, unique=True),
    Column("timestamp", String,  nullable=False),
)

organizations = Table(
    "organizations", _meta,
    Column("id",          Integer, primary_key=True, autoincrement=True),
    Column("name",        String,  nullable=False),
    Column("owner_sub",   String,  nullable=False),   # google_sub of creator
    Column("invite_code", String,  nullable=False, unique=True),
    Column("created_at",  String,  nullable=False),
)

org_members = Table(
    "org_members", _meta,
    Column("id",       Integer, primary_key=True, autoincrement=True),
    Column("org_id",   Integer, nullable=False),
    Column("anon_id",  String,  nullable=False),
    Column("role",     String,  nullable=False, server_default="member"),  # owner | member
    Column("joined_at", String, nullable=False),
)

audit_log = Table(
    "audit_log", _meta,
    Column("id",                Integer, primary_key=True, autoincrement=True),
    Column("anon_id",           String,  nullable=False),
    Column("timestamp",         String,  nullable=False),
    Column("input_hash",        String,  nullable=False),   # sha256(decision+context) — no PII
    Column("decision_words",    Integer, nullable=False),
    Column("category",          String,  nullable=False),
    Column("firewall_action",   String,  nullable=False),   # block|override_required|allow
    Column("confidence",        Float,   nullable=False),
    Column("risk_flags",        String,  nullable=False),   # JSON list
    Column("proxy_vars",        String,  nullable=False, server_default="[]"),  # JSON list of detected proxy fields
    Column("regulatory_refs",   String,  nullable=False, server_default="[]"),  # JSON list of triggered regulations
    Column("provider",          String,  nullable=False),
    Column("model_version",     String,  nullable=False, server_default="unknown"),
    Column("hitl_override",     Integer, nullable=False, server_default="0"),   # 1 if human overrode the verdict
    Column("hitl_reason",       String,  nullable=True),    # investigator's override reason
    Column("hitl_anon_id",      String,  nullable=True),    # who overrode it
)

api_keys = Table(
    "api_keys", _meta,
    Column("id",          Integer, primary_key=True, autoincrement=True),
    Column("anon_id",     String,  nullable=False),
    Column("key_hash",    String,  nullable=False, unique=True),
    Column("key_prefix",  String,  nullable=False),   # first 8 chars for display
    Column("label",       String,  nullable=False, server_default=""),
    Column("created_at",  String,  nullable=False),
    Column("last_used",   String,  nullable=True),
    Column("calls_total", Integer, nullable=False, server_default="0"),
    Column("calls_month", Integer, nullable=False, server_default="0"),
    Column("active",      Integer, nullable=False, server_default="1"),  # 1=active
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


def add_to_waitlist(email: str) -> bool:
    """
    Store an email address. Returns True if newly added, False if already exists.
    Email is stored as-is — this is explicit opt-in, not anonymous metadata.
    """
    try:
        with _engine.begin() as conn:
            conn.execute(waitlist.insert().values(
                email     = email.lower().strip(),
                timestamp = datetime.now(timezone.utc).isoformat(),
            ))
        return True
    except Exception:
        return False  # unique constraint violation = already signed up


def get_waitlist() -> List[Dict]:
    """Return all waitlist entries — for internal use only."""
    with _engine.connect() as conn:
        rows = conn.execute(
            waitlist.select().order_by(waitlist.c.id.desc())
        ).fetchall()
    return [{"email": r.email, "timestamp": r.timestamp} for r in rows]


def anon_id(google_sub: str) -> str:
    """One-way hash of the session subject — not reversible, not PII."""
    return hashlib.sha256(f"pragma:{google_sub}".encode()).hexdigest()[:16]


def log_audit(
    google_sub: str,
    decision: str,
    context: Dict[str, Any],
    firewall_action: str,
    confidence: float,
    risk_flags: List[str],
    proxy_vars: List[str],
    regulatory_refs: List[Dict],
    provider: str,
    category: str = "other",
    model_version: str = "unknown",
) -> int:
    """
    Immutable audit trail entry — one row per compliance evaluation.
    Stores input hash (not raw text), firewall verdict, proxy variable report,
    and regulatory refs triggered. Returns the audit log row ID.
    """
    input_hash = hashlib.sha256(
        f"{decision}:{json.dumps(context, sort_keys=True)}".encode()
    ).hexdigest()
    with _engine.begin() as conn:
        result = conn.execute(audit_log.insert().values(
            anon_id         = anon_id(google_sub),
            timestamp       = datetime.now(timezone.utc).isoformat(),
            input_hash      = input_hash,
            decision_words  = len(decision.split()),
            category        = category,
            firewall_action = firewall_action,
            confidence      = round(confidence, 3),
            risk_flags      = json.dumps(sorted(risk_flags)),
            proxy_vars      = json.dumps(proxy_vars),
            regulatory_refs = json.dumps([r.get("law", "") for r in regulatory_refs]),
            provider        = provider,
            model_version   = model_version,
            hitl_override   = 0,
        ))
        return result.inserted_primary_key[0]


def log_hitl_override(
    audit_log_id: int,
    investigator_sub: str,
    reason: str,
) -> None:
    """
    Record a human investigator override of the firewall verdict.
    Meets EU AI Act Article 14 human oversight requirements.
    """
    with _engine.begin() as conn:
        conn.execute(
            audit_log.update()
            .where(audit_log.c.id == audit_log_id)
            .values(
                hitl_override = 1,
                hitl_reason   = reason[:500],
                hitl_anon_id  = anon_id(investigator_sub),
            )
        )


def get_audit_log(google_sub: str, limit: int = 50) -> List[Dict]:
    """Return recent audit entries for a user, newest first."""
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        rows = conn.execute(
            audit_log.select()
            .where(audit_log.c.anon_id == aid)
            .order_by(audit_log.c.id.desc())
            .limit(limit)
        ).fetchall()
    return [
        {
            "id":             r.id,
            "timestamp":      r.timestamp,
            "category":       r.category,
            "firewall_action": r.firewall_action,
            "confidence":     r.confidence,
            "risk_flags":     json.loads(r.risk_flags or "[]"),
            "proxy_vars":     json.loads(r.proxy_vars or "[]"),
            "regulatory_refs": json.loads(r.regulatory_refs or "[]"),
            "hitl_override":  bool(r.hitl_override),
            "hitl_reason":    r.hitl_reason,
            "input_hash":     r.input_hash[:12] + "…",
        }
        for r in rows
    ]


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


# ── Org functions ──────────────────────────────────────────────────────────────

def create_org(name: str, owner_sub: str) -> Dict[str, Any]:
    """Create a new organization and make the creator the owner member."""
    import secrets
    invite_code = secrets.token_urlsafe(12)
    aid = anon_id(owner_sub)
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        result = conn.execute(organizations.insert().values(
            name=name, owner_sub=owner_sub,
            invite_code=invite_code, created_at=now,
        ))
        org_id = result.inserted_primary_key[0]
        conn.execute(org_members.insert().values(
            org_id=org_id, anon_id=aid, role="owner", joined_at=now,
        ))
    return {"org_id": org_id, "name": name, "invite_code": invite_code}


def get_org_by_invite(invite_code: str) -> Dict[str, Any] | None:
    with _engine.connect() as conn:
        row = conn.execute(
            organizations.select().where(organizations.c.invite_code == invite_code)
        ).fetchone()
    if not row:
        return None
    return {"org_id": row.id, "name": row.name, "owner_sub": row.owner_sub}


def join_org(org_id: int, google_sub: str) -> bool:
    """Add member to org. Returns False if already a member."""
    aid = anon_id(google_sub)
    try:
        with _engine.begin() as conn:
            existing = conn.execute(
                org_members.select()
                .where(org_members.c.org_id == org_id)
                .where(org_members.c.anon_id == aid)
            ).fetchone()
            if existing:
                return False
            conn.execute(org_members.insert().values(
                org_id=org_id, anon_id=aid, role="member",
                joined_at=datetime.now(timezone.utc).isoformat(),
            ))
        return True
    except Exception:
        return False


def get_my_orgs(google_sub: str) -> List[Dict]:
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        rows = conn.execute(
            org_members.join(organizations, org_members.c.org_id == organizations.c.id)
            .select().where(org_members.c.anon_id == aid)
        ).fetchall()
    return [
        {"org_id": r.org_id, "name": r.name, "role": r.role,
         "invite_code": r.invite_code if r.role == "owner" else None}
        for r in rows
    ]


def get_org_history(org_id: int, google_sub: str, limit: int = 50) -> List[Dict]:
    """Return recent request logs for all members of the org — caller must be a member."""
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        # Verify membership
        member = conn.execute(
            org_members.select()
            .where(org_members.c.org_id == org_id)
            .where(org_members.c.anon_id == aid)
        ).fetchone()
        if not member:
            return []
        # Get all member anon_ids
        members = conn.execute(
            org_members.select().where(org_members.c.org_id == org_id)
        ).fetchall()
        member_ids = [m.anon_id for m in members]
        rows = conn.execute(
            request_logs.select()
            .where(request_logs.c.anon_id.in_(member_ids))
            .order_by(request_logs.c.id.desc())
            .limit(limit)
        ).fetchall()
    return [
        {
            "timestamp":       r.timestamp,
            "category":        r.category,
            "decision_words":  r.decision_words,
            "provider":        r.provider,
            "confidence":      r.confidence,
            "risk_count":      r.risk_count,
            "risk_categories": json.loads(r.risk_categories),
            "is_self":         r.anon_id == aid,
        }
        for r in rows
    ]


# ── API key functions ──────────────────────────────────────────────────────────

def create_api_key(google_sub: str, label: str) -> Dict[str, Any]:
    """Generate a new API key. Returns the raw key (shown once only)."""
    import secrets
    raw_key = "pragma_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12]
    aid = anon_id(google_sub)
    with _engine.begin() as conn:
        result = conn.execute(api_keys.insert().values(
            anon_id=aid, key_hash=key_hash, key_prefix=key_prefix,
            label=label, created_at=datetime.now(timezone.utc).isoformat(),
        ))
    return {"key": raw_key, "key_prefix": key_prefix, "key_id": result.inserted_primary_key[0], "label": label}


def get_api_keys(google_sub: str) -> List[Dict]:
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        rows = conn.execute(
            api_keys.select().where(api_keys.c.anon_id == aid)
            .order_by(api_keys.c.id.desc())
        ).fetchall()
    return [
        {
            "key_id":      r.id,
            "key_prefix":  r.key_prefix,
            "label":       r.label,
            "created_at":  r.created_at,
            "last_used":   r.last_used,
            "calls_total": r.calls_total,
            "calls_month": r.calls_month,
            "active":      bool(r.active),
        }
        for r in rows
    ]


def revoke_api_key(key_id: int, google_sub: str) -> bool:
    aid = anon_id(google_sub)
    with _engine.begin() as conn:
        result = conn.execute(
            api_keys.update()
            .where(api_keys.c.id == key_id)
            .where(api_keys.c.anon_id == aid)
            .values(active=0)
        )
    return result.rowcount > 0


def verify_api_key(raw_key: str) -> Dict[str, Any] | None:
    """Verify an API key and increment usage counters. Returns anon_id or None."""
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        row = conn.execute(
            api_keys.select()
            .where(api_keys.c.key_hash == key_hash)
            .where(api_keys.c.active == 1)
        ).fetchone()
        if not row:
            return None
        conn.execute(
            api_keys.update()
            .where(api_keys.c.id == row.id)
            .values(
                last_used=now,
                calls_total=row.calls_total + 1,
                calls_month=row.calls_month + 1,
            )
        )
    return {"anon_id": row.anon_id, "key_id": row.id}
