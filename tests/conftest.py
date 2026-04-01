"""Shared fixtures for all tests."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

# Stub API keys before importing backend modules
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")

import backend.database as db_module
from backend import auth


@pytest.fixture(autouse=True)
def isolated_db():
    """Give each test its own in-memory SQLite database."""
    test_engine = create_engine("sqlite:///:memory:")
    with patch.object(db_module, "_engine", test_engine):
        db_module.init_db()
        yield test_engine


@pytest.fixture()
def guest_token():
    token, _ = auth.create_guest_session()
    yield token
    auth.logout(token)


@pytest.fixture()
def auth_headers(guest_token):
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
