"""FastAPI backend for ethical decision evaluation."""

import json
import os
from typing import Any, Dict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .llm_orchestrator import LLMOrchestrator
from .report_generator import generate_pdf
from .risk_detector import detect_all_risks

# Initialize FastAPI app
app = FastAPI(
    title="Ethical AI Decision Checker",
    description="API for evaluating decisions using ethical reasoning frameworks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = LLMOrchestrator()


class DecisionRequest(BaseModel):
    """Request schema for decision evaluation."""
    decision: str
    context: Dict[str, Any]


class EthicalAnalysis(BaseModel):
    """Response schema for ethical analysis."""
    kantian_analysis: str
    utilitarian_analysis: str
    virtue_ethics_analysis: str
    risk_flags: list[str]
    confidence_score: float
    recommendation: str
    provider: str = "unknown"


class ReportRequest(BaseModel):
    """Request schema for PDF report generation."""
    decision: str
    context: Dict[str, Any]
    analysis: Dict[str, Any]




@app.post("/evaluate-decision", response_model=EthicalAnalysis)
async def evaluate_decision(request: DecisionRequest) -> EthicalAnalysis:
    """
    Evaluate a decision using ethical reasoning frameworks.
    
    Returns analysis from Kantian ethics, Utilitarianism, and Virtue ethics,
    along with detected risk flags and recommendations.
    """
    if not request.decision or not request.decision.strip():
        raise HTTPException(status_code=400, detail="Decision cannot be empty")
    
    if not request.context:
        raise HTTPException(status_code=400, detail="Context cannot be empty")
    
    # Get LLM analysis via orchestrator (Claude → OpenAI fallback)
    llm_analysis = orchestrator.evaluate(request.decision, request.context)
    
    # Detect risks
    risk_flags = detect_all_risks(request.decision, request.context)
    
    # Merge with LLM-detected risks
    if llm_analysis.get("risk_flags"):
        risk_flags = sorted(list(set(risk_flags) | set(llm_analysis["risk_flags"])))
    
    # Ensure confidence score is valid
    confidence_score = llm_analysis.get("confidence_score", 0.5)
    if not isinstance(confidence_score, (int, float)) or confidence_score < 0 or confidence_score > 1:
        confidence_score = 0.5
    
    return EthicalAnalysis(
        kantian_analysis=llm_analysis.get("kantian_analysis", ""),
        utilitarian_analysis=llm_analysis.get("utilitarian_analysis", ""),
        virtue_ethics_analysis=llm_analysis.get("virtue_ethics_analysis", ""),
        risk_flags=risk_flags,
        confidence_score=confidence_score,
        recommendation=llm_analysis.get("recommendation", ""),
        provider=llm_analysis.get("provider", "unknown"),
    )


@app.post("/generate-report")
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


@app.get("/health-check")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ethical-ai-decision-checker",
        "providers": {
            "claude": orchestrator._claude is not None,
            "openai": orchestrator._openai is not None,
        }
    }


@app.get("/")
async def root():
    """Serve frontend UI."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Ethical AI Decision Checker API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
