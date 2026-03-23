"""LLM response validation and formatting."""

import json
from typing import Any, Dict


def validate_response_schema(data: Dict[str, Any]) -> bool:
    """Validate that response conforms to required schema."""
    required_fields = {
        "kantian_analysis": str,
        "utilitarian_analysis": str,
        "virtue_ethics_analysis": str,
        "risk_flags": list,
        "confidence_score": (int, float),
        "recommendation": str
    }
    
    for field, expected_type in required_fields.items():
        if field not in data:
            return False
        if not isinstance(data[field], expected_type):
            return False
    
    # Validate confidence score range
    if not (0 <= data["confidence_score"] <= 1):
        return False
    
    return True


def format_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure response is properly formatted and valid."""
    formatted = {
        "kantian_analysis": str(data.get("kantian_analysis", "")),
        "utilitarian_analysis": str(data.get("utilitarian_analysis", "")),
        "virtue_ethics_analysis": str(data.get("virtue_ethics_analysis", "")),
        "risk_flags": data.get("risk_flags", []),
        "confidence_score": min(1.0, max(0.0, float(data.get("confidence_score", 0.5)))),
        "recommendation": str(data.get("recommendation", ""))
    }
    
    # Ensure risk_flags is a list of strings
    if not isinstance(formatted["risk_flags"], list):
        formatted["risk_flags"] = []
    else:
        formatted["risk_flags"] = [str(flag) for flag in formatted["risk_flags"]]
    
    return formatted
