"""Unit tests for org and API key functions in backend/database.py."""

import pytest
from backend import database as db


# ── Organization tests ─────────────────────────────────────────────────────────

class TestCreateOrg:
    def test_returns_org_id(self):
        result = db.create_org("Test Org", "user-001")
        assert "org_id" in result
        assert isinstance(result["org_id"], int)

    def test_returns_name(self):
        result = db.create_org("Acme Corp", "user-002")
        assert result["name"] == "Acme Corp"

    def test_returns_invite_code(self):
        result = db.create_org("My Org", "user-003")
        assert "invite_code" in result
        assert len(result["invite_code"]) > 6

    def test_different_orgs_have_different_invite_codes(self):
        a = db.create_org("Org A", "user-004")
        b = db.create_org("Org B", "user-005")
        assert a["invite_code"] != b["invite_code"]

    def test_creator_becomes_member(self):
        result = db.create_org("Solo Org", "user-006")
        orgs = db.get_my_orgs("user-006")
        org_ids = [o["org_id"] for o in orgs]
        assert result["org_id"] in org_ids

    def test_creator_has_owner_role(self):
        result = db.create_org("Owner Org", "user-007")
        orgs = db.get_my_orgs("user-007")
        org = next(o for o in orgs if o["org_id"] == result["org_id"])
        assert org["role"] == "owner"

    def test_owner_sees_invite_code_in_my_orgs(self):
        created = db.create_org("Invite Org", "user-008")
        orgs = db.get_my_orgs("user-008")
        org = next(o for o in orgs if o["org_id"] == created["org_id"])
        assert org["invite_code"] == created["invite_code"]


class TestGetOrgByInvite:
    def test_valid_code_returns_org(self):
        created = db.create_org("Findable Org", "user-010")
        found = db.get_org_by_invite(created["invite_code"])
        assert found is not None
        assert found["org_id"] == created["org_id"]

    def test_invalid_code_returns_none(self):
        assert db.get_org_by_invite("not-a-real-code") is None

    def test_returned_name_matches(self):
        created = db.create_org("Named Org", "user-011")
        found = db.get_org_by_invite(created["invite_code"])
        assert found["name"] == "Named Org"


class TestJoinOrg:
    def test_new_member_returns_true(self):
        created = db.create_org("Join Org", "owner-001")
        result = db.join_org(created["org_id"], "member-001")
        assert result is True

    def test_duplicate_join_returns_false(self):
        created = db.create_org("Join Org 2", "owner-002")
        db.join_org(created["org_id"], "member-002")
        assert db.join_org(created["org_id"], "member-002") is False

    def test_joined_member_appears_in_my_orgs(self):
        created = db.create_org("Member Org", "owner-003")
        db.join_org(created["org_id"], "member-003")
        orgs = db.get_my_orgs("member-003")
        assert any(o["org_id"] == created["org_id"] for o in orgs)

    def test_member_role_is_member(self):
        created = db.create_org("Role Org", "owner-004")
        db.join_org(created["org_id"], "member-004")
        orgs = db.get_my_orgs("member-004")
        org = next(o for o in orgs if o["org_id"] == created["org_id"])
        assert org["role"] == "member"

    def test_member_does_not_see_invite_code(self):
        created = db.create_org("Hidden Invite Org", "owner-005")
        db.join_org(created["org_id"], "member-005")
        orgs = db.get_my_orgs("member-005")
        org = next(o for o in orgs if o["org_id"] == created["org_id"])
        assert org["invite_code"] is None


class TestGetMyOrgs:
    def test_new_user_has_empty_list(self):
        assert db.get_my_orgs("nobody-here") == []

    def test_user_in_multiple_orgs(self):
        db.create_org("Org X", "multi-user")
        db.create_org("Org Y", "multi-user")
        orgs = db.get_my_orgs("multi-user")
        assert len(orgs) >= 2

    def test_different_users_see_different_orgs(self):
        db.create_org("Private Org A", "user-private-a")
        db.create_org("Private Org B", "user-private-b")
        orgs_a = {o["name"] for o in db.get_my_orgs("user-private-a")}
        orgs_b = {o["name"] for o in db.get_my_orgs("user-private-b")}
        assert "Private Org A" in orgs_a
        assert "Private Org B" not in orgs_a
        assert "Private Org B" in orgs_b


class TestGetOrgHistory:
    def test_non_member_returns_empty_list(self):
        created = db.create_org("History Org", "hist-owner")
        result = db.get_org_history(created["org_id"], "non-member")
        assert result == []

    def test_member_can_see_own_logs(self):
        created = db.create_org("Shared Org", "hist-owner-2")
        db.log_request("hist-owner-2", "test decision", {"a": 1, "b": 2}, "claude", 0.8, ["bias"])
        rows = db.get_org_history(created["org_id"], "hist-owner-2")
        assert len(rows) >= 1

    def test_owner_can_see_member_logs(self):
        created = db.create_org("Cross Org", "cross-owner")
        db.join_org(created["org_id"], "cross-member")
        db.log_request("cross-member", "member decision", {"x": 1, "y": 2}, "openai", 0.7, [])
        rows = db.get_org_history(created["org_id"], "cross-owner")
        assert len(rows) >= 1

    def test_history_entry_has_is_self_flag(self):
        created = db.create_org("Self Flag Org", "self-owner")
        db.log_request("self-owner", "my decision", {"a": 1, "b": 2}, "claude", 0.9, [])
        rows = db.get_org_history(created["org_id"], "self-owner")
        assert rows[0]["is_self"] is True


# ── API key tests ──────────────────────────────────────────────────────────────

class TestCreateApiKey:
    def test_returns_raw_key(self):
        result = db.create_api_key("key-user-001", "My Key")
        assert "key" in result
        assert result["key"].startswith("pragma_")

    def test_returns_prefix(self):
        result = db.create_api_key("key-user-002", "Test Key")
        assert "key_prefix" in result
        assert result["key"].startswith(result["key_prefix"])

    def test_returns_key_id(self):
        result = db.create_api_key("key-user-003", "ID Key")
        assert "key_id" in result
        assert isinstance(result["key_id"], int)

    def test_label_stored(self):
        db.create_api_key("key-user-004", "Prod Key")
        keys = db.get_api_keys("key-user-004")
        assert keys[0]["label"] == "Prod Key"

    def test_raw_keys_differ(self):
        k1 = db.create_api_key("key-user-005", "K1")
        k2 = db.create_api_key("key-user-005", "K2")
        assert k1["key"] != k2["key"]


class TestGetApiKeys:
    def test_new_user_has_no_keys(self):
        assert db.get_api_keys("fresh-key-user") == []

    def test_key_entry_has_required_fields(self):
        db.create_api_key("fields-user", "Test")
        keys = db.get_api_keys("fields-user")
        for field in ("key_id", "key_prefix", "label", "created_at", "last_used",
                      "calls_total", "calls_month", "active"):
            assert field in keys[0]

    def test_newly_created_key_is_active(self):
        db.create_api_key("active-user", "Active Key")
        assert db.get_api_keys("active-user")[0]["active"] is True

    def test_raw_key_not_in_listing(self):
        created = db.create_api_key("safe-user", "Safe Key")
        keys = db.get_api_keys("safe-user")
        raw_key = created["key"]
        for k in keys:
            assert raw_key not in str(k)

    def test_user_isolation(self):
        db.create_api_key("user-alpha", "Alpha Key")
        db.create_api_key("user-beta", "Beta Key")
        alpha_keys = db.get_api_keys("user-alpha")
        beta_keys = db.get_api_keys("user-beta")
        assert len(alpha_keys) == 1
        assert len(beta_keys) == 1
        assert alpha_keys[0]["label"] == "Alpha Key"
        assert beta_keys[0]["label"] == "Beta Key"


class TestRevokeApiKey:
    def test_revoke_returns_true(self):
        created = db.create_api_key("revoke-user", "Revokable")
        assert db.revoke_api_key(created["key_id"], "revoke-user") is True

    def test_revoked_key_is_inactive(self):
        created = db.create_api_key("revoke-user-2", "Revokable 2")
        db.revoke_api_key(created["key_id"], "revoke-user-2")
        keys = db.get_api_keys("revoke-user-2")
        assert keys[0]["active"] is False

    def test_wrong_user_cannot_revoke(self):
        created = db.create_api_key("owner-user", "Protected Key")
        assert db.revoke_api_key(created["key_id"], "attacker-user") is False

    def test_wrong_user_key_stays_active(self):
        created = db.create_api_key("owner-user-2", "Still Active")
        db.revoke_api_key(created["key_id"], "bad-actor")
        keys = db.get_api_keys("owner-user-2")
        assert keys[0]["active"] is True


class TestVerifyApiKey:
    def test_valid_key_returns_dict(self):
        created = db.create_api_key("verify-user", "Verify Key")
        result = db.verify_api_key(created["key"])
        assert result is not None

    def test_invalid_key_returns_none(self):
        assert db.verify_api_key("pragma_fakekeythatdoesnotexist") is None

    def test_revoked_key_returns_none(self):
        created = db.create_api_key("verify-user-2", "Revokable Verify")
        db.revoke_api_key(created["key_id"], "verify-user-2")
        assert db.verify_api_key(created["key"]) is None

    def test_verify_increments_calls_total(self):
        created = db.create_api_key("usage-user", "Usage Key")
        db.verify_api_key(created["key"])
        db.verify_api_key(created["key"])
        keys = db.get_api_keys("usage-user")
        assert keys[0]["calls_total"] == 2

    def test_verify_updates_last_used(self):
        created = db.create_api_key("last-used-user", "Tracking Key")
        db.verify_api_key(created["key"])
        keys = db.get_api_keys("last-used-user")
        assert keys[0]["last_used"] is not None

    def test_verify_returns_anon_id(self):
        created = db.create_api_key("anon-user", "Anon Key")
        result = db.verify_api_key(created["key"])
        assert "anon_id" in result
