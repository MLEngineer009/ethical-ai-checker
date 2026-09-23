"""Unit tests for backend/database.py — uses isolated temp DB via conftest."""

import json
import pytest
from backend import database as db


class TestAnonId:
    def test_deterministic(self):
        assert db.anon_id("user123") == db.anon_id("user123")

    def test_different_inputs_different_outputs(self):
        assert db.anon_id("user1") != db.anon_id("user2")

    def test_length_is_16(self):
        assert len(db.anon_id("anything")) == 16

    def test_does_not_contain_input(self):
        result = db.anon_id("super-secret-sub")
        assert "super-secret-sub" not in result

    def test_guest_and_google_differ(self):
        assert db.anon_id("guest_abc") != db.anon_id("google-abc")


class TestInitDb:
    def test_init_creates_tables(self):
        """init_db called by conftest fixture; verify both tables exist."""
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(db._engine)
        tables = insp.get_table_names()
        assert "request_logs" in tables
        assert "analysis_feedback" in tables

    def test_init_is_idempotent(self):
        """Calling init_db twice should not raise."""
        db.init_db()
        db.init_db()


class TestLogRequest:
    def test_log_stores_entry(self):
        db.log_request(
            google_sub="sub-001",
            decision="Reject candidate",
            context={"gender": "female", "experience": 5},
            provider="claude",
            confidence=0.85,
            risk_flags=["bias", "fairness"],
        )
        stats = db.get_stats("sub-001")
        assert stats["total_requests"] == 1

    def test_log_stores_context_keys_not_values(self):
        db.log_request(
            google_sub="sub-002",
            decision="Approve loan",
            context={"income": 70000, "zip_code": "10001"},
            provider="openai",
            confidence=0.7,
            risk_flags=["bias"],
        )
        stats = db.get_stats("sub-002")
        entry = stats["history"][0]
        assert "income" in entry["context_keys"]
        assert "zip_code" in entry["context_keys"]
        # Values must NOT be stored
        assert "70000" not in str(entry)
        assert "10001" not in str(entry)

    def test_log_stores_word_count_not_text(self):
        decision = "Reject the job application today"
        db.log_request(
            google_sub="sub-003",
            decision=decision,
            context={"x": 1, "y": 2},
            provider="mock",
            confidence=0.0,
            risk_flags=[],
        )
        stats = db.get_stats("sub-003")
        entry = stats["history"][0]
        assert entry["decision_words"] == len(decision.split())
        assert decision not in str(stats)

    def test_log_confidence_rounded(self):
        db.log_request("sub-004", "decision text", {"a": 1, "b": 2}, "claude", 0.123456, [])
        stats = db.get_stats("sub-004")
        assert stats["history"][0]["confidence"] == round(0.123456, 3)

    def test_multiple_logs_accumulate(self):
        for i in range(3):
            db.log_request(f"sub-005", f"decision {i}", {"x": i, "y": i}, "claude", 0.5, [])
        stats = db.get_stats("sub-005")
        assert stats["total_requests"] == 3

    def test_different_users_isolated(self):
        db.log_request("user-A", "decision", {"x": 1, "y": 2}, "claude", 0.9, [])
        db.log_request("user-B", "decision", {"x": 1, "y": 2}, "openai", 0.6, [])
        assert db.get_stats("user-A")["total_requests"] == 1
        assert db.get_stats("user-B")["total_requests"] == 1


class TestGetStats:
    def test_unknown_user_returns_zero(self):
        stats = db.get_stats("nobody")
        assert stats["total_requests"] == 0
        assert stats["history"] == []

    def test_history_entry_structure(self):
        db.log_request("sub-h", "test", {"a": 1, "b": 2}, "claude", 0.75, ["bias"])
        history = db.get_stats("sub-h")["history"]
        entry = history[0]
        required_keys = {
            "timestamp", "context_keys", "decision_words",
            "provider", "confidence", "risk_count", "risk_categories",
        }
        assert required_keys.issubset(entry.keys())

    def test_risk_categories_stored_as_list(self):
        db.log_request("sub-rc", "test", {"a": 1, "b": 2}, "claude", 0.5, ["bias", "fairness"])
        entry = db.get_stats("sub-rc")["history"][0]
        assert isinstance(entry["risk_categories"], list)
        assert "bias" in entry["risk_categories"]

    def test_history_capped_at_20(self):
        for i in range(25):
            db.log_request("sub-cap", f"d{i}", {f"k{i}": i, f"j{i}": i}, "mock", 0.5, [])
        stats = db.get_stats("sub-cap")
        assert len(stats["history"]) == 20
        assert stats["total_requests"] == 20  # only last 20 returned


class TestLogFeedback:
    def test_thumbs_up_stored(self):
        db.log_feedback("fb-user-1", 1, "hiring", "pragma", "v1", 0.85, ["bias"])
        stats = db.get_feedback_stats()
        assert stats["total"] >= 1
        assert stats["by_category"]["hiring"]["up"] >= 1

    def test_thumbs_down_stored(self):
        db.log_feedback("fb-user-2", -1, "finance", "claude", "unknown", 0.6, [])
        stats = db.get_feedback_stats()
        assert stats["by_category"]["finance"]["down"] >= 1

    def test_invalid_rating_raises(self):
        with pytest.raises(ValueError):
            db.log_feedback("fb-user-3", 0, "other", "claude", "unknown", 0.5, [])

    def test_approval_rate_computed(self):
        db.log_feedback("fb-u4", 1, "healthcare", "claude", "unknown", 0.9, [])
        db.log_feedback("fb-u5", 1, "healthcare", "claude", "unknown", 0.8, [])
        db.log_feedback("fb-u6", -1, "healthcare", "claude", "unknown", 0.4, [])
        stats = db.get_feedback_stats()
        cat = stats["by_category"]["healthcare"]
        assert cat["approval_rate"] == round(2 / 3, 3)

    def test_by_provider_tracked(self):
        db.log_feedback("fb-u7", 1, "other", "pragma", "v1", 0.95, [])
        stats = db.get_feedback_stats()
        assert "pragma" in stats["by_provider"]

    def test_empty_returns_zero(self):
        # Fresh DB from conftest — no feedback yet
        stats = db.get_feedback_stats()
        assert stats["total"] == 0


class TestGDPRDeleteExport:
    """GDPR Art. 17 (delete_user_data) and Art. 20 (export_user_data).

    Both previously crashed with AttributeError on nonexistent columns
    (api_keys.owner_anon_id, ai_systems.owner_sub) — these tests lock the fix.
    """

    SUB = "google-gdpr-test-sub"
    EMAIL = "gdpr-test@example.com"

    def _seed_user(self):
        db.upsert_user(self.SUB, self.EMAIL, "GDPR Test")
        db.create_api_key(self.SUB, "test-key")
        db.create_ai_system(self.SUB, "Hiring Screener", "Acme Corp", "high", "screening resumes")

    @staticmethod
    def _count(table, column, value):
        from sqlalchemy import select, func
        with db._engine.connect() as conn:
            return conn.execute(
                select(func.count()).select_from(table).where(column == value)
            ).scalar()

    def test_delete_user_data_removes_all_pii_rows(self):
        self._seed_user()
        aid = db.anon_id(self.SUB)
        # Sanity: rows exist before deletion
        assert db.get_user_by_google_sub(self.SUB) is not None
        assert len(db.get_api_keys(self.SUB)) == 1
        assert self._count(db.ai_systems, db.ai_systems.c.anon_id, aid) == 1

        db.delete_user_data(self.SUB)  # must not raise

        assert db.get_user_by_google_sub(self.SUB) is None
        assert len(db.get_api_keys(self.SUB)) == 0
        assert self._count(db.ai_systems, db.ai_systems.c.anon_id, aid) == 0

    def test_delete_user_data_is_idempotent(self):
        self._seed_user()
        db.delete_user_data(self.SUB)
        db.delete_user_data(self.SUB)  # second call must not raise

    def test_delete_user_data_does_not_touch_other_users(self):
        self._seed_user()
        other = "google-gdpr-other-sub"
        db.upsert_user(other, "other@example.com", "Other User")
        db.create_api_key(other, "other-key")
        other_aid = db.anon_id(other)

        db.delete_user_data(self.SUB)

        assert db.get_user_by_google_sub(other) is not None
        assert len(db.get_api_keys(other)) == 1
        # Other user's data untouched
        assert db.get_user_by_google_sub(self.SUB) is None

    def test_export_user_data_returns_snapshot(self):
        self._seed_user()

        snap = db.export_user_data(self.SUB)  # must not raise

        assert snap["profile"]["email"] == self.EMAIL
        assert snap["profile"]["name"] == "GDPR Test"
        assert len(snap["ai_systems"]) == 1
        assert snap["ai_systems"][0]["name"] == "Hiring Screener"
        assert snap["ai_systems"][0]["risk_tier"] == "high"
        assert "exported_at" in snap

    def test_export_user_data_unknown_user_returns_empty_snapshot(self):
        snap = db.export_user_data("google-nonexistent-sub")
        assert snap["profile"]["email"] is None
        assert snap["ai_systems"] == []
        assert snap["total_evaluations"] == 0
