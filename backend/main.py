"""FastAPI backend for ethical decision evaluation."""

import csv
import io
import os
import secrets
from typing import Any, Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
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


@asynccontextmanager
async def lifespan(*_):
    database.init_db()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Pragma",
    description="API for evaluating decisions using ethical reasoning frameworks",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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


class EthicalAnalysis(BaseModel):
    kantian_analysis: str
    utilitarian_analysis: str
    virtue_ethics_analysis: str
    risk_flags: list[str]
    confidence_score: float
    recommendation: str
    provider: str = "unknown"
    regulatory_refs: list[Dict[str, Any]] = []


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
        raise HTTPException(status_code=401, detail="Invalid Google credential")
    token = auth.create_session(user_info)
    return {
        "token":   token,
        "name":    user_info["name"],
        "picture": user_info["picture"],
    }


@app.post("/auth/guest")
async def guest_auth():
    """Create a temporary guest session — no sign-in required."""
    token, user_info = auth.create_guest_session()
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
    if not request.context:
        raise HTTPException(status_code=400, detail="Context cannot be empty")

    category = request.category if request.category in VALID_CATEGORIES else "other"
    analysis = _run_evaluation(request.decision, request.context, category)

    database.log_request(
        google_sub=user["sub"],
        decision=request.decision,
        context=request.context,
        provider=analysis["provider"],
        confidence=analysis["confidence_score"],
        risk_flags=analysis["risk_flags"],
        category=category,
    )

    return EthicalAnalysis(**analysis)


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


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

def _run_evaluation(decision: str, context: Dict[str, Any], category: str) -> Dict[str, Any]:
    """Shared evaluation logic used by single and batch endpoints."""
    llm_analysis = orchestrator.evaluate(decision, context)
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
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")   # handle BOM
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")
    if len(rows) > 100:
        raise HTTPException(status_code=400, detail="Batch limit is 100 rows")

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
            results.append({**row, "error": str(e), "risk_flags": "",
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
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guests cannot create organizations")
    return database.create_org(name, user["sub"])


@app.post("/orgs/join", dependencies=[Depends(get_current_user)])
async def join_org(req: JoinOrgRequest, user: dict = Depends(get_current_user)):
    """Join an organization using an invite code."""
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guests cannot join organizations")
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


# ── API key endpoints ──────────────────────────────────────────────────────────

class CreateAPIKeyRequest(BaseModel):
    label: str = "My API Key"


@app.post("/api-keys", dependencies=[Depends(get_current_user)])
async def create_api_key(req: CreateAPIKeyRequest, user: dict = Depends(get_current_user)):
    """Generate a new API key. The raw key is returned once — store it safely."""
    if user.get("is_guest") or user.get("via_api_key"):
        raise HTTPException(status_code=403, detail="Cannot create API keys from a guest or API session")
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


@app.get("/")
async def root():
    """Serve frontend UI."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Pragma API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
