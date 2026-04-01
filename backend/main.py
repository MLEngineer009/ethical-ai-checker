"""FastAPI backend for ethical decision evaluation."""

import os
from typing import Any, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .llm_orchestrator import LLMOrchestrator
from .report_generator import generate_pdf
from .risk_detector import detect_all_risks
from . import auth
from . import database


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
    user = auth.get_user(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


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

    llm_analysis = orchestrator.evaluate(request.decision, request.context)
    risk_flags = detect_all_risks(request.decision, request.context)

    if llm_analysis.get("risk_flags"):
        risk_flags = sorted(list(set(risk_flags) | set(llm_analysis["risk_flags"])))

    confidence_score = llm_analysis.get("confidence_score", 0.5)
    if not isinstance(confidence_score, (int, float)) or confidence_score < 0 or confidence_score > 1:
        confidence_score = 0.5

    category = request.category if request.category in VALID_CATEGORIES else "other"

    # Log metadata — no PII, no decision text, no context values
    database.log_request(
        google_sub=user["sub"],
        decision=request.decision,
        context=request.context,
        provider=llm_analysis.get("provider", "unknown"),
        confidence=confidence_score,
        risk_flags=risk_flags,
        category=category,
    )

    return EthicalAnalysis(
        kantian_analysis=llm_analysis.get("kantian_analysis", ""),
        utilitarian_analysis=llm_analysis.get("utilitarian_analysis", ""),
        virtue_ethics_analysis=llm_analysis.get("virtue_ethics_analysis", ""),
        risk_flags=risk_flags,
        confidence_score=confidence_score,
        recommendation=llm_analysis.get("recommendation", ""),
        provider=llm_analysis.get("provider", "unknown"),
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


@app.get("/")
async def root():
    """Serve frontend UI."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Pragma API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
