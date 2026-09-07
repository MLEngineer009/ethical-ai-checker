"""
L1.5 Semantic Layer — catches contextual proxies that bypass exact keyword matching.

Uses sentence-transformers (all-MiniLM-L6-v2, ~80MB) for embedding-based
cosine similarity against a curated library of discriminatory proxy concepts.
Loaded lazily on first call; model cached in memory for the process lifetime.
"""

from __future__ import annotations
import logging
import numpy as np
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference concept library — proxy phrases by regulatory category
# ---------------------------------------------------------------------------

PROXY_CONCEPTS: Dict[str, Dict[str, Any]] = {
    "geographic_redlining": {
        "regulation": "Fair Housing Act / ECOA §202.6",
        "severity": "high",
        "phrases": [
            "historically underserved neighborhood",
            "inner city community",
            "urban core district",
            "transitional neighborhood",
            "that side of town",
            "gentrifying neighborhood",
            "high-crime area",
            "blighted district",
            "less desirable area",
            "low property value neighborhood",
            "economically distressed zone",
        ],
    },
    "age_discrimination": {
        "regulation": "ADEA / EU AI Act Art. 5(1)(b)",
        "severity": "high",
        "phrases": [
            "near retirement age",
            "close to pension eligibility",
            "will be retiring soon",
            "long tenure suggesting retirement",
            "overqualified for future growth trajectory",
            "lacks digital native skills",
            "not aligned with our young culture",
            "older than our typical candidate",
            "generational fit concerns",
        ],
    },
    "family_status": {
        "regulation": "ECOA §202.5(d) / Title VII",
        "severity": "high",
        "phrases": [
            "has young children at home",
            "childcare responsibilities may interfere",
            "family obligations conflict with schedule",
            "parental obligations limit availability",
            "pregnant or recently had a child",
            "maternity leave concerns",
            "primary caregiver duties",
            "spouse employed elsewhere",
        ],
    },
    "national_origin": {
        "regulation": "Title VII / ECOA §202.6",
        "severity": "high",
        "phrases": [
            "foreign accent may affect customer communication",
            "mother tongue is not English",
            "born overseas and may not understand local norms",
            "immigrant background",
            "cultural differences in professional expectations",
            "English as a second language limits effectiveness",
            "visa status creates uncertainty",
        ],
    },
    "disability": {
        "regulation": "ADA Title I / EU AI Act Art. 5",
        "severity": "high",
        "phrases": [
            "health issues affecting job performance",
            "medical condition limits capability",
            "physical limitations present",
            "mental health history concerning",
            "frequent accommodation needs",
            "chronic condition affecting attendance",
            "disability may impact productivity",
            "medical leave history suggests unreliability",
        ],
    },
    "religion": {
        "regulation": "Title VII / ECOA §202.6",
        "severity": "medium",
        "phrases": [
            "religious observance conflicts with work schedule",
            "prayer time requirements during core hours",
            "religious dietary restrictions complicate team events",
            "religious holiday observance affects availability",
            "faith-based lifestyle incompatible with company culture",
        ],
    },
    "race_ethnicity_proxy": {
        "regulation": "ECOA §202.6 / Fair Housing Act",
        "severity": "high",
        "phrases": [
            "cultural fit concerns with the current team",
            "comes from a very different background",
            "unconventional name may confuse clients",
            "grew up in a very different environment",
            "community values diverge from company culture",
            "communication style unfamiliar to our team",
        ],
    },
    "gender_proxy": {
        "regulation": "Title VII / EEOC / EU AI Act Art. 5",
        "severity": "high",
        "phrases": [
            "too emotional for leadership decisions",
            "work life balance priorities signal limited commitment",
            "leadership style not assertive enough",
            "communication too aggressive for support role",
            "not a strong fit for male dominated environment",
            "lacks gravitas expected in executive presence",
            "nurturing personality better suited for different role",
        ],
    },
}

# ---------------------------------------------------------------------------
# Model singleton — lazy loaded
# ---------------------------------------------------------------------------

_model = None
_reference_embeddings: Dict[str, np.ndarray] = {}  # category → matrix of phrase embeddings
_reference_phrases: Dict[str, List[str]] = {}


def _load_model():
    global _model, _reference_embeddings, _reference_phrases
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading semantic layer model (all-MiniLM-L6-v2)…")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        # Pre-compute reference embeddings for all concept phrases
        for category, meta in PROXY_CONCEPTS.items():
            phrases = meta["phrases"]
            _reference_phrases[category] = phrases
            _reference_embeddings[category] = _model.encode(
                phrases, convert_to_numpy=True, normalize_embeddings=True
            )
        logger.info("Semantic layer ready — %d proxy concept categories loaded", len(PROXY_CONCEPTS))
    except ImportError:
        logger.warning("sentence-transformers not installed — semantic layer disabled")
        _model = None
    except Exception as exc:
        logger.error("Semantic layer failed to load: %s", exc)
        _model = None
    return _model


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between a single vector and a matrix of row vectors."""
    return (b @ a).flatten()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_semantic_proxies(
    text: str,
    threshold: float = 0.72,
) -> List[Dict[str, Any]]:
    """
    Embed `text` and compare against all reference proxy concept phrases.

    Returns a list of semantic flags (one per triggered category), each with:
      - category: str
      - regulation: str
      - severity: str
      - similarity_score: float (0–1, highest matched phrase)
      - matched_concept: str (the reference phrase that triggered it)
    """
    if not text or not text.strip():
        return []

    model = _load_model()
    if model is None:
        return []

    try:
        query_embedding = model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )
    except Exception as exc:
        logger.error("Semantic layer encode error: %s", exc)
        return []

    flags = []
    for category, ref_matrix in _reference_embeddings.items():
        sims = _cosine_similarity(query_embedding, ref_matrix)
        max_idx = int(np.argmax(sims))
        max_sim = float(sims[max_idx])
        if max_sim >= threshold:
            meta = PROXY_CONCEPTS[category]
            flags.append({
                "category": category,
                "regulation": meta["regulation"],
                "severity": meta["severity"],
                "similarity_score": round(max_sim, 4),
                "matched_concept": _reference_phrases[category][max_idx],
                "layer": "L1.5_semantic",
            })

    # Sort by similarity descending
    flags.sort(key=lambda f: f["similarity_score"], reverse=True)
    return flags


def is_available() -> bool:
    """Returns True if sentence-transformers loaded successfully."""
    return _load_model() is not None
