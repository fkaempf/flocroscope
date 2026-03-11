"""User profile system with password-protected accounts.

Provides a simple local user management system for the Flocroscope
GUI.  Each user gets a profile stored as JSON with a salted SHA-256
password hash.  Profiles track per-user preferences and last-used
experiment settings.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Default storage directory (relative to project root)
_DEFAULT_PROFILES_DIR = "data/profiles"


@dataclass
class UserProfile:
    """A single user profile.

    Attributes:
        username: Unique username (case-insensitive key).
        display_name: Friendly display name shown in the GUI.
        password_hash: Salted SHA-256 hex digest.
        salt: Random hex salt for password hashing.
        role: User role (``admin`` or ``user``).
        created_at: ISO 8601 timestamp of account creation.
        last_login: ISO 8601 timestamp of most recent login.
        default_experiment_mode: Preferred experiment mode on login.
        default_preset: Name of the preferred experiment preset.
        preferences: Arbitrary per-user preference dict.
    """

    username: str = ""
    display_name: str = ""
    password_hash: str = ""
    salt: str = ""
    role: str = "user"
    created_at: str = ""
    last_login: str = ""
    default_experiment_mode: str = "Behaviour"
    default_preset: str = ""
    preferences: dict[str, object] = field(default_factory=dict)


def _hash_password(password: str, salt: str) -> str:
    """Produce a salted SHA-256 hex digest."""
    return hashlib.sha256(
        (salt + password).encode("utf-8"),
    ).hexdigest()


def _generate_salt() -> str:
    """Return 32 hex characters of random salt."""
    return os.urandom(16).hex()


class ProfileManager:
    """Manages user profiles on disk.

    Profiles are stored as individual JSON files under
    ``<profiles_dir>/<username>.json``.

    Args:
        profiles_dir: Directory to store profile JSON files.
    """

    def __init__(
        self,
        profiles_dir: str | Path = _DEFAULT_PROFILES_DIR,
    ) -> None:
        self._dir = Path(profiles_dir)
        self._current_user: UserProfile | None = None

    @property
    def profiles_dir(self) -> Path:
        """The directory where profiles are stored."""
        return self._dir

    @property
    def current_user(self) -> UserProfile | None:
        """The currently logged-in user, if any."""
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        """Whether a user is currently logged in."""
        return self._current_user is not None

    # -- CRUD --------------------------------------------------------- #

    def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        role: str | None = None,
    ) -> UserProfile:
        """Create a new user profile.

        The first user created is automatically assigned the
        ``admin`` role.  Subsequent users default to ``user``.

        Args:
            username: Unique username (case-insensitive).
            password: Plain-text password (hashed before storage).
            display_name: Friendly name; defaults to *username*.
            role: ``admin`` or ``user``.  If ``None``, auto-assigned.

        Returns:
            The newly created profile.

        Raises:
            ValueError: If *username* is empty or already exists.
        """
        username = username.strip().lower()
        if not username:
            raise ValueError("Username cannot be empty")
        if self._profile_path(username).exists():
            raise ValueError(f"User '{username}' already exists")

        if role is None:
            role = (
                "admin" if not self.list_users() else "user"
            )

        salt = _generate_salt()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        profile = UserProfile(
            username=username,
            display_name=display_name or username,
            password_hash=_hash_password(password, salt),
            salt=salt,
            role=role,
            created_at=now,
            last_login="",
        )
        self._save_profile(profile)
        logger.info("Created user profile: %s (%s)", username, role)
        return profile

    def list_users(self) -> list[str]:
        """Return sorted list of existing usernames."""
        if not self._dir.exists():
            return []
        return sorted(
            p.stem for p in self._dir.glob("*.json")
            if p.stem != "_last_user"
        )

    def list_profiles(self) -> list[UserProfile]:
        """Return all profiles as :class:`UserProfile` objects."""
        return [
            p for name in self.list_users()
            if (p := self.get_profile(name)) is not None
        ]

    @property
    def last_user(self) -> str:
        """Username of the most recently logged-in user."""
        meta_path = self._dir / "_last_user.json"
        if meta_path.exists():
            try:
                data = json.loads(
                    meta_path.read_text("utf-8"),
                )
                return data.get("username", "")
            except Exception:
                pass
        return ""

    def get_profile(self, username: str) -> UserProfile | None:
        """Load a profile from disk.

        Returns ``None`` if the profile does not exist.
        """
        username = username.strip().lower()
        path = self._profile_path(username)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text("utf-8"))
            return UserProfile(**{
                k: v for k, v in data.items()
                if k in UserProfile.__dataclass_fields__
            })
        except Exception as exc:
            logger.warning(
                "Failed to load profile %s: %s",
                username, exc,
            )
            return None

    def delete_user(self, username: str) -> bool:
        """Delete a user profile from disk.

        Returns ``True`` if the profile existed and was removed.
        """
        username = username.strip().lower()
        path = self._profile_path(username)
        if path.exists():
            path.unlink()
            logger.info("Deleted user profile: %s", username)
            if (
                self._current_user is not None
                and self._current_user.username == username
            ):
                self._current_user = None
            return True
        return False

    def update_profile(self, profile: UserProfile) -> None:
        """Save an updated profile to disk."""
        self._save_profile(profile)

    # -- Authentication ----------------------------------------------- #

    def authenticate(
        self, username: str, password: str,
    ) -> UserProfile | None:
        """Verify credentials and return the profile on success.

        Returns ``None`` on failure.
        """
        profile = self.get_profile(username)
        if profile is None:
            return None
        expected = _hash_password(password, profile.salt)
        if expected != profile.password_hash:
            return None
        return profile

    def login(
        self, username: str, password: str,
    ) -> UserProfile | None:
        """Authenticate and set the current user.

        Updates *last_login* on success and persists the change.

        Returns:
            The profile on success, ``None`` on failure.
        """
        profile = self.authenticate(username, password)
        if profile is None:
            return None
        profile.last_login = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_profile(profile)
        self._current_user = profile
        self._save_last_user(profile.username)
        logger.info("User logged in: %s", username)
        return profile

    def logout(self) -> None:
        """Clear the current user."""
        if self._current_user is not None:
            logger.info(
                "User logged out: %s",
                self._current_user.username,
            )
        self._current_user = None

    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change a user's password.

        Requires the correct *old_password*.  Returns ``True``
        on success.
        """
        profile = self.authenticate(username, old_password)
        if profile is None:
            return False
        salt = _generate_salt()
        profile.salt = salt
        profile.password_hash = _hash_password(new_password, salt)
        self._save_profile(profile)
        logger.info("Password changed for user: %s", username)
        return True

    # -- Internal ----------------------------------------------------- #

    def _save_last_user(self, username: str) -> None:
        """Persist the last logged-in username."""
        self._dir.mkdir(parents=True, exist_ok=True)
        meta = self._dir / "_last_user.json"
        meta.write_text(
            json.dumps({"username": username}),
            encoding="utf-8",
        )

    def _profile_path(self, username: str) -> Path:
        return self._dir / f"{username}.json"

    def _save_profile(self, profile: UserProfile) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._profile_path(profile.username)
        path.write_text(
            json.dumps(asdict(profile), indent=2),
            encoding="utf-8",
        )
