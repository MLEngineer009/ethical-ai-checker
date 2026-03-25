"""Unit tests for backend/auth.py."""

import pytest
from unittest.mock import patch, MagicMock
from backend import auth


class TestSessionManagement:
    def test_create_and_retrieve_session(self):
        user = {"sub": "123", "name": "Alice", "picture": "https://example.com/pic.jpg"}
        token = auth.create_session(user)
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes hex
        assert auth.get_user(token) == user

    def test_tokens_are_unique(self):
        user = {"sub": "abc", "name": "Bob", "picture": ""}
        t1 = auth.create_session(user)
        t2 = auth.create_session(user)
        assert t1 != t2

    def test_get_user_invalid_token(self):
        assert auth.get_user("not-a-real-token") is None

    def test_logout_removes_session(self):
        user = {"sub": "xyz", "name": "Carol", "picture": ""}
        token = auth.create_session(user)
        auth.logout(token)
        assert auth.get_user(token) is None

    def test_logout_nonexistent_token_no_error(self):
        auth.logout("does-not-exist")  # should not raise


class TestGuestSession:
    def test_returns_token_and_user_info(self):
        token, user_info = auth.create_guest_session()
        assert isinstance(token, str)
        assert isinstance(user_info, dict)

    def test_guest_user_info_structure(self):
        _, user_info = auth.create_guest_session()
        assert user_info["name"] == "Guest"
        assert user_info["is_guest"] is True
        assert user_info["sub"].startswith("guest_")
        assert user_info["picture"] == ""

    def test_guest_token_is_valid_session(self):
        token, user_info = auth.create_guest_session()
        retrieved = auth.get_user(token)
        assert retrieved == user_info

    def test_multiple_guests_get_different_tokens(self):
        t1, _ = auth.create_guest_session()
        t2, _ = auth.create_guest_session()
        assert t1 != t2

    def test_multiple_guests_get_different_subs(self):
        _, u1 = auth.create_guest_session()
        _, u2 = auth.create_guest_session()
        assert u1["sub"] != u2["sub"]


class TestVerifyGoogleToken:
    def test_returns_none_when_no_client_id(self):
        with patch.object(auth, "GOOGLE_CLIENT_ID", ""):
            with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID"):
                auth.verify_google_token("fake-credential")

    def test_returns_user_info_on_valid_token(self):
        mock_info = {
            "sub": "google-sub-123",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }
        with patch.object(auth, "GOOGLE_CLIENT_ID", "real-client-id"):
            with patch("backend.auth.id_token.verify_oauth2_token", return_value=mock_info):
                result = auth.verify_google_token("valid-token")
        assert result == {
            "sub": "google-sub-123",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }

    def test_returns_none_on_invalid_token(self):
        with patch.object(auth, "GOOGLE_CLIENT_ID", "real-client-id"):
            with patch("backend.auth.id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
                result = auth.verify_google_token("bad-credential")
        assert result is None

    def test_missing_optional_fields_use_defaults(self):
        mock_info = {"sub": "abc"}  # no name or picture
        with patch.object(auth, "GOOGLE_CLIENT_ID", "real-client-id"):
            with patch("backend.auth.id_token.verify_oauth2_token", return_value=mock_info):
                result = auth.verify_google_token("token")
        assert result["name"] == "User"
        assert result["picture"] == ""
