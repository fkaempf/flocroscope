"""User profile management panel.

Allows the logged-in user to view/edit their profile, change their
password, set default experiment mode and preset, and delete their
account.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.gui.profiles import ProfileManager, UserProfile

logger = logging.getLogger(__name__)


class UserProfilePanel:
    """Panel for managing the current user's profile.

    Args:
        profile_manager: The profile manager instance.
    """

    def __init__(
        self,
        profile_manager: ProfileManager,
    ) -> None:
        self._pm = profile_manager
        self._display_name = ""
        self._old_password = ""
        self._new_password = ""
        self._confirm_password = ""
        self._default_mode = "Behaviour"
        self._default_preset = ""
        self._status_msg = ""
        self._delete_confirmed = False
        self._on_account_deleted: object | None = None
        self.group_tag = "grp_user_profile"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg
        from flocroscope.gui.theme import ACCENT

        with dpg.group(parent=parent, tag=self.group_tag):
            dpg.add_text("User Profile", color=ACCENT)
            dpg.add_separator()

            # User info
            dpg.add_text("", tag="up_username")
            dpg.add_text("", tag="up_role")
            dpg.add_text("", tag="up_created")
            dpg.add_text("", tag="up_last_login")
            dpg.add_separator()

            # Edit display name
            with dpg.collapsing_header(
                label="Edit Profile",
                default_open=False,
            ):
                dpg.add_input_text(
                    label="Display Name",
                    tag="up_display_name",
                    width=250,
                    callback=self._on_display_name,
                )
                dpg.add_button(
                    label="Update Name",
                    tag="up_update_name_btn",
                    callback=self._on_update_name,
                    width=120,
                )

            # Default preferences
            with dpg.collapsing_header(
                label="Defaults",
                default_open=False,
            ):
                from flocroscope.gui.layout import (
                    ExperimentMode,
                )
                dpg.add_combo(
                    items=[m.value for m in ExperimentMode],
                    label="Default Mode",
                    tag="up_default_mode",
                    width=140,
                    callback=self._on_default_mode,
                )
                dpg.add_input_text(
                    label="Default Preset",
                    tag="up_default_preset",
                    width=250,
                    callback=self._on_default_preset,
                )
                dpg.add_button(
                    label="Save Defaults",
                    tag="up_save_defaults_btn",
                    callback=self._on_save_defaults,
                    width=120,
                )

            # Change password
            with dpg.collapsing_header(
                label="Change Password",
                default_open=False,
            ):
                dpg.add_input_text(
                    label="Current Password",
                    tag="up_old_pass",
                    password=True,
                    width=250,
                    callback=self._on_old_pass,
                )
                dpg.add_input_text(
                    label="New Password",
                    tag="up_new_pass",
                    password=True,
                    width=250,
                    callback=self._on_new_pass,
                )
                dpg.add_input_text(
                    label="Confirm New",
                    tag="up_confirm_pass",
                    password=True,
                    width=250,
                    callback=self._on_confirm_pass,
                )
                dpg.add_button(
                    label="Change Password",
                    tag="up_change_pass_btn",
                    callback=self._on_change_password,
                    width=140,
                )

            # Delete account
            with dpg.collapsing_header(
                label="Danger Zone",
                default_open=False,
            ):
                dpg.add_text(
                    "Permanently delete your account and "
                    "all associated data.",
                    color=(220, 70, 70),
                    wrap=400,
                )
                dpg.add_checkbox(
                    label="I understand this cannot be undone",
                    tag="up_delete_confirm",
                    callback=self._on_delete_confirm,
                )
                dpg.add_button(
                    label="Delete My Account",
                    tag="up_delete_btn",
                    callback=self._on_delete_account,
                    width=160,
                )

            dpg.add_spacer(height=4)
            dpg.add_text("", tag="up_status")

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        user = self._pm.current_user
        if user is None:
            dpg.set_value("up_username", "Not logged in")
            dpg.set_value("up_role", "")
            dpg.set_value("up_created", "")
            dpg.set_value("up_last_login", "")
            return

        dpg.set_value(
            "up_username",
            f"Username: {user.username}",
        )
        dpg.set_value(
            "up_role",
            f"Role: {user.role}",
        )
        dpg.set_value(
            "up_created",
            f"Created: {user.created_at}",
        )
        dpg.set_value(
            "up_last_login",
            f"Last login: {user.last_login}",
        )
        dpg.set_value("up_status", self._status_msg)

    # -- callbacks ---------------------------------------------------- #

    def _on_display_name(self, sender, app_data, user_data):
        self._display_name = app_data

    def _on_default_mode(self, sender, app_data, user_data):
        self._default_mode = app_data

    def _on_default_preset(self, sender, app_data, user_data):
        self._default_preset = app_data

    def _on_old_pass(self, sender, app_data, user_data):
        self._old_password = app_data

    def _on_new_pass(self, sender, app_data, user_data):
        self._new_password = app_data

    def _on_confirm_pass(self, sender, app_data, user_data):
        self._confirm_password = app_data

    def _on_update_name(self, sender, app_data, user_data):
        self._update_display_name()

    def _on_save_defaults(self, sender, app_data, user_data):
        self._save_defaults()

    def _on_change_password(self, sender, app_data, user_data):
        self._change_password()

    def _on_delete_confirm(self, sender, app_data, user_data):
        self._delete_confirmed = app_data

    def _on_delete_account(self, sender, app_data, user_data):
        self._delete_account()

    # -- actions ------------------------------------------------------ #

    def _update_display_name(self) -> None:
        user = self._pm.current_user
        if user is None:
            self._status_msg = "Not logged in"
            return
        if not self._display_name.strip():
            self._status_msg = "Display name cannot be empty"
            return
        user.display_name = self._display_name.strip()
        self._pm.update_profile(user)
        self._status_msg = "Display name updated"

    def _save_defaults(self) -> None:
        user = self._pm.current_user
        if user is None:
            self._status_msg = "Not logged in"
            return
        user.default_experiment_mode = self._default_mode
        user.default_preset = self._default_preset
        self._pm.update_profile(user)
        self._status_msg = "Defaults saved"

    def _change_password(self) -> None:
        user = self._pm.current_user
        if user is None:
            self._status_msg = "Not logged in"
            return
        if not self._old_password:
            self._status_msg = "Enter current password"
            return
        if not self._new_password:
            self._status_msg = "Enter new password"
            return
        if self._new_password != self._confirm_password:
            self._status_msg = "Passwords do not match"
            return
        if len(self._new_password) < 4:
            self._status_msg = (
                "Password must be at least 4 characters"
            )
            return

        success = self._pm.change_password(
            user.username,
            self._old_password,
            self._new_password,
        )
        if success:
            self._status_msg = "Password changed"
            self._old_password = ""
            self._new_password = ""
            self._confirm_password = ""
        else:
            self._status_msg = "Incorrect current password"

    def _delete_account(self) -> None:
        user = self._pm.current_user
        if user is None:
            self._status_msg = "Not logged in"
            return
        if not self._delete_confirmed:
            self._status_msg = (
                "Check the confirmation box first"
            )
            return

        username = user.username
        self._pm.delete_user(username)
        self._status_msg = f"Account '{username}' deleted"
        self._delete_confirmed = False
        logger.info("Account deleted: %s", username)

        # Trigger logout callback if set
        if callable(self._on_account_deleted):
            self._on_account_deleted()
