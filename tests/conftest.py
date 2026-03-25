"""Shared fixtures for all tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Stub out API keys before importing backend modules
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")

import backend.database as db_module
from backend import auth


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Redirect all DB writes to a temp file for each test."""
    tmp_db = tmp_path / "test.db"
    with patch.object(db_module, "DB_PATH", tmp_db):
        db_module.init_db()
        yield tmp_db


@pytest.fixture()
def guest_token():
    """Create a real guest session and return its token."""
    token, _ = auth.create_guest_session()
    yield token
    auth.logout(token)


@pytest.fixture()
def auth_headers(guest_token):
    """Authorization headers using a live guest session."""
    return {"Authorization": f"Bearer {guest_token}"}


@pytest.fixture()
def client():
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def valid_analysis():
    return {
        "kantian_analysis": "This action can be universalized.",
        "utilitarian_analysis": "Overall positive outcomes.",
        "virtue_ethics_analysis": "Reflects virtuous character.",
        "risk_flags": ["bias"],
        "confidence_score": 0.8,
        "recommendation": "Proceed with caution.",
        "provider": "mock",
    }
