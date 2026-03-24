"""Auth via Google SSO — verifies Google ID tokens, issues session tokens."""

import os
import secrets
from typing import Dict, Optional

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# In-memory session store: token -> user info dict
_sessions: Dict[str, dict] = {}


def verify_google_token(credential: str) -> Optional[dict]:
    """
    Verify a Google ID token from the frontend.
    Returns user info dict on success, None on failure.
    """
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID is not set in environment")
    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        return {
            "sub":      info["sub"],        # stable Google user ID
            "name":     info.get("name", "User"),
            "picture":  info.get("picture", ""),
        }
    except Exception:
        return None


def create_session(user_info: dict) -> str:
    """Create a session token and store user info. Returns token."""
    token = secrets.token_hex(32)
    _sessions[token] = user_info
    return token


def create_guest_session() -> tuple[str, dict]:
    """Create an anonymous guest session. Returns (token, user_info)."""
    guest_id = secrets.token_hex(8)
    user_info = {
        "sub":      f"guest_{guest_id}",
        "name":     "Guest",
        "picture":  "",
        "is_guest": True,
    }
    token = secrets.token_hex(32)
    _sessions[token] = user_info
    return token, user_info


def get_user(token: str) -> Optional[dict]:
    """Return user dict for a valid token, or None."""
    return _sessions.get(token)


def logout(token: str) -> None:
    _sessions.pop(token, None)
