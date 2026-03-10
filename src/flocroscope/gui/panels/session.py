"""Session management panel.

Provides GUI controls for starting/stopping experimental sessions,
managing trials, and viewing session status.  Optionally integrates
with Flomington for auto-populating fly metadata from stock/cross
records.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.flomington import FlomingtonClient
    from flocroscope.config.schema import FlocroscopeConfig
    from flocroscope.session.session import Session

logger = logging.getLogger(__name__)


class SessionPanel:
    """Panel for experiment session management.

    Args:
        config: Application configuration.
        flomington_client: Optional Flomington client for stock/cross
            lookups. When ``None``, the Flomington integration section
            is hidden and the panel works exactly as before.
    """

    def __init__(
        self,
        config: FlocroscopeConfig,
        flomington_client: FlomingtonClient | None = None,
    ) -> None:
        self._config = config
        self._flomington = flomington_client
        self._session: Session | None = None
        self._experimenter = ""
        self._fly_genotype = ""
        self._fly_id = ""
        self._notes = ""
        self._status_msg = ""
        self._flomington_lookup_done = False
        self.group_tag = "grp_session"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    @property
    def flomington_client(self) -> FlomingtonClient | None:
        """The Flomington client, if configured."""
        return self._flomington

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(parent=parent, tag=self.group_tag):
            # --- Setup group (visible when no session) ---
            with dpg.group(tag="sess_setup_group"):
                dpg.add_text("New Session")
                dpg.add_separator()
                dpg.add_input_text(
                    label="Experimenter",
                    tag="sess_experimenter",
                    callback=self._on_experimenter,
                )
                dpg.add_input_text(
                    label="Fly Genotype",
                    tag="sess_genotype",
                    callback=self._on_genotype,
                )
                dpg.add_input_text(
                    label="Fly/Cross ID",
                    tag="sess_fly_id",
                    callback=self._on_fly_id_change,
                )
                dpg.add_input_text(
                    label="Notes",
                    tag="sess_notes",
                    multiline=True,
                    height=200,
                    callback=self._on_notes,
                )

                # Flomington section
                with dpg.group(tag="sess_flom_group"):
                    dpg.add_spacer(height=4)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Flomington:")
                        dpg.add_text(
                            "", tag="sess_flom_status",
                        )
                    dpg.add_button(
                        label="Lookup from Flomington",
                        tag="sess_flom_lookup_btn",
                        callback=self._on_flom_lookup,
                    )
                    dpg.add_text(
                        "", tag="sess_flom_result",
                        color=(128, 204, 128),
                    )

                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Start Session",
                        tag="sess_start_btn",
                        callback=self._on_start,
                    )
                    dpg.add_text(
                        "", tag="sess_last_info",
                    )

            # --- Active group (visible during session) ---
            with dpg.group(
                tag="sess_active_group", show=False,
            ):
                dpg.add_text(
                    "", tag="sess_id_text",
                )
                dpg.add_text(
                    "", tag="sess_summary_text",
                )
                dpg.add_text(
                    "", tag="sess_trial_status",
                    color=(51, 230, 51),
                )
                dpg.add_separator()

                dpg.add_button(
                    label="Begin Trial",
                    tag="sess_begin_trial_btn",
                    callback=self._on_begin_trial,
                )
                dpg.add_button(
                    label="End Trial",
                    tag="sess_end_trial_btn",
                    callback=self._on_end_trial,
                    show=False,
                )
                dpg.add_separator()

                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Save Session",
                        callback=self._on_save,
                    )
                    dpg.add_button(
                        label="Stop Session",
                        callback=self._on_stop,
                    )

            dpg.add_separator()
            dpg.add_text("", tag="sess_status_msg")

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        is_active = (
            self._session is not None
            and self._session.is_running
        )

        if is_active:
            dpg.hide_item("sess_setup_group")
            dpg.show_item("sess_active_group")
            self._update_active()
        else:
            dpg.show_item("sess_setup_group")
            dpg.hide_item("sess_active_group")
            self._update_setup()

        # Flomington visibility
        if self._flomington is None:
            dpg.hide_item("sess_flom_group")
        else:
            dpg.show_item("sess_flom_group")
            connected = self._flomington.connected
            if connected:
                dpg.set_value(
                    "sess_flom_status", "Connected",
                )
                dpg.configure_item(
                    "sess_flom_status",
                    color=(51, 230, 51),
                )
            else:
                dpg.set_value(
                    "sess_flom_status", "Disconnected",
                )
                dpg.configure_item(
                    "sess_flom_status",
                    color=(230, 77, 77),
                )

            # Show lookup button only when ID present
            if (
                self._fly_id
                and self._fly_id.strip()
                and not self._flomington_lookup_done
            ):
                dpg.show_item("sess_flom_lookup_btn")
            else:
                dpg.hide_item("sess_flom_lookup_btn")

            if self._flomington_lookup_done:
                dpg.set_value(
                    "sess_flom_result",
                    "Genotype populated from Flomington",
                )
            else:
                dpg.set_value("sess_flom_result", "")

        dpg.set_value("sess_status_msg", self._status_msg)

    def _update_setup(self) -> None:
        """Update setup mode display."""
        import dearpygui.dearpygui as dpg

        if self._session is not None:
            dpg.set_value(
                "sess_last_info",
                f"Last session: {self._session.trial_count} "
                "trials",
            )

    def _update_active(self) -> None:
        """Update active session display."""
        import dearpygui.dearpygui as dpg

        session = self._session
        if session is None:
            return

        summary = session.summary()
        dpg.set_value(
            "sess_id_text",
            f"Session: {summary['session_id']}",
        )
        dpg.set_value(
            "sess_summary_text",
            f"Trials: {summary['trial_count']}  "
            f"Duration: {summary['total_duration_s']:.1f}s",
        )

        if summary["current_trial"] is not None:
            dpg.set_value(
                "sess_trial_status",
                f"Trial {summary['current_trial']} active",
            )
            dpg.configure_item(
                "sess_trial_status", color=(51, 230, 51),
            )
            dpg.hide_item("sess_begin_trial_btn")
            dpg.show_item("sess_end_trial_btn")
        else:
            dpg.set_value(
                "sess_trial_status", "No trial active",
            )
            dpg.configure_item(
                "sess_trial_status", color=(200, 200, 200),
            )
            dpg.show_item("sess_begin_trial_btn")
            dpg.hide_item("sess_end_trial_btn")

    # -- callbacks --

    def _on_experimenter(self, sender, app_data, user_data):
        self._experimenter = app_data

    def _on_genotype(self, sender, app_data, user_data):
        self._fly_genotype = app_data

    def _on_fly_id_change(self, sender, app_data, user_data):
        self._fly_id = app_data
        self._flomington_lookup_done = False

    def _on_notes(self, sender, app_data, user_data):
        self._notes = app_data

    def _on_flom_lookup(self, sender, app_data, user_data):
        self._lookup_from_flomington()

    def _on_start(self, sender, app_data, user_data):
        self._start_session()

    def _on_begin_trial(self, sender, app_data, user_data):
        if self._session is None:
            return
        self._session.begin_trial(metadata={
            "genotype": self._fly_genotype,
            "fly_id": self._fly_id,
        })
        self._status_msg = (
            f"Trial {self._session.current_trial.trial_number}"
            " started"
        )

    def _on_end_trial(self, sender, app_data, user_data):
        if self._session is None:
            return
        trial = self._session.end_trial()
        if trial:
            self._status_msg = (
                f"Trial {trial.trial_number} ended "
                f"({trial.duration_s:.1f}s)"
            )

    def _on_save(self, sender, app_data, user_data):
        if self._session is None:
            return
        path = self._session.save()
        self._status_msg = f"Saved to {path}"

    def _on_stop(self, sender, app_data, user_data):
        if self._session is None:
            return
        self._session.stop()
        path = self._session.save()
        self._status_msg = (
            f"Session stopped, saved to {path}"
        )

    def _lookup_from_flomington(self) -> None:
        """Look up fly/cross info from Flomington."""
        if self._flomington is None:
            return

        fly_id = self._fly_id
        if not fly_id or not fly_id.strip():
            return
        fly_id = fly_id.strip()

        stock = self._flomington.get_stock(fly_id)
        if stock is not None and stock.genotype:
            self._fly_genotype = stock.genotype
            self._flomington_lookup_done = True
            self._status_msg = (
                f"Populated genotype from stock: {stock.name}"
            )
            logger.info(
                "Flomington stock lookup: %s -> %s",
                fly_id, stock.genotype,
            )
            return

        cross = self._flomington.get_cross(fly_id)
        if cross is not None:
            parts = []
            if cross.virgin_genotype:
                parts.append(cross.virgin_genotype)
            if cross.male_genotype:
                parts.append(cross.male_genotype)
            if parts:
                genotype = " x ".join(parts)
                self._fly_genotype = genotype
                self._flomington_lookup_done = True
                self._status_msg = (
                    f"Populated genotype from cross: "
                    f"{cross.cross_id} ({cross.status})"
                )
                logger.info(
                    "Flomington cross lookup: %s -> %s",
                    fly_id, genotype,
                )
                return

        self._status_msg = (
            f"ID '{fly_id}' not found in Flomington"
        )

    def _start_session(self) -> None:
        """Create and start a new session."""
        from flocroscope.session.session import Session

        self._session = Session(
            config=self._config,
            experimenter=self._experimenter,
            stimulus_type="gui",
        )
        self._session.metadata.fly_genotype = self._fly_genotype
        if self._fly_id:
            self._session.metadata.fly_stock_id = self._fly_id
        self._session.metadata.notes = self._notes
        self._session.start()
        self._status_msg = (
            f"Session {self._session.session_id} started"
        )
        logger.info("Session started from GUI")
