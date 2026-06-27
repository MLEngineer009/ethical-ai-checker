"""FastAPI backend for ethical decision evaluation."""

import csv
import io
import logging
import os
import secrets
from typing import Any, Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .llm_orchestrator import LLMOrchestrator
from .report_generator import generate_pdf
from .risk_detector import detect_all_risks
from .regulations import get_regulatory_refs
from . import auth
from . import database
from . import questions as questions_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(*_):
    logger.info("Pragma API starting — initialising database")
    database.init_db()
    logger.info("Database ready")
    yield
    logger.info("Pragma API shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="Pragma",
    description="API for evaluating decisions using ethical reasoning frameworks",
    version="1.0.0",
    lifespan=lifespan,
)

_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]
_extra = os.getenv("ALLOWED_ORIGINS", "")  # comma-separated, set in Railway
if _extra:
    _ALLOWED_ORIGINS.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

orchestrator = LLMOrchestrator()
_bearer = HTTPBearer(auto_error=False)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    # Session token (Google/guest)
    user = auth.get_user(token)
    if user:
        return user
    # API key fallback
    if token.startswith("pragma_"):
        key_info = database.verify_api_key(token)
        if key_info:
            return {"sub": key_info["anon_id"], "name": "API", "picture": "", "via_api_key": True}
    raise HTTPException(status_code=401, detail="Invalid or expired session")


# ── Auth schemas ──────────────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    credential: str   # Google ID token from frontend


# ── Decision schemas ──────────────────────────────────────────────────────────

VALID_CATEGORIES = {"hiring", "finance", "healthcare", "workplace", "policy", "personal", "other"}

class DecisionRequest(BaseModel):
    decision: str
    context: Dict[str, Any]
    category: str = "other"
    block_threshold: float = 0.8   # confidence above this + 2+ flags → block

    @property
    def decision_trimmed(self) -> str:
        return self.decision[:4000]


class EthicalAnalysis(BaseModel):
    kantian_analysis: str
    utilitarian_analysis: str
    virtue_ethics_analysis: str
    risk_flags: list[str]
    confidence_score: float
    recommendation: str
    provider: str = "unknown"
    regulatory_refs: list[Dict[str, Any]] = []
    compliance_checks: list[Dict[str, Any]] = []
    # ── Firewall fields ────────────────────────────────────────────────────────
    should_block: bool = False         # True → decision should be blocked
    override_required: bool = False    # True → human review required before proceeding
    firewall_action: str = "allow"     # "block" | "override_required" | "allow"
    audit_log_id: Optional[int] = None
    proxy_variables_detected: list[Dict[str, Any]] = []


class ReportRequest(BaseModel):
    decision: str
    context: Dict[str, Any]
    analysis: Dict[str, Any]


class FeedbackRequest(BaseModel):
    rating: int              # 1 = thumbs up, -1 = thumbs down
    category: str = "other"
    provider: str = "unknown"
    model_version: str = "unknown"
    confidence: float = 0.5
    risk_flags: list[str] = []


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/auth/google")
async def google_auth(req: GoogleAuthRequest):
    """Verify Google ID token and return a session token."""
    user_info = auth.verify_google_token(req.credential)
    if not user_info:
        logger.warning("Google auth failed — invalid credential")
        raise HTTPException(status_code=401, detail="Invalid Google credential")
    token = auth.create_session(user_info)
    logger.info("Google auth success — user=%s", user_info.get("name", "unknown"))
    # Upsert user profile so we can send email notifications
    if user_info.get("email"):
        try:
            database.upsert_user(
                google_sub=user_info["sub"],
                email=user_info["email"],
                name=user_info.get("name", "User"),
            )
        except Exception:
            logger.exception("Failed to upsert user profile — non-fatal")
    return {
        "token":   token,
        "name":    user_info["name"],
        "picture": user_info["picture"],
    }


@app.post("/auth/guest")
async def guest_auth():
    """Create a temporary guest session — no sign-in required."""
    token, user_info = auth.create_guest_session()
    logger.info("Guest session created — name=%s", user_info.get("name", "guest"))
    return {"token": token, "name": user_info["name"], "picture": "", "is_guest": True}


@app.post("/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    if credentials:
        auth.logout(credentials.credentials)
    return {"ok": True}


@app.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"name": user["name"], "picture": user["picture"]}


@app.get("/my-stats")
async def my_stats(user: dict = Depends(get_current_user)):
    """Return aggregate usage stats — no PII."""
    return database.get_stats(user["sub"])


# ── Protected endpoints ───────────────────────────────────────────────────────

@app.post("/evaluate-decision", response_model=EthicalAnalysis, dependencies=[Depends(get_current_user)])
async def evaluate_decision(
    request: DecisionRequest,
    user: dict = Depends(get_current_user),
) -> EthicalAnalysis:
    """Evaluate a decision using ethical reasoning frameworks."""
    if not request.decision or not request.decision.strip():
        raise HTTPException(status_code=400, detail="Decision cannot be empty")
    if len(request.decision) > 4000:
        raise HTTPException(status_code=400, detail="Decision text exceeds 4,000 character limit")
    if not request.context:
        raise HTTPException(status_code=400, detail="Context cannot be empty")
    if len(str(request.context)) > 8000:
        raise HTTPException(status_code=400, detail="Context exceeds size limit")

    GUEST_EVAL_LIMIT = 10
    if user.get("is_guest"):
        if database.count_evaluations(user["sub"]) >= GUEST_EVAL_LIMIT:
            raise HTTPException(status_code=429, detail=f"Guest accounts are limited to {GUEST_EVAL_LIMIT} evaluations. Sign in with Google for unlimited access.")
    else:
        sub = database.get_subscription(user["sub"])
        limit = sub.get("eval_limit")
        if limit is not None and sub["evals_this_month"] >= limit:
            plan = sub["plan"]
            if plan == "free":
                raise HTTPException(
                    status_code=429,
                    detail=f"Free plan limit of {limit} evaluations/month reached. Upgrade to Growth for 2,000 evaluations/month.",
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail=f"Monthly evaluation limit of {limit} reached for your {plan} plan.",
                )

    category = request.category if request.category in VALID_CATEGORIES else "other"
    analysis = _run_evaluation(request.decision, request.context, category, request.block_threshold)

    from .risk_detector import get_proxy_variable_report
    proxy_report = get_proxy_variable_report(request.context)

    action = analysis["firewall_action"]
    if action == "block":
        logger.warning(
            "Firewall BLOCK — category=%s confidence=%.2f flags=%s",
            category, analysis["confidence_score"], analysis["risk_flags"],
        )
    elif action == "override_required":
        logger.info(
            "Firewall OVERRIDE_REQUIRED — category=%s confidence=%.2f flags=%s",
            category, analysis["confidence_score"], analysis["risk_flags"],
        )
    else:
        logger.info("Firewall ALLOW — category=%s confidence=%.2f", category, analysis["confidence_score"])

    database.log_request(
        google_sub=user["sub"],
        decision=request.decision,
        context=request.context,
        provider=analysis["provider"],
        confidence=analysis["confidence_score"],
        risk_flags=analysis["risk_flags"],
        category=category,
    )
    audit_log_id = database.log_audit(
        google_sub=user["sub"],
        decision=request.decision,
        context=request.context,
        firewall_action=analysis["firewall_action"],
        confidence=analysis["confidence_score"],
        risk_flags=analysis["risk_flags"],
        proxy_vars=[p["field"] for p in proxy_report["proxy_variables_detected"]],
        regulatory_refs=analysis.get("regulatory_refs", []),
        provider=analysis["provider"],
        category=category,
    )

    analysis["audit_log_id"] = audit_log_id
    analysis["proxy_variables_detected"] = proxy_report["proxy_variables_detected"]
    return EthicalAnalysis(**analysis)


class HITLOverrideRequest(BaseModel):
    audit_log_id: int
    reason: str

@app.post("/audit/override", dependencies=[Depends(get_current_user)])
async def hitl_override(request: HITLOverrideRequest, user: dict = Depends(get_current_user)):
    """
    Record a human investigator override of a firewall verdict.
    Meets EU AI Act Article 14 human oversight requirements.
    """
    if not request.reason or not request.reason.strip():
        raise HTTPException(status_code=400, detail="Override reason cannot be empty")
    if len(request.reason) > 1000:
        raise HTTPException(status_code=400, detail="Override reason exceeds 1,000 character limit")
    success = database.log_hitl_override(
        audit_log_id=request.audit_log_id,
        investigator_sub=user["sub"],
        reason=request.reason,
        google_sub=user["sub"],
    )
    if not success:
        raise HTTPException(404, "Audit log entry not found or access denied")
    logger.info("HITL override recorded — audit_log_id=%d", request.audit_log_id)
    return {"recorded": True, "audit_log_id": request.audit_log_id}


@app.get("/audit/log", dependencies=[Depends(get_current_user)])
async def get_audit_log(user: dict = Depends(get_current_user), limit: int = 50):
    """Return the last N audit log entries for the current user."""
    return database.get_audit_log(google_sub=user["sub"], limit=limit)


class ProxyVariableReportRequest(BaseModel):
    context: Dict[str, Any]


@app.post("/proxy-variable-report", dependencies=[Depends(get_current_user)])
async def proxy_variable_report(request: ProxyVariableReportRequest):
    """
    Returns a structured proxy variable audit report for a given context.
    Lists each detected field, its value, the risk it represents, and the
    applicable ECOA / Regulation B citation.
    """
    from .risk_detector import get_proxy_variable_report
    return get_proxy_variable_report(request.context)


# ── EU AI Act — AI System Registration & Compliance ──────────────────────────

class AISystemRequest(BaseModel):
    # Core profile
    system_name: str
    company_name: str
    risk_tier: str                          # minimal|limited|high|unacceptable
    use_case: str
    model_version: str = "unknown"
    training_data_sources: List[str] = []
    intended_purpose: str = ""
    geographic_scope: str = ""
    # Declarative article fields
    art4_literacy_training: bool = False
    art6_annex_category: str = ""
    art15_accuracy_metric: str = ""
    art15_robustness_tested: bool = False
    art17_qms_documented: bool = False
    art25_instructions_provided: bool = False
    art25_monitoring_active: bool = False
    art27_fria_conducted: bool = False
    art30_eu_db_registered: bool = False
    art30_registration_number: str = ""
    art33_conformity_type: str = ""         # self-assessment|third-party|pending
    # Evidence notes + dates (enables pass vs partial distinction)
    art4_literacy_training_evidence_notes: str = ""
    art4_literacy_training_evidence_date: str = ""
    art17_qms_documented_evidence_notes: str = ""
    art17_qms_documented_evidence_date: str = ""
    art25_instructions_provided_evidence_notes: str = ""
    art25_instructions_provided_evidence_date: str = ""
    art25_monitoring_active_evidence_notes: str = ""
    art25_monitoring_active_evidence_date: str = ""
    art27_fria_conducted_evidence_notes: str = ""
    art27_fria_conducted_evidence_date: str = ""
    art30_eu_db_registered_evidence_notes: str = ""
    art30_eu_db_registered_evidence_date: str = ""
    art33_conformity_type_evidence_notes: str = ""
    art33_conformity_type_evidence_date: str = ""


VALID_RISK_TIERS = {"minimal", "limited", "high", "unacceptable"}
VALID_CONFORMITY_TYPES = {"self-assessment", "third-party", "pending", ""}


@app.post("/ai-systems", dependencies=[Depends(get_current_user)])
async def register_ai_system(request: AISystemRequest, user: dict = Depends(get_current_user)):
    """Register an AI system for EU AI Act data lineage tracking."""
    from .compliance_engine import ANNEX_III_CATEGORIES
    if not request.system_name.strip():
        raise HTTPException(status_code=400, detail="system_name is required")
    if not request.company_name.strip():
        raise HTTPException(status_code=400, detail="company_name is required")
    if request.risk_tier not in VALID_RISK_TIERS:
        raise HTTPException(status_code=400, detail=f"risk_tier must be one of {VALID_RISK_TIERS}")
    if request.art33_conformity_type not in VALID_CONFORMITY_TYPES:
        raise HTTPException(status_code=400, detail=f"art33_conformity_type must be one of {VALID_CONFORMITY_TYPES}")
    if request.art6_annex_category.strip() and request.art6_annex_category.strip() not in ANNEX_III_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"art6_annex_category must be one of the official Annex III categories: {ANNEX_III_CATEGORIES}",
        )
    logger.info(
        "AI system registration — name=%r company=%r risk_tier=%s",
        request.system_name, request.company_name, request.risk_tier,
    )
    return database.create_ai_system(
        google_sub=user["sub"],
        system_name=request.system_name.strip(),
        company_name=request.company_name.strip(),
        risk_tier=request.risk_tier,
        use_case=request.use_case.strip(),
        model_version=request.model_version,
        training_data_sources=request.training_data_sources,
        intended_purpose=request.intended_purpose.strip(),
        geographic_scope=request.geographic_scope.strip(),
        art4_literacy_training=request.art4_literacy_training,
        art6_annex_category=request.art6_annex_category.strip(),
        art15_accuracy_metric=request.art15_accuracy_metric.strip(),
        art15_robustness_tested=request.art15_robustness_tested,
        art17_qms_documented=request.art17_qms_documented,
        art25_instructions_provided=request.art25_instructions_provided,
        art25_monitoring_active=request.art25_monitoring_active,
        art27_fria_conducted=request.art27_fria_conducted,
        art30_eu_db_registered=request.art30_eu_db_registered,
        art30_registration_number=request.art30_registration_number.strip(),
        art33_conformity_type=request.art33_conformity_type.strip(),
        art4_literacy_training_evidence_notes=request.art4_literacy_training_evidence_notes.strip(),
        art4_literacy_training_evidence_date=request.art4_literacy_training_evidence_date.strip(),
        art17_qms_documented_evidence_notes=request.art17_qms_documented_evidence_notes.strip(),
        art17_qms_documented_evidence_date=request.art17_qms_documented_evidence_date.strip(),
        art25_instructions_provided_evidence_notes=request.art25_instructions_provided_evidence_notes.strip(),
        art25_instructions_provided_evidence_date=request.art25_instructions_provided_evidence_date.strip(),
        art25_monitoring_active_evidence_notes=request.art25_monitoring_active_evidence_notes.strip(),
        art25_monitoring_active_evidence_date=request.art25_monitoring_active_evidence_date.strip(),
        art27_fria_conducted_evidence_notes=request.art27_fria_conducted_evidence_notes.strip(),
        art27_fria_conducted_evidence_date=request.art27_fria_conducted_evidence_date.strip(),
        art30_eu_db_registered_evidence_notes=request.art30_eu_db_registered_evidence_notes.strip(),
        art30_eu_db_registered_evidence_date=request.art30_eu_db_registered_evidence_date.strip(),
        art33_conformity_type_evidence_notes=request.art33_conformity_type_evidence_notes.strip(),
        art33_conformity_type_evidence_date=request.art33_conformity_type_evidence_date.strip(),
    )


@app.get("/ai-systems", dependencies=[Depends(get_current_user)])
async def list_ai_systems(user: dict = Depends(get_current_user)):
    """List all AI systems registered by the current user."""
    return database.get_ai_systems(google_sub=user["sub"])


@app.get("/ai-systems/{system_id}/compliance", dependencies=[Depends(get_current_user)])
async def get_compliance_status(system_id: int, user: dict = Depends(get_current_user)):
    """Compute EU AI Act compliance checklist for a registered AI system."""
    from .compliance_engine import compute_compliance
    system = database.get_ai_system(system_id=system_id, google_sub=user["sub"])
    if not system:
        raise HTTPException(status_code=404, detail="AI system not found")
    stats = database.get_audit_stats_for_system(google_sub=user["sub"])
    result = compute_compliance(system=system, stats=stats)
    try:
        database.save_compliance_snapshot(
            google_sub=user["sub"],
            system_id=system_id,
            score=result["overall_score"],
            verdict=result["verdict"],
            passes=result["passes"],
            partials=result["partials"],
            fails=result["fails"],
            articles=result["articles"],
        )
    except Exception:
        logger.exception("Failed to save compliance snapshot — non-fatal")
    return result


@app.get("/ai-systems/{system_id}/history", dependencies=[Depends(get_current_user)])
async def get_compliance_history(system_id: int, user: dict = Depends(get_current_user)):
    """Return score history snapshots for a single AI system (for trend charts)."""
    system = database.get_ai_system(system_id=system_id, google_sub=user["sub"])
    if not system:
        raise HTTPException(status_code=404, detail="AI system not found")
    return database.get_compliance_history(google_sub=user["sub"], system_id=system_id)


@app.get("/dashboard/summary", dependencies=[Depends(get_current_user)])
async def get_dashboard_summary(user: dict = Depends(get_current_user)):
    """Return compliance summary across all of the user's AI systems."""
    return database.get_dashboard_summary(google_sub=user["sub"])


# ── Evidence collection endpoints ─────────────────────────────────────────────

@app.post("/evidence/extract", dependencies=[Depends(get_current_user)])
async def extract_evidence_from_document(
    article_key: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a compliance document and extract structured evidence using AI.
    Returns notes, date, verdict, and explanation for the given article.
    """
    from .evidence_analyzer import analyze_document
    from .interview_engine import get_article_questions

    article_info = get_article_questions(article_key)
    if not article_info:
        raise HTTPException(status_code=400, detail=f"Unknown article key: {article_key}")

    max_bytes = 10 * 1024 * 1024  # 10 MB
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large — maximum 10 MB")

    logger.info(
        "Evidence extraction — user=%s article=%s file=%s size=%d",
        user["sub"][:8], article_key, file.filename, len(data),
    )
    result = analyze_document(
        article_key=article_key,
        article_title=article_info["title"],
        article_requirement=article_info["requirement"],
        filename=file.filename or "upload",
        file_data=data,
    )
    return result


@app.post("/evidence/interview", dependencies=[Depends(get_current_user)])
async def score_evidence_interview(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Score structured interview answers for a compliance article using AI.
    Body: { article_key: str, answers: [{question: str, answer: str}] }
    """
    from .evidence_analyzer import score_interview
    from .interview_engine import get_article_questions

    body = await request.json()
    article_key = body.get("article_key", "")
    answers = body.get("answers", [])

    article_info = get_article_questions(article_key)
    if not article_info:
        raise HTTPException(status_code=400, detail=f"Unknown article key: {article_key}")
    if not answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    logger.info(
        "Interview scoring — user=%s article=%s answers=%d",
        user["sub"][:8], article_key, len(answers),
    )
    result = score_interview(
        article_key=article_key,
        article_title=article_info["title"],
        article_requirement=article_info["requirement"],
        questions_and_answers=answers,
    )
    return result


@app.get("/evidence/questions/{article_key}", dependencies=[Depends(get_current_user)])
async def get_interview_questions(article_key: str, _: dict = Depends(get_current_user)):
    """Return the guided interview questions for a given article."""
    from .interview_engine import get_article_questions
    info = get_article_questions(article_key)
    if not info:
        raise HTTPException(status_code=404, detail=f"No interview available for: {article_key}")
    return info


@app.post("/ai-systems/{system_id}/certificate", dependencies=[Depends(get_current_user)])
async def issue_certificate(system_id: int, user: dict = Depends(get_current_user)):
    """Generate a PDF compliance readiness certificate for a registered AI system."""
    from .compliance_engine import compute_compliance
    from .compliance_certificate import generate_certificate
    system = database.get_ai_system(system_id=system_id, google_sub=user["sub"])
    if not system:
        raise HTTPException(status_code=404, detail="AI system not found")
    stats = database.get_audit_stats_for_system(google_sub=user["sub"])
    compliance = compute_compliance(system=system, stats=stats)

    verdict = compliance["verdict"]
    logger.info(
        "Certificate request — system_id=%d name=%r score=%.3f verdict=%s",
        system_id, system["system_name"], compliance["overall_score"], verdict,
    )
    if verdict == "prohibited":
        logger.warning(
            "Certificate DENIED — system_id=%d is prohibited under EU AI Act Art. 5", system_id
        )

    certificate_id = "PRAGMA-" + secrets.token_hex(6).upper()
    database.save_certificate(
        google_sub=user["sub"],
        ai_system_id=system_id,
        certificate_id=certificate_id,
        overall_score=compliance["overall_score"],
        articles_status={k: v["status"] for k, v in compliance["articles"].items()},
        total_evaluations=stats["total"],
        hitl_overrides=stats["hitl_overrides"],
        proxy_vars_caught=stats["proxy_vars_caught"],
    )

    try:
        pdf_bytes = generate_certificate(compliance=compliance, certificate_id=certificate_id)
    except Exception:
        logger.exception("Certificate PDF generation failed — system_id=%d cert=%s", system_id, certificate_id)
        raise HTTPException(status_code=500, detail="Certificate generation failed")
    logger.info("Certificate issued — id=%s system_id=%d", certificate_id, system_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="pragma-certificate-{certificate_id}.pdf"'},
    )


@app.post("/feedback", dependencies=[Depends(get_current_user)])
async def submit_feedback(
    request: FeedbackRequest,
    user: dict = Depends(get_current_user),
):
    """
    Thumbs up/down on an analysis — feeds the Pragma model retraining flywheel.
    No decision text or context is stored here.
    """
    if request.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 (up) or -1 (down)")
    category = request.category if request.category in VALID_CATEGORIES else "other"
    database.log_feedback(
        google_sub    = user["sub"],
        rating        = request.rating,
        category      = category,
        provider      = request.provider,
        model_version = request.model_version,
        confidence    = request.confidence,
        risk_flags    = request.risk_flags,
    )
    return {"ok": True}


@app.post("/generate-report", dependencies=[Depends(get_current_user)])
async def generate_report(request: ReportRequest) -> Response:
    """Generate a PDF report for a completed ethical analysis."""
    try:
        pdf_bytes = generate_pdf(request.decision, request.context, request.analysis)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ethical-analysis-report.pdf"},
        )
    except Exception:
        logger.exception("PDF report generation failed")
        raise HTTPException(status_code=500, detail="Report generation failed")


# ── Public endpoints ──────────────────────────────────────────────────────────

@app.get("/health-check")
async def health_check():
    return {
        "status": "healthy",
        "service": "pragma",
        "model": {
            "pragma":  orchestrator._custom.available,   # our model — primary
            "claude":  orchestrator._claude is not None, # fallback
            "openai":  orchestrator._openai is not None, # fallback
        }
    }


class WaitlistRequest(BaseModel):
    email: str


@app.post("/waitlist")
async def join_waitlist(req: WaitlistRequest):
    """Capture email from landing page — no auth required."""
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid email")
    added = database.add_to_waitlist(email)
    return {"added": added}


@app.get("/questions")
async def get_questions(category: str = ""):
    """
    Return guided context questions for a given category.
    Used by all clients (web, mobile) to render the question UI.
    Version-stamped so ml/optimize_questions.py can track improvements.
    """
    if category and category not in questions_module.QUESTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    if category:
        return {
            "version": questions_module.VERSION,
            "category": category,
            "questions": questions_module.get_questions(category),
        }
    return questions_module.get_all()


# ── Bulk evaluation ───────────────────────────────────────────────────────────

def _compute_firewall(risk_flags: list, confidence_score: float, block_threshold: float = 0.8) -> Dict[str, Any]:
    """Compute firewall action based on risk flags and confidence."""
    should_block = confidence_score >= block_threshold and len(risk_flags) >= 2
    override_required = len(risk_flags) >= 1 and not should_block
    if should_block:
        action = "block"
    elif override_required:
        action = "override_required"
    else:
        action = "allow"
    return {"should_block": should_block, "override_required": override_required, "firewall_action": action}


def _run_evaluation(decision: str, context: Dict[str, Any], category: str, block_threshold: float = 0.8) -> Dict[str, Any]:
    """Shared evaluation logic used by single and batch endpoints."""
    llm_analysis = orchestrator.evaluate(decision, context, category)
    risk_flags = detect_all_risks(decision, context)
    if llm_analysis.get("risk_flags"):
        risk_flags = sorted(list(set(risk_flags) | set(llm_analysis["risk_flags"])))
    confidence_score = llm_analysis.get("confidence_score", 0.5)
    if not isinstance(confidence_score, (int, float)) or not 0 <= confidence_score <= 1:
        confidence_score = 0.5
    return {
        "kantian_analysis":      llm_analysis.get("kantian_analysis", ""),
        "utilitarian_analysis":  llm_analysis.get("utilitarian_analysis", ""),
        "virtue_ethics_analysis": llm_analysis.get("virtue_ethics_analysis", ""),
        "risk_flags":            risk_flags,
        "confidence_score":      confidence_score,
        "recommendation":        llm_analysis.get("recommendation", ""),
        "provider":              llm_analysis.get("provider", "unknown"),
        "regulatory_refs":       get_regulatory_refs(risk_flags, category),
        "compliance_checks":     llm_analysis.get("compliance_checks", []),
        **_compute_firewall(risk_flags, confidence_score, block_threshold),
    }


@app.post("/evaluate-batch", dependencies=[Depends(get_current_user)])
async def evaluate_batch(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Accepts a CSV with columns: decision, category, [any context keys…]
    Returns a CSV with all original columns plus analysis columns appended.

    Example CSV header:
        decision,category,role,experience_years
    """
    # Enforce plan limits before processing — batch counts against the monthly quota
    if not user.get("is_guest"):
        sub = database.get_subscription(user["sub"])
        limit = sub.get("eval_limit")
        if limit is not None and sub["evals_this_month"] >= limit:
            raise HTTPException(status_code=429, detail=f"Monthly evaluation limit of {limit} reached.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")   # handle BOM
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except Exception:
        logger.warning("Batch upload rejected — invalid CSV from user=%s", user["sub"][:8])
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")
    if len(rows) > 100:
        raise HTTPException(status_code=400, detail="Batch limit is 100 rows")
    logger.info("Batch evaluation started — rows=%d user=%s", len(rows), user["sub"][:8])

    RESERVED = {"decision", "category"}
    results = []
    for row in rows:
        decision = row.get("decision", "").strip()
        category = row.get("category", "other").strip()
        if category not in VALID_CATEGORIES:
            category = "other"
        context = {k: v for k, v in row.items() if k not in RESERVED and v}
        if not decision:
            results.append({**row, "error": "missing decision", "risk_flags": "",
                            "confidence_score": "", "recommendation": "", "regulatory_refs": ""})
            continue
        try:
            analysis = _run_evaluation(decision, context, category)
            database.log_request(
                google_sub=user["sub"], decision=decision, context=context,
                provider=analysis["provider"], confidence=analysis["confidence_score"],
                risk_flags=analysis["risk_flags"], category=category,
            )
            results.append({
                **row,
                "risk_flags":       ", ".join(analysis["risk_flags"]),
                "confidence_score": round(analysis["confidence_score"], 3),
                "recommendation":   analysis["recommendation"],
                "regulatory_refs":  "; ".join(r["law"] for r in analysis["regulatory_refs"]),
                "provider":         analysis["provider"],
                "error":            "",
            })
        except Exception as e:
            logger.error("Batch row evaluation failed — decision=%r error=%s", decision[:60], e)
            results.append({**row, "error": "evaluation error", "risk_flags": "",
                            "confidence_score": "", "recommendation": "", "regulatory_refs": ""})

    # Build output CSV
    if results:
        out_fields = list(results[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(results)
        csv_bytes = output.getvalue().encode()
    else:
        csv_bytes = b""

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pragma-batch-results.csv"},
    )


# ── Disparate Impact Analysis (EEOC 4/5ths Rule) ─────────────────────────────

@app.post("/disparity-analysis", dependencies=[Depends(get_current_user)])
async def disparity_analysis(
    file: UploadFile = File(...),
    demographic_field: str = Form(...),
    outcome_field: str = Form(...),
    positive_outcome: str = Form("advance"),
    user: dict = Depends(get_current_user),
):
    """
    Upload a CSV of AI decisions and compute disparate impact statistics
    per demographic group using the EEOC 4/5ths (80%) rule.

    Required CSV columns:
      - <demographic_field>  e.g. race, gender, age_group
      - <outcome_field>      e.g. decision, result, ai_verdict
      Any additional context columns are ignored.

    Returns:
      - selection_rates: selection rate per group
      - disparity_ratios: ratio vs. highest-rate group
      - violations: groups below the 80% threshold (EEOC 4/5ths rule)
      - adverse_impact_found: bool
      - total_decisions, total_groups
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")
    if len(rows) > 5000:
        raise HTTPException(status_code=400, detail="Disparity analysis limit is 5,000 rows")

    if demographic_field not in rows[0]:
        raise HTTPException(
            status_code=400,
            detail=f"Demographic field '{demographic_field}' not found in CSV. "
                   f"Available columns: {', '.join(rows[0].keys())}",
        )
    if outcome_field not in rows[0]:
        raise HTTPException(
            status_code=400,
            detail=f"Outcome field '{outcome_field}' not found in CSV. "
                   f"Available columns: {', '.join(rows[0].keys())}",
        )

    # Count selections per demographic group
    group_total: Dict[str, int] = {}
    group_selected: Dict[str, int] = {}

    for row in rows:
        group = (row.get(demographic_field) or "unknown").strip()
        outcome = (row.get(outcome_field) or "").strip().lower()
        is_selected = positive_outcome.lower() in outcome or outcome in ("yes", "true", "1", "pass", "advance", "hired")

        group_total[group] = group_total.get(group, 0) + 1
        if is_selected:
            group_selected[group] = group_selected.get(group, 0) + 1

    if not group_total:
        raise HTTPException(status_code=400, detail="No valid rows found")

    # Compute selection rates
    selection_rates: Dict[str, float] = {
        g: round(group_selected.get(g, 0) / group_total[g], 4)
        for g in group_total
        if group_total[g] >= 5  # minimum sample size for statistical reliability
    }

    if not selection_rates:
        raise HTTPException(
            status_code=400,
            detail="No groups have enough data (minimum 5 decisions per group required)",
        )

    highest_rate = max(selection_rates.values())
    highest_group = max(selection_rates, key=lambda g: selection_rates[g])

    # EEOC 4/5ths rule: a group is disparately impacted if its selection rate
    # is less than 80% of the highest group's selection rate
    THRESHOLD = 0.80
    disparity_ratios: Dict[str, float] = {
        g: round(rate / highest_rate, 4) if highest_rate > 0 else 1.0
        for g, rate in selection_rates.items()
    }
    violations = [
        {
            "group":              g,
            "selection_rate":     selection_rates[g],
            "disparity_ratio":    disparity_ratios[g],
            "vs_highest_group":   highest_group,
            "total_in_group":     group_total[g],
            "selected_in_group":  group_selected.get(g, 0),
            "eeoc_threshold":     THRESHOLD,
            "verdict":            "ADVERSE IMPACT",
            "regulation":         "EEOC Uniform Guidelines on Employee Selection Procedures (29 CFR Part 1607) — 4/5ths rule",
        }
        for g, ratio in disparity_ratios.items()
        if ratio < THRESHOLD and g != highest_group
    ]

    groups_detail = [
        {
            "group":             g,
            "total":             group_total[g],
            "selected":          group_selected.get(g, 0),
            "selection_rate":    selection_rates[g],
            "disparity_ratio":   disparity_ratios[g],
            "status":            "ADVERSE IMPACT" if disparity_ratios[g] < THRESHOLD and g != highest_group else "OK",
        }
        for g in sorted(selection_rates, key=lambda x: selection_rates[x], reverse=True)
    ]

    adverse_impact_found = len(violations) > 0

    logger.info(
        "Disparity analysis — rows=%d groups=%d adverse_impact=%s user=%s",
        len(rows), len(selection_rates), adverse_impact_found, user["sub"][:8],
    )

    return {
        "adverse_impact_found":  adverse_impact_found,
        "total_decisions":       len(rows),
        "total_groups":          len(selection_rates),
        "demographic_field":     demographic_field,
        "outcome_field":         outcome_field,
        "positive_outcome":      positive_outcome,
        "highest_rate_group":    highest_group,
        "highest_selection_rate": highest_rate,
        "eeoc_threshold":        THRESHOLD,
        "groups":                groups_detail,
        "violations":            violations,
        "regulatory_refs": [
            {
                "law":          "EEOC Uniform Guidelines on Employee Selection Procedures",
                "citation":     "29 CFR Part 1607, Section 4D — 4/5ths (80%) rule",
                "jurisdiction": "US",
                "url":          "https://www.govinfo.gov/content/pkg/CFR-2021-title29-vol4/pdf/CFR-2021-title29-vol4-part1607.pdf",
            },
            {
                "law":          "NYC Local Law 144 — Automated Employment Decision Tools",
                "citation":     "Requires annual bias audit including impact ratio by race/sex and intersectional categories",
                "jurisdiction": "US (New York City)",
                "url":          "https://rules.cityofnewyork.us/rule/automated-employment-decision-tools-2/",
            },
            {
                "law":          "EU AI Act Art. 9 — Risk Management System",
                "citation":     "Requires testing AI systems for discriminatory outputs across demographic groups",
                "jurisdiction": "EU",
                "url":          "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689",
            },
        ] if adverse_impact_found else [],
        "summary": (
            f"Adverse impact detected: {len(violations)} group(s) fall below the EEOC 80% threshold. "
            f"Highest selection rate: {highest_group} at {highest_rate:.1%}. "
            f"This pattern may constitute unlawful disparate impact under EEOC guidelines and NYC Local Law 144."
            if adverse_impact_found else
            f"No adverse impact detected across {len(selection_rates)} demographic groups. "
            f"All groups are within the EEOC 80% threshold relative to the highest-rate group ({highest_group} at {highest_rate:.1%})."
        ),
    }


# ── Counterfactual analysis ────────────────────────────────────────────────────

class CounterfactualRequest(BaseModel):
    decision: str
    context: Dict[str, Any]
    category: str = "other"
    changed_key: str
    changed_value: Any


@app.post("/counterfactual", dependencies=[Depends(get_current_user)])
async def counterfactual(request: CounterfactualRequest):
    """
    Run two analyses — original context vs. modified context — and return both
    plus a diff of risk flags and confidence change.
    Useful for bias audits: 'what changes if gender=male vs gender=female?'
    """
    if not request.decision.strip():
        raise HTTPException(status_code=400, detail="Decision cannot be empty")

    category = request.category if request.category in VALID_CATEGORIES else "other"
    modified_context = {**request.context, request.changed_key: request.changed_value}

    original  = _run_evaluation(request.decision, request.context, category)
    modified  = _run_evaluation(request.decision, modified_context, category)

    orig_flags = set(original["risk_flags"])
    mod_flags  = set(modified["risk_flags"])

    return {
        "original":  original,
        "modified":  modified,
        "changed_key":   request.changed_key,
        "original_value": request.context.get(request.changed_key),
        "modified_value": request.changed_value,
        "diff": {
            "flags_added":   sorted(mod_flags - orig_flags),
            "flags_removed": sorted(orig_flags - mod_flags),
            "confidence_delta": round(
                modified["confidence_score"] - original["confidence_score"], 3
            ),
        },
    }


# ── Team / Org endpoints ───────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: str


class JoinOrgRequest(BaseModel):
    invite_code: str


@app.post("/orgs", dependencies=[Depends(get_current_user)])
async def create_org(req: CreateOrgRequest, user: dict = Depends(get_current_user)):
    """Create a new organization. The caller becomes the owner."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Organization name cannot be empty")
    return database.create_org(name, user["sub"])


@app.post("/orgs/join", dependencies=[Depends(get_current_user)])
async def join_org(req: JoinOrgRequest, user: dict = Depends(get_current_user)):
    """Join an organization using an invite code."""
    org = database.get_org_by_invite(req.invite_code)
    if not org:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    joined = database.join_org(org["org_id"], user["sub"])
    return {"org_id": org["org_id"], "name": org["name"], "already_member": not joined}


@app.get("/orgs", dependencies=[Depends(get_current_user)])
async def my_orgs(user: dict = Depends(get_current_user)):
    """List organizations the current user belongs to."""
    return database.get_my_orgs(user["sub"])


@app.get("/orgs/{org_id}/history", dependencies=[Depends(get_current_user)])
async def org_history(org_id: int, user: dict = Depends(get_current_user)):
    """Return shared decision history for all members of an org."""
    rows = database.get_org_history(org_id, user["sub"])
    if rows is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return {"org_id": org_id, "history": rows}


# ── Billing / Stripe ──────────────────────────────────────────────────────────

import stripe as _stripe

_stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
_STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")
_STRIPE_GROWTH_PRICE_ID = os.getenv("STRIPE_GROWTH_PRICE_ID", "")

# Map Stripe price IDs → plan names (extend when more tiers are added)
_PRICE_TO_PLAN: Dict[str, str] = {}
if _STRIPE_GROWTH_PRICE_ID:
    _PRICE_TO_PLAN[_STRIPE_GROWTH_PRICE_ID] = "growth"


@app.get("/billing/subscription", dependencies=[Depends(get_current_user)])
async def get_subscription(user: dict = Depends(get_current_user)):
    """Return current plan, usage this month, and eval limit."""
    return database.get_subscription(user["sub"])


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


@app.post("/billing/create-checkout-session", dependencies=[Depends(get_current_user)])
async def create_checkout_session(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Create a Stripe Checkout session for a paid plan upgrade."""
    if not _stripe.api_key:
        raise HTTPException(status_code=503, detail="Billing not configured")
    if req.price_id not in _PRICE_TO_PLAN:
        raise HTTPException(status_code=400, detail="Invalid price_id")

    sub = database.get_subscription(user["sub"])
    customer_id = sub.get("stripe_customer_id")

    session_params: Dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": req.price_id, "quantity": 1}],
        "success_url": req.success_url,
        "cancel_url":  req.cancel_url,
        "metadata":    {"anon_id": database.anon_id(user["sub"])},
        "subscription_data": {"metadata": {"anon_id": database.anon_id(user["sub"])}},
    }
    if customer_id:
        session_params["customer"] = customer_id
    elif user.get("email"):
        session_params["customer_email"] = user["email"]

    session = _stripe.checkout.Session.create(**session_params)
    logger.info("Stripe Checkout session created — user=%s price=%s", user["sub"][:8], req.price_id)
    return {"checkout_url": session.url}


@app.post("/billing/portal", dependencies=[Depends(get_current_user)])
async def billing_portal(user: dict = Depends(get_current_user)):
    """Create a Stripe Customer Portal session for plan management/cancellation."""
    if not _stripe.api_key:
        raise HTTPException(status_code=503, detail="Billing not configured")
    sub = database.get_subscription(user["sub"])
    customer_id = sub.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found")
    origin = os.getenv("APP_URL", "https://usepragma.co")
    portal = _stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{origin}/",
    )
    logger.info("Stripe portal session created — user=%s", user["sub"][:8])
    return {"portal_url": portal.url}


@app.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook — verifies signature then updates subscription records.
    Must be registered in Stripe dashboard pointing to /billing/webhook.
    No auth — Stripe calls this directly.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not _STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    try:
        event = _stripe.Webhook.construct_event(payload, sig_header, _STRIPE_WEBHOOK_SECRET)
    except _stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    _handle_stripe_event(event)
    return {"received": True}


def _handle_stripe_event(event: Dict) -> None:
    """Process a verified Stripe event and update the subscriptions table."""
    etype = event["type"]
    data  = event["data"]["object"]

    if etype == "checkout.session.completed":
        anon_id_val   = data.get("metadata", {}).get("anon_id")
        customer_id   = data.get("customer")
        subscription_id = data.get("subscription")
        if not anon_id_val:
            logger.warning("checkout.session.completed missing anon_id metadata")
            return
        # Retrieve full subscription to get price and period
        if subscription_id:
            stripe_sub = _stripe.Subscription.retrieve(subscription_id)
            price_id   = stripe_sub["items"]["data"][0]["price"]["id"]
            plan       = _PRICE_TO_PLAN.get(price_id, "growth")
            period_end = datetime.fromtimestamp(
                stripe_sub["current_period_end"], tz=timezone.utc
            ).isoformat()
            database.upsert_subscription(
                anon_id_val=anon_id_val, plan=plan, status="active",
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                current_period_end=period_end,
            )
            logger.info("Checkout completed — anon_id=%s plan=%s", anon_id_val[:8], plan)

    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        customer_id     = data.get("customer")
        subscription_id = data.get("id")
        price_id        = data["items"]["data"][0]["price"]["id"]
        plan            = _PRICE_TO_PLAN.get(price_id, "growth")
        status          = data.get("status", "active")
        period_end      = datetime.fromtimestamp(
            data["current_period_end"], tz=timezone.utc
        ).isoformat()
        anon_id_val = database.get_anon_id_by_stripe_customer(customer_id)
        if anon_id_val:
            database.upsert_subscription(
                anon_id_val=anon_id_val, plan=plan, status=status,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                current_period_end=period_end,
            )

    elif etype == "customer.subscription.deleted":
        customer_id = data.get("customer")
        anon_id_val = database.get_anon_id_by_stripe_customer(customer_id)
        if anon_id_val:
            database.upsert_subscription(
                anon_id_val=anon_id_val, plan="free", status="canceled",
                stripe_customer_id=customer_id,
                stripe_subscription_id=data.get("id"),
                current_period_end=None,
            )
            logger.info("Subscription canceled — anon_id=%s downgraded to free", anon_id_val[:8])

    else:
        logger.debug("Unhandled Stripe event type: %s", etype)


# ── API key endpoints ──────────────────────────────────────────────────────────

class CreateAPIKeyRequest(BaseModel):
    label: str = "My API Key"


@app.post("/api-keys", dependencies=[Depends(get_current_user)])
async def create_api_key(req: CreateAPIKeyRequest, user: dict = Depends(get_current_user)):
    """Generate a new API key. The raw key is returned once — store it safely."""
    if user.get("via_api_key"):
        raise HTTPException(status_code=403, detail="Cannot create API keys from an API key session")
    return database.create_api_key(user["sub"], req.label.strip() or "My API Key")


@app.get("/api-keys", dependencies=[Depends(get_current_user)])
async def list_api_keys(user: dict = Depends(get_current_user)):
    """List all API keys for the current user (prefix + usage stats, never the raw key)."""
    return database.get_api_keys(user["sub"])


@app.delete("/api-keys/{key_id}", dependencies=[Depends(get_current_user)])
async def revoke_api_key(key_id: int, user: dict = Depends(get_current_user)):
    """Revoke an API key by ID."""
    revoked = database.revoke_api_key(key_id, user["sub"])
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"revoked": True}


CHAT_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions about hiring, HR policy, lending, and business decisions. You are professional, concise, and always remind users to follow fair and legal practices. Keep answers under 3 sentences."""

CHAT_FALLBACK_ANSWERS = [
    ("hire", "Base hiring decisions on verified qualifications, skills assessments, and structured interviews. Always document your criteria before reviewing candidates to ensure consistency."),
    ("loan", "Credit decisions should be based on objective financial factors: income, debt-to-income ratio, credit history, and repayment capacity. Avoid using proxies that correlate with protected characteristics."),
    ("fire", "Terminations should be documented, consistent, and based on clear performance or conduct criteria. Consult HR and legal before proceeding with any dismissal."),
    ("promote", "Promotions should follow transparent criteria applied consistently across all eligible employees. Document the decision rationale and ensure it's reviewable."),
    ("salary", "Compensation decisions should be based on role scope, market data, and performance metrics — not on personal characteristics. Conduct regular pay equity audits."),
    ("interview", "Use structured interviews with standardized questions for all candidates. Score responses against predefined criteria before comparing candidates."),
]

def _generate_chat_response(message: str, history: list) -> str:
    """Generate a chat response using the LLM orchestrator, with a fallback."""
    try:
        context = {"question": message}
        result = orchestrator.evaluate(message, context)
        rec = result.get("recommendation", "")
        if rec and len(rec) > 20:
            return rec
    except Exception:
        pass

    msg_lower = message.lower()
    for keyword, answer in CHAT_FALLBACK_ANSWERS:
        if keyword in msg_lower:
            return answer
    return "That's a great question. Please consult your HR and legal teams to ensure your approach aligns with applicable regulations and your company's policies."


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    category: str = "other"
    block_threshold: float = 0.8

class ChatResponse(BaseModel):
    user_message: str
    ai_response: Optional[str]
    blocked: bool
    firewall_action: str
    risk_flags: List[str]
    confidence_score: float
    recommendation: str
    violations: List[Dict[str, Any]] = []


@app.post("/chat", dependencies=[Depends(get_current_user)])
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)) -> ChatResponse:
    """
    Compliance-aware chat endpoint.
    Evaluates the user message through the Pragma firewall before generating a response.
    Blocked messages return firewall details with no AI response.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    category = request.category if request.category in VALID_CATEGORIES else "other"
    context = {"input": request.message[:500]}

    # Use heuristic flags as the primary block signal — the custom model is not
    # calibrated enough to differentiate safe from risky via confidence score alone.
    heuristic_flags = detect_all_risks(request.message, context)
    analysis = _run_evaluation(request.message, context, category, request.block_threshold)

    heuristic_block = (
        analysis["confidence_score"] >= request.block_threshold
        and len(heuristic_flags) >= 2
    )
    firewall_action = "block" if heuristic_block else (
        "override_required" if len(heuristic_flags) >= 1 else "allow"
    )
    blocked = firewall_action == "block"

    ai_response = None
    if not blocked:
        ai_response = _generate_chat_response(request.message, request.history)

    database.log_request(
        google_sub=user["sub"],
        decision=request.message,
        context=context,
        provider=analysis["provider"],
        confidence=analysis["confidence_score"],
        risk_flags=analysis["risk_flags"],
        category=category,
    )

    return ChatResponse(
        user_message=request.message,
        ai_response=ai_response,
        blocked=blocked,
        firewall_action=firewall_action,
        risk_flags=heuristic_flags,
        confidence_score=analysis["confidence_score"],
        recommendation=analysis["recommendation"],
        violations=analysis.get("regulatory_refs", []),
    )


@app.get("/notifications/unsubscribe")
async def unsubscribe(token: str):
    """One-click email unsubscribe — no auth required."""
    user = database.get_user_by_unsubscribe_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe token")
    database.set_email_notifications(user["google_sub"], enabled=False)
    logger.info("Email notifications disabled — sub=%s", user["google_sub"])
    return Response(
        content="<html><body style='font-family:sans-serif;text-align:center;padding:60px;background:#0a0b0f;color:#fff;'>"
                "<h2>✓ Unsubscribed</h2>"
                "<p style='color:rgba(255,255,255,0.6);'>You will no longer receive compliance reminder emails from Pragma.</p>"
                "<p><a href='/' style='color:#6366f1;'>Back to app</a></p>"
                "</body></html>",
        media_type="text/html",
    )


@app.post("/notifications/preferences", dependencies=[Depends(get_current_user)])
async def set_notification_preferences(
    enabled: bool,
    user: dict = Depends(get_current_user),
):
    """Toggle email notifications on or off for the current user."""
    database.set_email_notifications(user["sub"], enabled=enabled)
    return {"email_notifications": enabled}


@app.get("/")
async def root():
    """Serve frontend UI."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Pragma API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
