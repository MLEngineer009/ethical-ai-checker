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
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

from sqlalchemy import (
    Column, Float, Integer, String,
    MetaData, Table, create_engine, func, inspect, select, text,
)

# ── Engine setup ──────────────────────────────────────────────────────────────

def _make_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        # Railway uses postgres:// — SQLAlchemy 2.x requires postgresql://
        url = url.replace("postgres://", "postgresql://", 1)
        logger.info("Database: PostgreSQL (Railway)")
        return url
    # Local dev / tests: SQLite file
    data_dir = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "metadata.db"
    logger.info("Database: SQLite — %s", db_path)
    return f"sqlite:///{db_path}"


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

# ── EU AI Act Data Lineage ─────────────────────────────────────────────────────

ai_systems = Table(
    "ai_systems", _meta,
    # ── Core profile (Arts 10, 11) ──────────────────────────────────────────
    Column("id",                    Integer, primary_key=True, autoincrement=True),
    Column("anon_id",               String,  nullable=False),
    Column("system_name",           String,  nullable=False),
    Column("company_name",          String,  nullable=False),
    Column("risk_tier",             String,  nullable=False),   # minimal|limited|high|unacceptable
    Column("use_case",              String,  nullable=False),
    Column("model_version",         String,  nullable=False, server_default="unknown"),
    Column("training_data_sources", String,  nullable=False, server_default="[]"),  # JSON list
    Column("intended_purpose",      String,  nullable=False, server_default=""),
    Column("geographic_scope",      String,  nullable=False, server_default=""),
    # ── Declarative article checks ──────────────────────────────────────────
    Column("art4_literacy_training",    Integer, nullable=False, server_default="0"),  # bool
    Column("art6_annex_category",       String,  nullable=False, server_default=""),   # Annex III category
    Column("art15_accuracy_metric",     String,  nullable=False, server_default=""),   # e.g. "F1=0.94"
    Column("art15_robustness_tested",   Integer, nullable=False, server_default="0"),  # bool
    Column("art17_qms_documented",      Integer, nullable=False, server_default="0"),  # bool
    Column("art25_instructions_provided", Integer, nullable=False, server_default="0"),# bool
    Column("art25_monitoring_active",   Integer, nullable=False, server_default="0"),  # bool
    Column("art27_fria_conducted",      Integer, nullable=False, server_default="0"),  # bool
    Column("art30_eu_db_registered",    Integer, nullable=False, server_default="0"),  # bool
    Column("art30_registration_number", String,  nullable=False, server_default=""),
    Column("art33_conformity_type",     String,  nullable=False, server_default=""),   # self-assessment|third-party|pending
    # Evidence notes + dates for the 7 boolean-only article declarations
    Column("art4_literacy_training_evidence_notes",      String, nullable=False, server_default=""),
    Column("art4_literacy_training_evidence_date",       String, nullable=False, server_default=""),
    Column("art17_qms_documented_evidence_notes",        String, nullable=False, server_default=""),
    Column("art17_qms_documented_evidence_date",         String, nullable=False, server_default=""),
    Column("art25_instructions_provided_evidence_notes", String, nullable=False, server_default=""),
    Column("art25_instructions_provided_evidence_date",  String, nullable=False, server_default=""),
    Column("art25_monitoring_active_evidence_notes",     String, nullable=False, server_default=""),
    Column("art25_monitoring_active_evidence_date",      String, nullable=False, server_default=""),
    Column("art27_fria_conducted_evidence_notes",        String, nullable=False, server_default=""),
    Column("art27_fria_conducted_evidence_date",         String, nullable=False, server_default=""),
    Column("art30_eu_db_registered_evidence_notes",      String, nullable=False, server_default=""),
    Column("art30_eu_db_registered_evidence_date",       String, nullable=False, server_default=""),
    Column("art33_conformity_type_evidence_notes",       String, nullable=False, server_default=""),
    Column("art33_conformity_type_evidence_date",        String, nullable=False, server_default=""),
    Column("created_at",               String,  nullable=False),
    Column("updated_at",               String,  nullable=False),
)

compliance_certificates = Table(
    "compliance_certificates", _meta,
    Column("id",                  Integer, primary_key=True, autoincrement=True),
    Column("certificate_id",      String,  nullable=False, unique=True),  # UUID
    Column("ai_system_id",        Integer, nullable=False),
    Column("anon_id",             String,  nullable=False),
    Column("issued_at",           String,  nullable=False),
    Column("valid_until",         String,  nullable=False),          # 1 year
    Column("overall_score",       Float,   nullable=False),          # 0.0–1.0
    Column("articles_status",     String,  nullable=False),          # JSON dict
    Column("total_evaluations",   Integer, nullable=False, server_default="0"),
    Column("hitl_overrides",      Integer, nullable=False, server_default="0"),
    Column("proxy_vars_caught",   Integer, nullable=False, server_default="0"),
)

subscriptions = Table(
    "subscriptions", _meta,
    Column("id",                      Integer, primary_key=True, autoincrement=True),
    Column("anon_id",                 String,  nullable=False, unique=True),
    Column("plan",                    String,  nullable=False, server_default="free"),  # free|growth|enterprise
    Column("status",                  String,  nullable=False, server_default="active"),  # active|past_due|canceled
    Column("stripe_customer_id",      String,  nullable=True),
    Column("stripe_subscription_id",  String,  nullable=True),
    Column("current_period_end",      String,  nullable=True),  # ISO timestamp
    Column("created_at",              String,  nullable=False),
    Column("updated_at",              String,  nullable=False),
)

users = Table(
    "users", _meta,
    Column("id",                    Integer, primary_key=True, autoincrement=True),
    Column("google_sub",            String,  nullable=False, unique=True),
    Column("email",                 String,  nullable=False),
    Column("name",                  String,  nullable=False),
    Column("email_notifications",   Integer, nullable=False, server_default="1"),  # 1=on, 0=off
    Column("unsubscribe_token",     String,  nullable=True),   # one-click unsubscribe
    Column("created_at",            String,  nullable=False),
    Column("last_seen_at",          String,  nullable=False),
)

notification_log = Table(
    "notification_log", _meta,
    Column("id",                Integer, primary_key=True, autoincrement=True),
    Column("google_sub",        String,  nullable=False),
    Column("notification_type", String,  nullable=False),  # welcome|gap_reminder|countdown|recheck
    Column("system_id",         Integer, nullable=True),
    Column("email",             String,  nullable=False),
    Column("sent_at",           String,  nullable=False),
)


# ── Public API ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    _meta.create_all(_engine, checkfirst=True)
    insp = inspect(_engine)

    # Migration: request_logs.category
    cols = [c["name"] for c in insp.get_columns("request_logs")]
    if "category" not in cols:
        logger.info("Migration: adding request_logs.category column")
        with _engine.begin() as conn:
            conn.execute(text("ALTER TABLE request_logs ADD COLUMN category VARCHAR DEFAULT 'other'"))

    # Migration: ai_systems declarative article columns
    if "ai_systems" in insp.get_table_names():
        ai_cols = {c["name"] for c in insp.get_columns("ai_systems")}
        new_cols = [
            ("art4_literacy_training",     "INTEGER DEFAULT 0"),
            ("art6_annex_category",        "VARCHAR DEFAULT ''"),
            ("art15_accuracy_metric",      "VARCHAR DEFAULT ''"),
            ("art15_robustness_tested",    "INTEGER DEFAULT 0"),
            ("art17_qms_documented",       "INTEGER DEFAULT 0"),
            ("art25_instructions_provided","INTEGER DEFAULT 0"),
            ("art25_monitoring_active",    "INTEGER DEFAULT 0"),
            ("art27_fria_conducted",       "INTEGER DEFAULT 0"),
            ("art30_eu_db_registered",     "INTEGER DEFAULT 0"),
            ("art30_registration_number",  "VARCHAR DEFAULT ''"),
            ("art33_conformity_type",      "VARCHAR DEFAULT ''"),
            # Evidence columns (v2 — pass/partial/fail distinction)
            ("art4_literacy_training_evidence_notes",      "VARCHAR DEFAULT ''"),
            ("art4_literacy_training_evidence_date",       "VARCHAR DEFAULT ''"),
            ("art17_qms_documented_evidence_notes",        "VARCHAR DEFAULT ''"),
            ("art17_qms_documented_evidence_date",         "VARCHAR DEFAULT ''"),
            ("art25_instructions_provided_evidence_notes", "VARCHAR DEFAULT ''"),
            ("art25_instructions_provided_evidence_date",  "VARCHAR DEFAULT ''"),
            ("art25_monitoring_active_evidence_notes",     "VARCHAR DEFAULT ''"),
            ("art25_monitoring_active_evidence_date",      "VARCHAR DEFAULT ''"),
            ("art27_fria_conducted_evidence_notes",        "VARCHAR DEFAULT ''"),
            ("art27_fria_conducted_evidence_date",         "VARCHAR DEFAULT ''"),
            ("art30_eu_db_registered_evidence_notes",      "VARCHAR DEFAULT ''"),
            ("art30_eu_db_registered_evidence_date",       "VARCHAR DEFAULT ''"),
            ("art33_conformity_type_evidence_notes",       "VARCHAR DEFAULT ''"),
            ("art33_conformity_type_evidence_date",        "VARCHAR DEFAULT ''"),
        ]
        _SAFE_COL = re.compile(r'^[a-z_][a-z0-9_]*$')
        with _engine.begin() as conn:
            for col_name, col_def in new_cols:
                if col_name not in ai_cols:
                    if not _SAFE_COL.match(col_name):
                        logger.error("Migration aborted — unsafe column name: %r", col_name)
                        continue
                    logger.info("Migration: adding ai_systems.%s column", col_name)
                    conn.execute(text(f"ALTER TABLE ai_systems ADD COLUMN {col_name} {col_def}"))
    # Migration: users.unsubscribe_token (added after initial users table)
    if "users" in insp.get_table_names():
        user_cols = {c["name"] for c in insp.get_columns("users")}
        if "unsubscribe_token" not in user_cols:
            with _engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN unsubscribe_token VARCHAR"))

    logger.info("Database schema up to date")


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
        logger.info("Waitlist signup — email=%s", email.split("@")[0] + "@…")
        return True
    except Exception:
        logger.debug("Waitlist duplicate — email already registered")
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
    try:
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
            row_id = result.inserted_primary_key[0]
        logger.debug("Audit log entry created — id=%d action=%s", row_id, firewall_action)
        return row_id
    except Exception:
        logger.exception("Failed to write audit log entry — action=%s category=%s", firewall_action, category)
        raise


def log_hitl_override(
    audit_log_id: int,
    investigator_sub: str,
    reason: str,
    google_sub: str = "",
) -> bool:
    """
    Record a human investigator override of the firewall verdict.
    Meets EU AI Act Article 14 human oversight requirements.

    Now enforces ownership: only the user who created the audit entry may
    override it. Returns True on success, False if not found or not owned.
    """
    with _engine.begin() as conn:
        row = conn.execute(
            audit_log.select().where(audit_log.c.id == audit_log_id)
        ).fetchone()
        if not row:
            return False
        if row.anon_id != anon_id(google_sub):
            return False
        conn.execute(
            audit_log.update()
            .where(audit_log.c.id == audit_log_id)
            .values(
                hitl_override = 1,
                hitl_reason   = reason[:500],
                hitl_anon_id  = anon_id(investigator_sub),
            )
        )
    return True


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


def count_evaluations(google_sub: str) -> int:
    """Count the number of evaluations made by a user (from request_logs)."""
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        result = conn.execute(
            select(func.count()).select_from(request_logs).where(request_logs.c.anon_id == aid)
        )
        return result.scalar() or 0


def count_evaluations_this_month(google_sub: str) -> int:
    """Count evaluations made by a user in the current calendar month."""
    aid = anon_id(google_sub)
    month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
    with _engine.connect() as conn:
        result = conn.execute(
            select(func.count()).select_from(request_logs).where(
                request_logs.c.anon_id == aid,
                request_logs.c.timestamp.like(f"{month_prefix}%"),
            )
        )
        return result.scalar() or 0


# ── Subscription / billing ─────────────────────────────────────────────────────

PLAN_LIMITS = {
    "free":       100,
    "growth":     2000,
    "enterprise": None,   # unlimited
}


def get_subscription(google_sub: str) -> Dict[str, Any]:
    """Return the user's current subscription. Creates a free record if none exists."""
    aid = anon_id(google_sub)
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        row = conn.execute(
            subscriptions.select().where(subscriptions.c.anon_id == aid)
        ).fetchone()
        if not row:
            conn.execute(subscriptions.insert().values(
                anon_id=aid, plan="free", status="active", created_at=now, updated_at=now,
            ))
            return {"plan": "free", "status": "active", "stripe_customer_id": None,
                    "stripe_subscription_id": None, "current_period_end": None,
                    "evals_this_month": 0, "eval_limit": PLAN_LIMITS["free"]}
    evals = count_evaluations_this_month(google_sub)
    limit = PLAN_LIMITS.get(row.plan, 100)
    return {
        "plan":                   row.plan,
        "status":                 row.status,
        "stripe_customer_id":     row.stripe_customer_id,
        "stripe_subscription_id": row.stripe_subscription_id,
        "current_period_end":     row.current_period_end,
        "evals_this_month":       evals,
        "eval_limit":             limit,
    }


def upsert_subscription(
    anon_id_val: str,
    plan: str,
    status: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    current_period_end: str,
) -> None:
    """Create or update subscription record — called from Stripe webhook."""
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        existing = conn.execute(
            subscriptions.select().where(subscriptions.c.anon_id == anon_id_val)
        ).fetchone()
        if existing:
            conn.execute(
                subscriptions.update()
                .where(subscriptions.c.anon_id == anon_id_val)
                .values(plan=plan, status=status, stripe_customer_id=stripe_customer_id,
                        stripe_subscription_id=stripe_subscription_id,
                        current_period_end=current_period_end, updated_at=now)
            )
        else:
            conn.execute(subscriptions.insert().values(
                anon_id=anon_id_val, plan=plan, status=status,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                current_period_end=current_period_end,
                created_at=now, updated_at=now,
            ))
    logger.info("Subscription upserted — anon_id=%s plan=%s status=%s", anon_id_val[:8], plan, status)


def get_anon_id_by_stripe_customer(stripe_customer_id: str) -> str | None:
    """Look up anon_id from a Stripe customer ID — used in webhook handlers."""
    with _engine.connect() as conn:
        row = conn.execute(
            subscriptions.select().where(subscriptions.c.stripe_customer_id == stripe_customer_id)
        ).fetchone()
    return row.anon_id if row else None


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
        logger.info("User joined org — org_id=%d", org_id)
        return True
    except Exception:
        logger.exception("Failed to add member to org — org_id=%d", org_id)
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


# ── AI System (EU AI Act Data Lineage) ────────────────────────────────────────

def create_ai_system(
    google_sub: str,
    system_name: str,
    company_name: str,
    risk_tier: str,
    use_case: str,
    model_version: str = "unknown",
    training_data_sources: List[str] = [],
    intended_purpose: str = "",
    geographic_scope: str = "",
    # Declarative article fields
    art4_literacy_training: bool = False,
    art6_annex_category: str = "",
    art15_accuracy_metric: str = "",
    art15_robustness_tested: bool = False,
    art17_qms_documented: bool = False,
    art25_instructions_provided: bool = False,
    art25_monitoring_active: bool = False,
    art27_fria_conducted: bool = False,
    art30_eu_db_registered: bool = False,
    art30_registration_number: str = "",
    art33_conformity_type: str = "",
    # Evidence notes + dates
    art4_literacy_training_evidence_notes: str = "",
    art4_literacy_training_evidence_date: str = "",
    art17_qms_documented_evidence_notes: str = "",
    art17_qms_documented_evidence_date: str = "",
    art25_instructions_provided_evidence_notes: str = "",
    art25_instructions_provided_evidence_date: str = "",
    art25_monitoring_active_evidence_notes: str = "",
    art25_monitoring_active_evidence_date: str = "",
    art27_fria_conducted_evidence_notes: str = "",
    art27_fria_conducted_evidence_date: str = "",
    art30_eu_db_registered_evidence_notes: str = "",
    art30_eu_db_registered_evidence_date: str = "",
    art33_conformity_type_evidence_notes: str = "",
    art33_conformity_type_evidence_date: str = "",
) -> Dict[str, Any]:
    aid = anon_id(google_sub)
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        result = conn.execute(ai_systems.insert().values(
            anon_id=aid,
            system_name=system_name,
            company_name=company_name,
            risk_tier=risk_tier,
            use_case=use_case,
            model_version=model_version,
            training_data_sources=json.dumps(training_data_sources),
            intended_purpose=intended_purpose,
            geographic_scope=geographic_scope,
            art4_literacy_training=int(art4_literacy_training),
            art6_annex_category=art6_annex_category,
            art15_accuracy_metric=art15_accuracy_metric,
            art15_robustness_tested=int(art15_robustness_tested),
            art17_qms_documented=int(art17_qms_documented),
            art25_instructions_provided=int(art25_instructions_provided),
            art25_monitoring_active=int(art25_monitoring_active),
            art27_fria_conducted=int(art27_fria_conducted),
            art30_eu_db_registered=int(art30_eu_db_registered),
            art30_registration_number=art30_registration_number,
            art33_conformity_type=art33_conformity_type,
            art4_literacy_training_evidence_notes=art4_literacy_training_evidence_notes,
            art4_literacy_training_evidence_date=art4_literacy_training_evidence_date,
            art17_qms_documented_evidence_notes=art17_qms_documented_evidence_notes,
            art17_qms_documented_evidence_date=art17_qms_documented_evidence_date,
            art25_instructions_provided_evidence_notes=art25_instructions_provided_evidence_notes,
            art25_instructions_provided_evidence_date=art25_instructions_provided_evidence_date,
            art25_monitoring_active_evidence_notes=art25_monitoring_active_evidence_notes,
            art25_monitoring_active_evidence_date=art25_monitoring_active_evidence_date,
            art27_fria_conducted_evidence_notes=art27_fria_conducted_evidence_notes,
            art27_fria_conducted_evidence_date=art27_fria_conducted_evidence_date,
            art30_eu_db_registered_evidence_notes=art30_eu_db_registered_evidence_notes,
            art30_eu_db_registered_evidence_date=art30_eu_db_registered_evidence_date,
            art33_conformity_type_evidence_notes=art33_conformity_type_evidence_notes,
            art33_conformity_type_evidence_date=art33_conformity_type_evidence_date,
            created_at=now,
            updated_at=now,
        ))
    system_id = result.inserted_primary_key[0]
    logger.info("AI system created — id=%d name=%r risk_tier=%s", system_id, system_name, risk_tier)
    return {"system_id": system_id, "system_name": system_name, "company_name": company_name}


def get_ai_systems(google_sub: str) -> List[Dict]:
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        rows = conn.execute(
            ai_systems.select()
            .where(ai_systems.c.anon_id == aid)
            .order_by(ai_systems.c.id.desc())
        ).fetchall()
    return [
        {
            "system_id":            r.id,
            "system_name":          r.system_name,
            "company_name":         r.company_name,
            "risk_tier":            r.risk_tier,
            "use_case":             r.use_case,
            "model_version":        r.model_version,
            "training_data_sources": json.loads(r.training_data_sources or "[]"),
            "intended_purpose":     r.intended_purpose,
            "geographic_scope":     r.geographic_scope,
            "created_at":           r.created_at,
        }
        for r in rows
    ]


def get_ai_system(system_id: int, google_sub: str) -> Dict | None:
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        row = conn.execute(
            ai_systems.select()
            .where(ai_systems.c.id == system_id)
            .where(ai_systems.c.anon_id == aid)
        ).fetchone()
    if not row:
        return None
    return {
        "system_id":            row.id,
        "system_name":          row.system_name,
        "company_name":         row.company_name,
        "risk_tier":            row.risk_tier,
        "use_case":             row.use_case,
        "model_version":        row.model_version,
        "training_data_sources": json.loads(row.training_data_sources or "[]"),
        "intended_purpose":     row.intended_purpose,
        "geographic_scope":     row.geographic_scope,
        "art4_literacy_training":     bool(getattr(row, "art4_literacy_training", 0)),
        "art6_annex_category":        getattr(row, "art6_annex_category", "") or "",
        "art15_accuracy_metric":      getattr(row, "art15_accuracy_metric", "") or "",
        "art15_robustness_tested":    bool(getattr(row, "art15_robustness_tested", 0)),
        "art17_qms_documented":       bool(getattr(row, "art17_qms_documented", 0)),
        "art25_instructions_provided":bool(getattr(row, "art25_instructions_provided", 0)),
        "art25_monitoring_active":    bool(getattr(row, "art25_monitoring_active", 0)),
        "art27_fria_conducted":       bool(getattr(row, "art27_fria_conducted", 0)),
        "art30_eu_db_registered":     bool(getattr(row, "art30_eu_db_registered", 0)),
        "art30_registration_number":  getattr(row, "art30_registration_number", "") or "",
        "art33_conformity_type":      getattr(row, "art33_conformity_type", "") or "",
        "art4_literacy_training_evidence_notes":      getattr(row, "art4_literacy_training_evidence_notes", "") or "",
        "art4_literacy_training_evidence_date":       getattr(row, "art4_literacy_training_evidence_date", "") or "",
        "art17_qms_documented_evidence_notes":        getattr(row, "art17_qms_documented_evidence_notes", "") or "",
        "art17_qms_documented_evidence_date":         getattr(row, "art17_qms_documented_evidence_date", "") or "",
        "art25_instructions_provided_evidence_notes": getattr(row, "art25_instructions_provided_evidence_notes", "") or "",
        "art25_instructions_provided_evidence_date":  getattr(row, "art25_instructions_provided_evidence_date", "") or "",
        "art25_monitoring_active_evidence_notes":     getattr(row, "art25_monitoring_active_evidence_notes", "") or "",
        "art25_monitoring_active_evidence_date":      getattr(row, "art25_monitoring_active_evidence_date", "") or "",
        "art27_fria_conducted_evidence_notes":        getattr(row, "art27_fria_conducted_evidence_notes", "") or "",
        "art27_fria_conducted_evidence_date":         getattr(row, "art27_fria_conducted_evidence_date", "") or "",
        "art30_eu_db_registered_evidence_notes":      getattr(row, "art30_eu_db_registered_evidence_notes", "") or "",
        "art30_eu_db_registered_evidence_date":       getattr(row, "art30_eu_db_registered_evidence_date", "") or "",
        "art33_conformity_type_evidence_notes":       getattr(row, "art33_conformity_type_evidence_notes", "") or "",
        "art33_conformity_type_evidence_date":        getattr(row, "art33_conformity_type_evidence_date", "") or "",
        "created_at":           row.created_at,
    }


def get_audit_stats_for_system(google_sub: str) -> Dict[str, Any]:
    """Aggregate stats from audit_log used to drive the compliance checklist."""
    aid = anon_id(google_sub)
    with _engine.connect() as conn:
        rows = conn.execute(
            audit_log.select().where(audit_log.c.anon_id == aid)
        ).fetchall()
    if not rows:
        return {"total": 0, "hitl_overrides": 0, "proxy_vars_caught": 0,
                "has_regulatory_refs": False, "has_risk_flags": False, "categories": set()}
    total = len(rows)
    hitl = sum(1 for r in rows if r.hitl_override)
    proxy = sum(len(json.loads(r.proxy_vars or "[]")) for r in rows)
    has_reg = any(json.loads(r.regulatory_refs or "[]") for r in rows)
    has_flags = any(json.loads(r.risk_flags or "[]") for r in rows)
    cats = {r.category for r in rows}
    return {
        "total":              total,
        "hitl_overrides":     hitl,
        "proxy_vars_caught":  proxy,
        "has_regulatory_refs": has_reg,
        "has_risk_flags":     has_flags,
        "categories":         list(cats),
    }


def save_certificate(
    google_sub: str,
    ai_system_id: int,
    certificate_id: str,
    overall_score: float,
    articles_status: Dict,
    total_evaluations: int,
    hitl_overrides: int,
    proxy_vars_caught: int,
) -> None:
    aid = anon_id(google_sub)
    now = datetime.now(timezone.utc)
    valid_until = now.replace(year=now.year + 1).isoformat()
    with _engine.begin() as conn:
        conn.execute(compliance_certificates.insert().values(
            certificate_id=certificate_id,
            ai_system_id=ai_system_id,
            anon_id=aid,
            issued_at=now.isoformat(),
            valid_until=valid_until,
            overall_score=round(overall_score, 3),
            articles_status=json.dumps(articles_status),
            total_evaluations=total_evaluations,
            hitl_overrides=hitl_overrides,
            proxy_vars_caught=proxy_vars_caught,
        ))


# ── User profiles & notifications ─────────────────────────────────────────────

def upsert_user(google_sub: str, email: str, name: str) -> None:
    """Create or update user profile. Called on every login."""
    import secrets as _secrets
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        existing = conn.execute(
            users.select().where(users.c.google_sub == google_sub)
        ).fetchone()
        if existing:
            conn.execute(
                users.update()
                .where(users.c.google_sub == google_sub)
                .values(name=name, last_seen_at=now)
            )
        else:
            conn.execute(users.insert().values(
                google_sub=google_sub,
                email=email,
                name=name,
                email_notifications=1,
                unsubscribe_token=_secrets.token_hex(16),
                created_at=now,
                last_seen_at=now,
            ))


def get_user_by_sub(google_sub: str) -> Dict | None:
    with _engine.connect() as conn:
        row = conn.execute(
            users.select().where(users.c.google_sub == google_sub)
        ).fetchone()
    if not row:
        return None
    return {
        "google_sub":           row.google_sub,
        "email":                row.email,
        "name":                 row.name,
        "email_notifications":  bool(row.email_notifications),
        "unsubscribe_token":    row.unsubscribe_token,
        "created_at":           row.created_at,
        "last_seen_at":         row.last_seen_at,
    }


def get_user_by_unsubscribe_token(token: str) -> Dict | None:
    with _engine.connect() as conn:
        row = conn.execute(
            users.select().where(users.c.unsubscribe_token == token)
        ).fetchone()
    if not row:
        return None
    return {"google_sub": row.google_sub, "email": row.email, "name": row.name}


def set_email_notifications(google_sub: str, enabled: bool) -> None:
    with _engine.begin() as conn:
        conn.execute(
            users.update()
            .where(users.c.google_sub == google_sub)
            .values(email_notifications=1 if enabled else 0)
        )


def get_all_notification_users() -> List[Dict]:
    """Return all users with email notifications enabled and a valid email."""
    with _engine.connect() as conn:
        rows = conn.execute(
            users.select()
            .where(users.c.email_notifications == 1)
            .where(users.c.email != "")
        ).fetchall()
    return [
        {
            "google_sub":        r.google_sub,
            "email":             r.email,
            "name":              r.name,
            "unsubscribe_token": r.unsubscribe_token,
        }
        for r in rows
    ]


def was_notification_sent(google_sub: str, notification_type: str,
                          system_id: int | None = None,
                          within_days: int = 30) -> bool:
    """Return True if this notification type was already sent recently."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
    with _engine.connect() as conn:
        q = notification_log.select().where(
            notification_log.c.google_sub == google_sub,
            notification_log.c.notification_type == notification_type,
            notification_log.c.sent_at >= cutoff,
        )
        if system_id is not None:
            q = q.where(notification_log.c.system_id == system_id)
        row = conn.execute(q).fetchone()
    return row is not None


def log_notification(google_sub: str, notification_type: str,
                     email: str, system_id: int | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        conn.execute(notification_log.insert().values(
            google_sub=google_sub,
            notification_type=notification_type,
            system_id=system_id,
            email=email,
            sent_at=now,
        ))
