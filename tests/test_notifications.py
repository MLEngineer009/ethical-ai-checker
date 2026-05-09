"""Tests for email_service and notifications modules."""

import pytest
from unittest.mock import patch, MagicMock


# ── email_service ──────────────────────────────────────────────────────────────

class TestEmailTemplates:
    def test_welcome_html_contains_name(self):
        from backend.email_service import welcome_html
        html = welcome_html(name="Alice", unsubscribe_token="tok123")
        assert "Alice" in html
        assert "EU AI Act" in html
        assert "tok123" in html

    def test_welcome_subject(self):
        from backend.email_service import welcome_subject
        assert "EU AI Act" in welcome_subject()

    def test_gap_reminder_html_shows_fails_and_partials(self):
        from backend.email_service import gap_reminder_html
        fails    = [{"article": "Art. 27", "title": "FRIA"}]
        partials = [{"article": "Art. 17", "title": "QMS"}]
        html = gap_reminder_html(
            name="Bob",
            system_name="LoanSight AI",
            company_name="Veridian Finance SA",
            fails=fails,
            partials=partials,
            score=0.57,
            days_unresolved=45,
            unsubscribe_token="tok456",
        )
        assert "LoanSight AI" in html
        assert "Art. 27" in html
        assert "Art. 17" in html
        assert "57%" in html
        assert "tok456" in html

    def test_gap_reminder_subject_singular(self):
        from backend.email_service import gap_reminder_subject
        subj = gap_reminder_subject("LoanSight AI", fail_count=1, partial_count=0)
        assert "1 compliance gap" in subj
        assert "LoanSight AI" in subj

    def test_gap_reminder_subject_plural(self):
        from backend.email_service import gap_reminder_subject
        subj = gap_reminder_subject("LoanSight AI", fail_count=2, partial_count=1)
        assert "3 compliance gaps" in subj

    def test_countdown_html_shows_days(self):
        from backend.email_service import countdown_html
        systems = [{"system_name": "LoanSight AI", "company_name": "Veridian", "score": 0.67}]
        html = countdown_html(
            name="Carol",
            days_remaining=82,
            systems=systems,
            unsubscribe_token="tok789",
        )
        assert "82" in html
        assert "LoanSight AI" in html
        assert "Carol" in html

    def test_countdown_subject_contains_days(self):
        from backend.email_service import countdown_subject
        subj = countdown_subject(82)
        assert "82" in subj

    def test_send_returns_false_when_key_missing(self):
        from backend.email_service import send
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("RESEND_API_KEY", None)
            result = send("test@example.com", "Subject", "<p>body</p>")
        assert result is False

    def test_send_returns_true_on_success(self):
        from backend.email_service import send
        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "abc123"}
        with patch("backend.email_service._resend_client", return_value=mock_resend):
            result = send("test@example.com", "Hello", "<p>hi</p>")
        assert result is True
        mock_resend.Emails.send.assert_called_once()

    def test_send_returns_false_on_api_error(self):
        from backend.email_service import send
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")
        with patch("backend.email_service._resend_client", return_value=mock_resend):
            result = send("test@example.com", "Hello", "<p>hi</p>")
        assert result is False


# ── notifications ──────────────────────────────────────────────────────────────

class TestNotificationsLogic:
    def _make_user(self):
        return {
            "google_sub":        "sub_test_001",
            "email":             "user@example.com",
            "name":              "Test User",
            "unsubscribe_token": "unsubtoken",
        }

    def test_send_welcome_sends_once(self):
        from backend import notifications
        user = self._make_user()
        with patch("backend.notifications.database.was_notification_sent", return_value=False), \
             patch("backend.notifications.email_service.send", return_value=True) as mock_send, \
             patch("backend.notifications.database.log_notification") as mock_log:
            result = notifications.send_welcome(user)
        assert result is True
        mock_send.assert_called_once()
        mock_log.assert_called_once_with(user["google_sub"], "welcome", user["email"])

    def test_send_welcome_skips_if_already_sent(self):
        from backend import notifications
        user = self._make_user()
        with patch("backend.notifications.database.was_notification_sent", return_value=True):
            result = notifications.send_welcome(user)
        assert result is False

    def test_send_gap_reminders_skips_ready_systems(self):
        from backend import notifications
        user = self._make_user()
        mock_results = [{"system_id": 1, "system_name": "Safe AI", "company_name": "Corp",
                         "risk_tier": "high", "score": 0.95, "verdict": "ready",
                         "articles": {}}]
        with patch("backend.notifications._compliance_for_user", return_value=mock_results):
            count = notifications.send_gap_reminders(user)
        assert count == 0

    def test_send_gap_reminders_sends_for_partial_system(self):
        from backend import notifications
        user = self._make_user()
        articles = {
            "art_27": {"status": "fail",    "title": "Article 27 — FRIA"},
            "art_17": {"status": "partial", "title": "Article 17 — QMS"},
            "art_4":  {"status": "pass",    "title": "Article 4 — AI Literacy"},
        }
        mock_results = [{"system_id": 2, "system_name": "RiskBot", "company_name": "Corp",
                         "risk_tier": "high", "score": 0.55, "verdict": "not_ready",
                         "articles": articles}]
        mock_system  = [{"system_id": 2, "system_name": "RiskBot", "created_at": "2025-01-01T00:00:00+00:00"}]
        with patch("backend.notifications._compliance_for_user", return_value=mock_results), \
             patch("backend.notifications.database.was_notification_sent", return_value=False), \
             patch("backend.notifications.database.get_ai_systems", return_value=mock_system), \
             patch("backend.notifications.email_service.send", return_value=True), \
             patch("backend.notifications.database.log_notification"):
            count = notifications.send_gap_reminders(user)
        assert count == 1

    def test_send_countdown_skips_non_high_risk_users(self):
        from backend import notifications
        user = self._make_user()
        mock_results = [{"system_id": 3, "risk_tier": "minimal", "score": 0.9}]
        with patch("backend.notifications._compliance_for_user", return_value=mock_results):
            result = notifications.send_countdown(user)
        assert result is False

    def test_send_countdown_sends_for_high_risk(self):
        from backend import notifications
        user = self._make_user()
        mock_results = [{"system_id": 4, "system_name": "LoanBot",
                         "company_name": "Corp", "risk_tier": "high", "score": 0.6}]
        with patch("backend.notifications._compliance_for_user", return_value=mock_results), \
             patch("backend.notifications.database.was_notification_sent", return_value=False), \
             patch("backend.notifications.email_service.send", return_value=True), \
             patch("backend.notifications.database.log_notification"):
            result = notifications.send_countdown(user)
        assert result is True

    def test_send_countdown_skips_if_sent_recently(self):
        from backend import notifications
        user = self._make_user()
        mock_results = [{"system_id": 4, "risk_tier": "high", "score": 0.6}]
        with patch("backend.notifications._compliance_for_user", return_value=mock_results), \
             patch("backend.notifications.database.was_notification_sent", return_value=True):
            result = notifications.send_countdown(user)
        assert result is False

    def test_run_all_dry_run(self):
        from backend import notifications
        mock_users = [self._make_user()]
        with patch("backend.notifications.database.init_db"), \
             patch("backend.notifications.database.get_all_notification_users",
                   return_value=mock_users):
            totals = notifications.run_all(dry_run=True)
        assert totals["users_checked"] == 1
        assert totals["welcome"] == 0
        assert totals["gap_reminder"] == 0

    def test_days_until_deadline_positive(self):
        from backend.notifications import _days_until_deadline
        days = _days_until_deadline()
        assert days >= 0
