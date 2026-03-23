"""Integration tests for ethical decision evaluation API."""

import pytest
from fastapi.testclient import TestClient
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health-check")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_evaluate_decision_hiring_bias():
    """Test detection of hiring bias based on gender."""
    response = client.post("/evaluate-decision", json={
        "decision": "Reject job candidate",
        "context": {
            "experience": 5,
            "education": "non-elite",
            "gender": "female"
        }
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "kantian_analysis" in data
    assert "utilitarian_analysis" in data
    assert "virtue_ethics_analysis" in data
    assert isinstance(data["risk_flags"], list)
    assert "bias" in data["risk_flags"]
    assert 0 <= data["confidence_score"] <= 1
    assert "recommendation" in data


def test_evaluate_decision_loan_discrimination():
    """Test detection of loan discrimination based on zip code."""
    response = client.post("/evaluate-decision", json={
        "decision": "Reject loan application",
        "context": {
            "credit_score": 720,
            "income": 75000,
            "zip_code": "90210"
        }
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "bias" in data["risk_flags"]
    assert len(data["risk_flags"]) > 0


def test_evaluate_decision_missing_decision():
    """Test error handling for missing decision."""
    response = client.post("/evaluate-decision", json={
        "decision": "",
        "context": {"experience": 5}
    })
    
    assert response.status_code == 400


def test_evaluate_decision_missing_context():
    """Test error handling for missing context."""
    response = client.post("/evaluate-decision", json={
        "decision": "Reject candidate",
        "context": {}
    })
    
    assert response.status_code == 400


def test_response_schema():
    """Test that response conforms to schema."""
    response = client.post("/evaluate-decision", json={
        "decision": "Approve promotion",
        "context": {
            "performance": "excellent",
            "years_employed": 3
        }
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields exist
    required_fields = [
        "kantian_analysis",
        "utilitarian_analysis", 
        "virtue_ethics_analysis",
        "risk_flags",
        "confidence_score",
        "recommendation"
    ]
    
    for field in required_fields:
        assert field in data
    
    # Verify types
    assert isinstance(data["kantian_analysis"], str)
    assert isinstance(data["utilitarian_analysis"], str)
    assert isinstance(data["virtue_ethics_analysis"], str)
    assert isinstance(data["risk_flags"], list)
    assert isinstance(data["confidence_score"], (int, float))
    assert isinstance(data["recommendation"], str)
