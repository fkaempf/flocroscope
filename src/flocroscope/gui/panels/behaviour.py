"""Behaviour overview panel.

Combines experiment-level status from all subsystems into a single
dashboard: current experiment type, hardware readiness, active
recording state, and a checklist of connected components.

.. note::

   In the new single-window layout the experiment type selector
   and hardware indicators live in the top bar of ``app.py``.
   This panel is retained for backward compatibility and for
   standalone/testing use.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flocroscope.gui.layout import ExperimentMode

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import FlocroscopeConfig
    from flocroscope.session.session import Session

logger = logging.getLogger(__name__)

# Backward-compatible re-export from layout.py.
EXPERIMENT_TYPES = [m.value for m in ExperimentMode]


class BehaviourPanel:
    """Dashboard panel for experiment / behaviour overview.

    Args:
        config: Full configuration.
        comms: Optional CommsHub for hardware status.
        session: Optional active Session for recording state.
    """

    def __init__(
        self,
        config: FlocroscopeConfig | None = None,
        comms: CommsHub | None = None,
        session: Session | None = None,
    ) -> None:
        self._config = config
        self._comms = comms
        self._session = session
        self._experiment_type_idx: int = 0
        self.group_tag = "grp_behaviour"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public helpers --

    @property
    def experiment_type(self) -> str:
        return EXPERIMENT_TYPES[self._experiment_type_idx]

    @property
    def session(self) -> Session | None:
        return self._session

    @session.setter
    def session(self, value: Session | None) -> None:
        self._session = value

    # -- widget creation --

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            dpg.add_text("Experiment Type:")
            dpg.add_combo(
                items=EXPERIMENT_TYPES,
                tag="beh_exp_type",
                default_value=EXPERIMENT_TYPES[0],
                callback=self._on_exp_type,
            )

            dpg.add_separator()
            dpg.add_text("Hardware Checklist:")

            _hw = [
                ("FicTrac (treadmill)", "fictrac"),
                ("ScanImage (2P)", "scanimage"),
                ("LED (optogenetics)", "led"),
                ("Presenter", "presenter"),
            ]
            for label, ep in _hw:
                dpg.add_text(
                    f"  [ ] {label}",
                    tag=f"beh_hw_{ep}",
                )

            dpg.add_separator()
            dpg.add_text("Session:")
            dpg.add_text(
                "", tag="beh_session_status",
            )
            dpg.add_text(
                "", tag="beh_session_trials",
            )

            dpg.add_separator()
            dpg.add_text("Recording:")
            dpg.add_text(
                "", tag="beh_recording_status",
            )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        # Hardware checklist
        _hw = [
            ("FicTrac (treadmill)", "fictrac"),
            ("ScanImage (2P)", "scanimage"),
            ("LED (optogenetics)", "led"),
            ("Presenter", "presenter"),
        ]
        for label, ep in _hw:
            if self._comms is not None:
                status = self._comms.status
                connected = status.get(ep, False)
            else:
                connected = False

            if connected:
                dpg.set_value(
                    f"beh_hw_{ep}",
                    f"  [x] {label}",
                )
                dpg.configure_item(
                    f"beh_hw_{ep}",
                    color=(51, 230, 51),
                )
            else:
                dpg.set_value(
                    f"beh_hw_{ep}",
                    f"  [ ] {label}",
                )
                dpg.configure_item(
                    f"beh_hw_{ep}",
                    color=(128, 128, 128),
                )

        # Session status
        if self._session is not None:
            dpg.set_value(
                "beh_session_status", "Active",
            )
            dpg.configure_item(
                "beh_session_status",
                color=(51, 230, 51),
            )
            dpg.set_value(
                "beh_session_trials",
                f"  Trials: {self._session.trial_count}",
            )
        else:
            dpg.set_value(
                "beh_session_status",
                "No active session",
            )
            dpg.configure_item(
                "beh_session_status",
                color=(153, 153, 153),
            )
            dpg.set_value("beh_session_trials", "")

        # Recording status
        if (
            self._session is not None
            and self._session.is_running
        ):
            dpg.set_value(
                "beh_recording_status", "RECORDING",
            )
            dpg.configure_item(
                "beh_recording_status",
                color=(230, 51, 51),
            )
        else:
            dpg.set_value(
                "beh_recording_status", "Not recording",
            )
            dpg.configure_item(
                "beh_recording_status",
                color=(153, 153, 153),
            )

    # -- callbacks --

    def _on_exp_type(self, sender, app_data, user_data):
        if app_data in EXPERIMENT_TYPES:
            self._experiment_type_idx = (
                EXPERIMENT_TYPES.index(app_data)
            )
