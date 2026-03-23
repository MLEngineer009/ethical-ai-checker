"""Risk detection heuristics for bias, fairness, and discrimination."""

import re
from typing import List

# Sensitive attributes that trigger bias flags
SENSITIVE_ATTRIBUTES = {
    "gender", "sex", "race", "ethnicity", "color", "national_origin",
    "age", "disability", "religion", "veteran_status", "sexual_orientation",
    "marital_status", "zip_code", "postcode", "neighborhood",
    "mother_tongue", "accent", "appearance", "height", "weight"
}

# Keywords that suggest exclusionary or harmful reasoning
HARM_KEYWORDS = {
    "exclude", "eliminate", "reject", "ban", "forbid", "prevent",
    "block", "disqualify", "unfit", "unsuitable", "unworthy"
}

TRANSPARENCY_KEYWORDS = {
    "assume", "likely", "probably", "might", "could", "unclear",
    "vague", "unspecified", "unknown", "undefined"
}


def detect_bias_risks(context: dict) -> List[str]:
    """Detect bias risks based on presence of sensitive attributes."""
    flags = []
    context_str = str(context).lower()
    
    for attr in SENSITIVE_ATTRIBUTES:
        if attr.lower() in context_str:
            flags.append("bias")
            break
    
    return flags


def detect_fairness_risks(decision: str, context: dict) -> List[str]:
    """Detect fairness issues based on decision reasoning."""
    flags = []
    decision_lower = decision.lower()
    
    # Check for exclusionary language
    if any(keyword in decision_lower for keyword in HARM_KEYWORDS):
        flags.append("fairness")
    
    # Check for group-based reasoning
    if any(group in decision_lower for group in ["all ", "any ", "every "]):
        flags.append("fairness")
    
    return flags


def detect_transparency_risks(decision: str, context: dict) -> List[str]:
    """Detect lack of transparency in reasoning."""
    flags = []
    decision_lower = decision.lower()
    
    if any(keyword in decision_lower for keyword in TRANSPARENCY_KEYWORDS):
        flags.append("transparency")
    
    # Check if context is too sparse
    if isinstance(context, dict) and len(context) < 2:
        flags.append("transparency")
    
    return flags


def detect_discrimination_risks(decision: str, context: dict) -> List[str]:
    """Detect potential discrimination patterns."""
    flags = []
    decision_lower = decision.lower()
    
    # Exclusionary patterns
    exclusionary_patterns = [
        r"based on.*(?:gender|race|age|religion)",
        r"(?:gender|race|age|religion).*based",
        r"not.*(?:similar to|like|matching)"
    ]
    
    for pattern in exclusionary_patterns:
        if re.search(pattern, decision_lower):
            flags.append("discrimination")
            break
    
    return flags


def detect_all_risks(decision: str, context: dict) -> List[str]:
    """Detect all risk flags for a decision."""
    all_flags = set()
    
    all_flags.update(detect_bias_risks(context))
    all_flags.update(detect_fairness_risks(decision, context))
    all_flags.update(detect_transparency_risks(decision, context))
    all_flags.update(detect_discrimination_risks(decision, context))
    
    return sorted(list(all_flags))
