"""Tests for the user profile system.

Pure Python tests -- no DearPyGui required.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from flocroscope.gui.profiles import (
    ProfileManager,
    UserProfile,
    _generate_salt,
    _hash_password,
)


@pytest.fixture
def tmp_profiles_dir():
    """Create a temporary directory for profile storage."""
    d = os.path.join(
        os.environ.get("TMPDIR", "/tmp/claude-1000"),
        "test_profiles",
    )
    os.makedirs(d, exist_ok=True)
    yield d
    # Cleanup
    for f in Path(d).glob("*.json"):
        f.unlink()
    try:
        Path(d).rmdir()
    except OSError:
        pass


@pytest.fixture
def pm(tmp_profiles_dir):
    """Create a ProfileManager with temp storage."""
    return ProfileManager(tmp_profiles_dir)


# ------------------------------------------------------------------ #
#  UserProfile dataclass
# ------------------------------------------------------------------ #


class TestUserProfile:
    """Tests for the UserProfile dataclass."""

    def test_default_construction(self) -> None:
        p = UserProfile()
        assert p.username == ""
        assert p.role == "user"
        assert p.default_experiment_mode == "Behaviour"
        assert p.preferences == {}

    def test_custom_fields(self) -> None:
        p = UserProfile(
            username="alice",
            display_name="Alice",
            role="admin",
        )
        assert p.username == "alice"
        assert p.display_name == "Alice"
        assert p.role == "admin"


# ------------------------------------------------------------------ #
#  Password hashing
# ------------------------------------------------------------------ #


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_salt_generation(self) -> None:
        s = _generate_salt()
        assert isinstance(s, str)
        assert len(s) == 32  # 16 bytes = 32 hex chars

    def test_different_salts(self) -> None:
        s1 = _generate_salt()
        s2 = _generate_salt()
        assert s1 != s2

    def test_hash_deterministic(self) -> None:
        salt = "abc123"
        h1 = _hash_password("password", salt)
        h2 = _hash_password("password", salt)
        assert h1 == h2

    def test_different_passwords_different_hashes(self) -> None:
        salt = "abc123"
        h1 = _hash_password("pass1", salt)
        h2 = _hash_password("pass2", salt)
        assert h1 != h2

    def test_different_salts_different_hashes(self) -> None:
        h1 = _hash_password("password", "salt1")
        h2 = _hash_password("password", "salt2")
        assert h1 != h2


# ------------------------------------------------------------------ #
#  ProfileManager CRUD
# ------------------------------------------------------------------ #


class TestProfileManagerCreation:
    """Tests for creating user profiles."""

    def test_create_user(self, pm) -> None:
        profile = pm.create_user("alice", "secret123")
        assert profile.username == "alice"
        assert profile.password_hash != ""
        assert profile.salt != ""
        assert profile.created_at != ""

    def test_create_user_display_name(self, pm) -> None:
        profile = pm.create_user(
            "bob", "pass", display_name="Bob Smith",
        )
        assert profile.display_name == "Bob Smith"

    def test_create_user_default_display_name(self, pm) -> None:
        profile = pm.create_user("carol", "pass")
        assert profile.display_name == "carol"

    def test_create_duplicate_raises(self, pm) -> None:
        pm.create_user("alice", "pass")
        with pytest.raises(ValueError, match="already exists"):
            pm.create_user("alice", "otherpass")

    def test_create_empty_username_raises(self, pm) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            pm.create_user("", "pass")

    def test_case_insensitive_username(self, pm) -> None:
        pm.create_user("Alice", "pass")
        with pytest.raises(ValueError, match="already exists"):
            pm.create_user("alice", "pass2")

    def test_create_admin_role(self, pm) -> None:
        profile = pm.create_user(
            "admin_user", "pass", role="admin",
        )
        assert profile.role == "admin"


class TestProfileManagerListing:
    """Tests for listing users."""

    def test_list_empty(self, pm) -> None:
        assert pm.list_users() == []

    def test_list_after_creation(self, pm) -> None:
        pm.create_user("alice", "pass")
        pm.create_user("bob", "pass")
        users = pm.list_users()
        assert users == ["alice", "bob"]

    def test_list_sorted(self, pm) -> None:
        pm.create_user("charlie", "pass")
        pm.create_user("alice", "pass")
        assert pm.list_users() == ["alice", "charlie"]


class TestProfileManagerGetProfile:
    """Tests for loading profiles."""

    def test_get_existing_profile(self, pm) -> None:
        pm.create_user("alice", "pass", display_name="Alice")
        profile = pm.get_profile("alice")
        assert profile is not None
        assert profile.username == "alice"
        assert profile.display_name == "Alice"

    def test_get_nonexistent_returns_none(self, pm) -> None:
        assert pm.get_profile("nobody") is None

    def test_get_profile_case_insensitive(self, pm) -> None:
        pm.create_user("alice", "pass")
        profile = pm.get_profile("Alice")
        assert profile is not None
        assert profile.username == "alice"


class TestProfileManagerDelete:
    """Tests for deleting profiles."""

    def test_delete_existing(self, pm) -> None:
        pm.create_user("alice", "pass")
        assert pm.delete_user("alice") is True
        assert pm.get_profile("alice") is None

    def test_delete_nonexistent(self, pm) -> None:
        assert pm.delete_user("nobody") is False

    def test_delete_clears_current_user(self, pm) -> None:
        pm.create_user("alice", "pass")
        pm.login("alice", "pass")
        assert pm.is_logged_in
        pm.delete_user("alice")
        assert not pm.is_logged_in


class TestProfileManagerUpdate:
    """Tests for updating profiles."""

    def test_update_profile(self, pm) -> None:
        pm.create_user("alice", "pass")
        profile = pm.get_profile("alice")
        profile.display_name = "Alice Updated"
        pm.update_profile(profile)
        reloaded = pm.get_profile("alice")
        assert reloaded.display_name == "Alice Updated"


# ------------------------------------------------------------------ #
#  Authentication
# ------------------------------------------------------------------ #


class TestAuthentication:
    """Tests for login/authentication."""

    def test_authenticate_success(self, pm) -> None:
        pm.create_user("alice", "secret")
        result = pm.authenticate("alice", "secret")
        assert result is not None
        assert result.username == "alice"

    def test_authenticate_wrong_password(self, pm) -> None:
        pm.create_user("alice", "secret")
        result = pm.authenticate("alice", "wrong")
        assert result is None

    def test_authenticate_nonexistent_user(self, pm) -> None:
        result = pm.authenticate("nobody", "pass")
        assert result is None

    def test_login_success(self, pm) -> None:
        pm.create_user("alice", "secret")
        profile = pm.login("alice", "secret")
        assert profile is not None
        assert pm.is_logged_in
        assert pm.current_user.username == "alice"

    def test_login_updates_last_login(self, pm) -> None:
        pm.create_user("alice", "secret")
        pm.login("alice", "secret")
        profile = pm.get_profile("alice")
        assert profile.last_login != ""

    def test_login_failure_returns_none(self, pm) -> None:
        pm.create_user("alice", "secret")
        result = pm.login("alice", "wrong")
        assert result is None
        assert not pm.is_logged_in

    def test_logout(self, pm) -> None:
        pm.create_user("alice", "secret")
        pm.login("alice", "secret")
        pm.logout()
        assert not pm.is_logged_in
        assert pm.current_user is None


class TestChangePassword:
    """Tests for password change."""

    def test_change_password_success(self, pm) -> None:
        pm.create_user("alice", "oldpass")
        assert pm.change_password(
            "alice", "oldpass", "newpass",
        )
        # Old password no longer works
        assert pm.authenticate("alice", "oldpass") is None
        # New password works
        assert pm.authenticate("alice", "newpass") is not None

    def test_change_password_wrong_old(self, pm) -> None:
        pm.create_user("alice", "oldpass")
        assert not pm.change_password(
            "alice", "wrong", "newpass",
        )
        # Original password still works
        assert pm.authenticate("alice", "oldpass") is not None


# ------------------------------------------------------------------ #
#  Persistence
# ------------------------------------------------------------------ #


class TestPersistence:
    """Tests for JSON file persistence."""

    def test_profile_persisted_as_json(self, pm) -> None:
        pm.create_user("alice", "pass")
        path = pm.profiles_dir / "alice.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["username"] == "alice"

    def test_preferences_persisted(self, pm) -> None:
        pm.create_user("alice", "pass")
        profile = pm.get_profile("alice")
        profile.preferences["theme"] = "dark"
        pm.update_profile(profile)
        reloaded = pm.get_profile("alice")
        assert reloaded.preferences["theme"] == "dark"


# ------------------------------------------------------------------ #
#  First-user admin & last_user tracking
# ------------------------------------------------------------------ #


class TestFirstUserAdmin:
    """Tests for auto-admin assignment."""

    def test_first_user_is_admin(self, pm) -> None:
        """First user created gets admin role automatically."""
        profile = pm.create_user("first", "pass")
        assert profile.role == "admin"

    def test_second_user_is_regular(self, pm) -> None:
        """Subsequent users get regular user role."""
        pm.create_user("first", "pass")
        second = pm.create_user("second", "pass")
        assert second.role == "user"

    def test_explicit_role_overrides(self, pm) -> None:
        """Explicit role parameter overrides auto-assignment."""
        profile = pm.create_user(
            "first", "pass", role="user",
        )
        assert profile.role == "user"


class TestLastUserTracking:
    """Tests for last-user persistence."""

    def test_last_user_empty_initially(self, pm) -> None:
        assert pm.last_user == ""

    def test_last_user_updated_on_login(self, pm) -> None:
        pm.create_user("alice", "pass")
        pm.login("alice", "pass")
        assert pm.last_user == "alice"

    def test_last_user_survives_new_instance(
        self, tmp_profiles_dir,
    ) -> None:
        pm1 = ProfileManager(tmp_profiles_dir)
        pm1.create_user("bob", "pass")
        pm1.login("bob", "pass")

        pm2 = ProfileManager(tmp_profiles_dir)
        assert pm2.last_user == "bob"


class TestListProfiles:
    """Tests for list_profiles method."""

    def test_list_profiles_empty(self, pm) -> None:
        assert pm.list_profiles() == []

    def test_list_profiles_returns_objects(self, pm) -> None:
        pm.create_user("alice", "pass")
        pm.create_user("bob", "pass")
        profiles = pm.list_profiles()
        assert len(profiles) == 2
        assert all(
            isinstance(p, UserProfile) for p in profiles
        )
        names = [p.username for p in profiles]
        assert "alice" in names
        assert "bob" in names
