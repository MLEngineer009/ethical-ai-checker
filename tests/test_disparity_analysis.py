"""Tests for POST /disparity-analysis — EEOC 4/5ths disparate impact endpoint."""

import io
import csv
import pytest
from fastapi.testclient import TestClient


def _make_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def _csv_file(rows: list[dict], filename: str = "test.csv"):
    return ("file", (filename, io.BytesIO(_make_csv(rows)), "text/csv"))


# ── Test data ─────────────────────────────────────────────────────────────────

# White: 8/10 = 80%, Black: 3/10 = 30% (ratio 0.375), Hispanic: 5/10 = 50% (ratio 0.625)
ADVERSE_IMPACT_ROWS = (
    [{"race": "White",    "decision": "advance"}] * 8 +
    [{"race": "White",    "decision": "reject"}]  * 2 +
    [{"race": "Black",    "decision": "advance"}] * 3 +
    [{"race": "Black",    "decision": "reject"}]  * 7 +
    [{"race": "Hispanic", "decision": "advance"}] * 5 +
    [{"race": "Hispanic", "decision": "reject"}]  * 5
)

# White: 8/10 = 80%, Black: 7/10 = 70% → ratio 0.875 (above 80% threshold — no violation)
CLEAN_ROWS = (
    [{"race": "White", "decision": "advance"}] * 8 +
    [{"race": "White", "decision": "reject"}]  * 2 +
    [{"race": "Black", "decision": "advance"}] * 7 +
    [{"race": "Black", "decision": "reject"}]  * 3
)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_adverse_impact_detected(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(ADVERSE_IMPACT_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adverse_impact_found"] is True
    assert data["total_decisions"] == 30
    assert data["total_groups"] == 3
    violations = {v["group"] for v in data["violations"]}
    assert "Black" in violations
    assert "Hispanic" in violations
    assert "White" not in violations


def test_disparity_ratios_correct(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(ADVERSE_IMPACT_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    data = resp.json()
    groups = {g["group"]: g for g in data["groups"]}
    assert groups["White"]["selection_rate"] == pytest.approx(0.80, abs=0.01)
    assert groups["Black"]["selection_rate"] == pytest.approx(0.30, abs=0.01)
    assert groups["Black"]["disparity_ratio"] == pytest.approx(0.375, abs=0.01)
    assert groups["Black"]["status"] == "ADVERSE IMPACT"


def test_no_adverse_impact(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(CLEAN_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adverse_impact_found"] is False
    assert data["violations"] == []


def test_highest_group_never_flagged(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(ADVERSE_IMPACT_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    data = resp.json()
    violation_groups = {v["group"] for v in data["violations"]}
    assert data["highest_rate_group"] not in violation_groups


def test_missing_demographic_field(client: TestClient, auth_headers: dict):
    rows = [{"decision": "advance"}] * 6 + [{"decision": "reject"}] * 4
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(rows)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "race" in resp.json()["detail"]


def test_missing_outcome_field(client: TestClient, auth_headers: dict):
    rows = [{"race": "White"}] * 6 + [{"race": "Black"}] * 5
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(rows)],
        data={"demographic_field": "race", "outcome_field": "verdict", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "verdict" in resp.json()["detail"]


def test_empty_csv_rejected(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[("file", ("empty.csv", io.BytesIO(b"race,decision\n"), "text/csv"))],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_regulatory_refs_returned_on_violation(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(ADVERSE_IMPACT_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["adverse_impact_found"] is True
    assert len(data["regulatory_refs"]) > 0
    laws = [r["law"] for r in data["regulatory_refs"]]
    assert any("EEOC" in law for law in laws)
    assert any("NYC" in law for law in laws)


def test_regulatory_refs_empty_when_no_violation(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(CLEAN_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["adverse_impact_found"] is False
    assert data["regulatory_refs"] == []


def test_groups_below_minimum_sample_excluded(client: TestClient, auth_headers: dict):
    # Only 2 rows for "Asian" — below minimum of 5, should be excluded from analysis
    rows = (
        [{"race": "White", "decision": "advance"}] * 8 +
        [{"race": "White", "decision": "reject"}]  * 2 +
        [{"race": "Asian", "decision": "reject"}]  * 2
    )
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(rows)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    group_names = {g["group"] for g in resp.json()["groups"]}
    assert "Asian" not in group_names


def test_requires_auth(client: TestClient):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(ADVERSE_IMPACT_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
    )
    assert resp.status_code == 401


def test_summary_text_present(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/disparity-analysis",
        files=[_csv_file(ADVERSE_IMPACT_ROWS)],
        data={"demographic_field": "race", "outcome_field": "decision", "positive_outcome": "advance"},
        headers=auth_headers,
    )
    data = resp.json()
    assert "summary" in data
    assert len(data["summary"]) > 20
