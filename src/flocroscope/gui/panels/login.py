"""Login and registration panel.

Shows a login form before the main application.  Supports creating
new accounts and authenticating existing users via the
:class:`~flocroscope.gui.profiles.ProfileManager`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.gui.profiles import ProfileManager, UserProfile

logger = logging.getLogger(__name__)


class LoginPanel:
    """Panel for user authentication.

    After a successful login, ``logged_in_user`` contains the
    authenticated :class:`UserProfile`.  The main app checks this
    each frame to decide whether to show the login screen or the
    main workspace.

    Args:
        profile_manager: The profile manager instance.
    """

    def __init__(
        self,
        profile_manager: ProfileManager,
    ) -> None:
        self._pm = profile_manager
        self._logged_in_user: UserProfile | None = None
        self._username = ""
        self._password = ""
        self._reg_username = ""
        self._reg_display_name = ""
        self._reg_password = ""
        self._reg_confirm = ""
        self._status_msg = ""
        self._show_register = False
        self._built = False
        self.group_tag = "grp_login"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    @property
    def logged_in_user(self) -> UserProfile | None:
        """The currently authenticated user, or ``None``."""
        return self._logged_in_user

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in_user is not None

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg
        from flocroscope.gui.theme import (
            ACCENT, ACCENT_HOVER, TEXT_SECONDARY, BG_DARK,
            BORDER, TEXT_PRIMARY,
        )

        self._built = True

        with dpg.group(parent=parent, tag=self.group_tag):
            # Vertical centering spacer
            dpg.add_spacer(height=100)

            # Centered card wrapper
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=340)
                with dpg.child_window(
                    width=520, height=440,
                    tag="login_card",
                ):
                    # Top padding inside card
                    dpg.add_spacer(height=24)

                    # Title block -- centered feel
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=20)
                        with dpg.group():
                            dpg.add_text(
                                "FLOCROSCOPE",
                                color=ACCENT,
                                tag="login_title",
                            )
                            dpg.add_spacer(height=2)
                            dpg.add_text(
                                "Virtual Reality Stimulus Platform",
                                color=TEXT_SECONDARY,
                                tag="login_subtitle",
                            )

                    dpg.add_spacer(height=20)

                    # Thin accent divider
                    dpg.add_separator()

                    dpg.add_spacer(height=16)

                    # --- Login form ---
                    with dpg.group(tag="login_form"):
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=20)
                            with dpg.group():
                                dpg.add_text(
                                    "Sign In",
                                    color=TEXT_PRIMARY,
                                )
                                dpg.add_spacer(height=12)

                                users = self._pm.list_users()
                                last = self._pm.last_user
                                if users:
                                    default_user = (
                                        last if last in users
                                        else users[0]
                                    )
                                    self._username = default_user
                                    dpg.add_combo(
                                        items=users,
                                        label="Username",
                                        tag="login_username",
                                        default_value=default_user,
                                        width=320,
                                        callback=self._on_username,
                                    )
                                else:
                                    dpg.add_input_text(
                                        label="Username",
                                        tag="login_username",
                                        width=320,
                                        callback=self._on_username,
                                    )

                                dpg.add_spacer(height=6)

                                dpg.add_input_text(
                                    label="Password",
                                    tag="login_password",
                                    password=True,
                                    width=320,
                                    on_enter=True,
                                    callback=(
                                        self._on_login_enter
                                    ),
                                )
                                dpg.add_spacer(height=14)

                                with dpg.group(horizontal=True):
                                    dpg.add_button(
                                        label="Login",
                                        tag="login_btn",
                                        callback=(
                                            self._on_login
                                        ),
                                        width=150,
                                    )
                                    dpg.add_spacer(width=8)
                                    dpg.add_button(
                                        label="Create Account",
                                        tag=(
                                            "login_show_reg_btn"
                                        ),
                                        callback=(
                                            self
                                            ._on_show_register
                                        ),
                                        width=150,
                                    )

                                dpg.add_spacer(height=8)
                                dpg.add_text(
                                    "",
                                    tag="login_status",
                                    color=(235, 70, 70),
                                )

                                if users:
                                    dpg.add_spacer(height=10)
                                    dpg.add_text(
                                        f"{len(users)}"
                                        " registered user(s)",
                                        tag="login_user_count",
                                        color=TEXT_SECONDARY,
                                    )

                    # --- Registration form ---
                    with dpg.group(
                        tag="register_form", show=False,
                    ):
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=20)
                            with dpg.group():
                                dpg.add_text(
                                    "Create Account",
                                    color=TEXT_PRIMARY,
                                )
                                dpg.add_spacer(height=12)

                                dpg.add_input_text(
                                    label="Username",
                                    tag="reg_username",
                                    width=320,
                                    callback=(
                                        self._on_reg_username
                                    ),
                                )
                                dpg.add_spacer(height=4)
                                dpg.add_input_text(
                                    label="Display Name",
                                    tag="reg_display",
                                    width=320,
                                    callback=(
                                        self._on_reg_display
                                    ),
                                )
                                dpg.add_spacer(height=4)
                                dpg.add_input_text(
                                    label="Password",
                                    tag="reg_password",
                                    password=True,
                                    width=320,
                                    callback=(
                                        self._on_reg_password
                                    ),
                                )
                                dpg.add_spacer(height=4)
                                dpg.add_input_text(
                                    label="Confirm Password",
                                    tag="reg_confirm",
                                    password=True,
                                    width=320,
                                    callback=(
                                        self._on_reg_confirm
                                    ),
                                )
                                dpg.add_spacer(height=14)

                                with dpg.group(horizontal=True):
                                    dpg.add_button(
                                        label="Register",
                                        tag="reg_btn",
                                        callback=(
                                            self._on_register
                                        ),
                                        width=150,
                                    )
                                    dpg.add_spacer(width=8)
                                    dpg.add_button(
                                        label="Back to Login",
                                        tag="reg_back_btn",
                                        callback=(
                                            self._on_back_login
                                        ),
                                        width=150,
                                    )

                                dpg.add_spacer(height=8)
                                dpg.add_text(
                                    "",
                                    tag="reg_status",
                                    color=(235, 70, 70),
                                )

    def update(self) -> None:
        """Push status each frame."""
        pass

    # -- callbacks ---------------------------------------------------- #

    def _on_username(self, sender, app_data, user_data):
        self._username = app_data

    def _on_login_enter(self, sender, app_data, user_data):
        self._password = app_data
        self._do_login()

    def _on_login(self, sender, app_data, user_data):
        import dearpygui.dearpygui as dpg
        self._password = dpg.get_value("login_password")
        self._do_login()

    def _on_show_register(self, sender, app_data, user_data):
        import dearpygui.dearpygui as dpg
        self._show_register = True
        dpg.hide_item("login_form")
        dpg.show_item("register_form")

    def _on_back_login(self, sender, app_data, user_data):
        import dearpygui.dearpygui as dpg
        self._show_register = False
        dpg.show_item("login_form")
        dpg.hide_item("register_form")
        self._refresh_user_list()

    def _on_reg_username(self, sender, app_data, user_data):
        self._reg_username = app_data

    def _on_reg_display(self, sender, app_data, user_data):
        self._reg_display_name = app_data

    def _on_reg_password(self, sender, app_data, user_data):
        self._reg_password = app_data

    def _on_reg_confirm(self, sender, app_data, user_data):
        self._reg_confirm = app_data

    def _on_register(self, sender, app_data, user_data):
        self._do_register()

    def _refresh_user_list(self) -> None:
        """Refresh the username combo after registration."""
        try:
            import dearpygui.dearpygui as dpg
            users = self._pm.list_users()
            dpg.configure_item(
                "login_username", items=users,
            )
            if hasattr(dpg, "does_item_exist"):
                if dpg.does_item_exist("login_user_count"):
                    dpg.set_value(
                        "login_user_count",
                        f"{len(users)} registered user(s)",
                    )
        except Exception:
            pass

    # -- actions ------------------------------------------------------ #

    def _do_login(self) -> None:
        import dearpygui.dearpygui as dpg

        if not self._username:
            dpg.set_value(
                "login_status", "Enter a username",
            )
            return
        if not self._password:
            dpg.set_value(
                "login_status", "Enter a password",
            )
            return

        profile = self._pm.login(
            self._username, self._password,
        )
        if profile is None:
            dpg.set_value(
                "login_status", "Invalid credentials",
            )
            logger.warning(
                "Login failed for user: %s", self._username,
            )
            return

        self._logged_in_user = profile
        dpg.set_value("login_status", "")
        # Clear password field for security
        dpg.set_value("login_password", "")
        self._password = ""
        logger.info(
            "Login successful: %s", profile.username,
        )

    def _do_register(self) -> None:
        import dearpygui.dearpygui as dpg

        if not self._reg_username:
            dpg.set_value("reg_status", "Username required")
            return
        if not self._reg_password:
            dpg.set_value("reg_status", "Password required")
            return
        if self._reg_password != self._reg_confirm:
            dpg.set_value(
                "reg_status", "Passwords do not match",
            )
            return
        if len(self._reg_password) < 4:
            dpg.set_value(
                "reg_status",
                "Password must be at least 4 characters",
            )
            return

        try:
            self._pm.create_user(
                username=self._reg_username,
                password=self._reg_password,
                display_name=self._reg_display_name,
            )
            # Auto-login after registration
            profile = self._pm.login(
                self._reg_username, self._reg_password,
            )
            self._logged_in_user = profile
            dpg.set_value("reg_status", "")
            # Clear registration fields
            dpg.set_value("reg_password", "")
            dpg.set_value("reg_confirm", "")
            self._reg_password = ""
            self._reg_confirm = ""
            logger.info(
                "Registration + login: %s",
                self._reg_username,
            )
        except ValueError as exc:
            dpg.set_value("reg_status", str(exc))
