"""Behaviour overview panel.

Combines experiment-level status from all subsystems into a single
dashboard: current experiment type, hardware readiness, active
recording state, and a checklist of connected components.

Also includes a launcher for the Fly Bowl Data Capture (FBDC)
MATLAB GUI (https://github.com/kristinbranson/FlyBowlDataCapture).

.. note::

   In the new single-window layout the experiment type selector
   and hardware indicators live in the top bar of ``app.py``.
   This panel is retained for backward compatibility and for
   standalone/testing use.
"""

from __future__ import annotations

import logging
import subprocess
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

        # FBDC launch state
        self._fbdc_matlab_path: str = ""
        self._fbdc_dir: str = ""
        self._fbdc_process: subprocess.Popen | None = None
        self._fbdc_running: bool = False
        self._fbdc_launch_status: str = ""

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

    @property
    def fbdc_running(self) -> bool:
        """Whether an FBDC/MATLAB process was launched."""
        return self._fbdc_running

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

            # -- Fly Bowl Data Capture (FBDC) section --
            dpg.add_separator()
            dpg.add_text("Fly Bowl Data Capture (FBDC):")
            dpg.add_text(
                "MATLAB GUI for behaviour capture "
                "(FlyBowlDataCapture)",
                color=(140, 140, 155),
            )

            dpg.add_input_text(
                label="MATLAB executable",
                tag="fbdc_matlab_path",
                default_value="",
                hint="path/to/matlab",
                width=400,
                callback=self._on_fbdc_matlab_change,
            )
            dpg.add_input_text(
                label="FBDC directory",
                tag="fbdc_dir",
                default_value="",
                hint="path/to/FlyBowlDataCapture",
                width=400,
                callback=self._on_fbdc_dir_change,
            )
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Launch FBDC",
                    tag="fbdc_launch_btn",
                    callback=self._on_fbdc_launch,
                    width=140,
                )
                dpg.add_button(
                    label="Stop FBDC",
                    tag="fbdc_stop_btn",
                    callback=self._on_fbdc_stop,
                    show=False,
                    width=120,
                )
                dpg.add_text(
                    "", tag="fbdc_launch_running",
                    color=(102, 255, 102),
                )
            dpg.add_text(
                "", tag="fbdc_launch_status",
                wrap=400,
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

        # FBDC launch status
        self._update_fbdc_status(dpg)

    def _update_fbdc_status(self, dpg: object) -> None:
        """Update the FBDC launch subprocess status."""
        import dearpygui.dearpygui as dpg

        # Poll subprocess
        if self._fbdc_process is not None:
            ret = self._fbdc_process.poll()
            if ret is not None:
                self._fbdc_running = False
                if ret == 0:
                    self._fbdc_launch_status = (
                        "FBDC/MATLAB exited normally."
                    )
                else:
                    self._fbdc_launch_status = (
                        f"FBDC/MATLAB exited with "
                        f"code {ret}."
                    )
                self._fbdc_process = None

        if self._fbdc_running:
            dpg.configure_item(
                "fbdc_launch_btn", show=False,
            )
            dpg.configure_item(
                "fbdc_stop_btn", show=True,
            )
            dpg.set_value(
                "fbdc_launch_running", "Running...",
            )
        else:
            dpg.configure_item(
                "fbdc_launch_btn", show=True,
            )
            dpg.configure_item(
                "fbdc_stop_btn", show=False,
            )
            dpg.set_value("fbdc_launch_running", "")

        dpg.set_value(
            "fbdc_launch_status",
            self._fbdc_launch_status,
        )

    # -- callbacks ---------------------------------------------------- #

    def _on_exp_type(self, sender, app_data, user_data):
        if app_data in EXPERIMENT_TYPES:
            self._experiment_type_idx = (
                EXPERIMENT_TYPES.index(app_data)
            )

    def _on_fbdc_matlab_change(
        self, sender, app_data, user_data,
    ):
        self._fbdc_matlab_path = app_data

    def _on_fbdc_dir_change(
        self, sender, app_data, user_data,
    ):
        self._fbdc_dir = app_data

    def _on_fbdc_launch(
        self, sender, app_data, user_data,
    ):
        self._launch_fbdc()

    def _on_fbdc_stop(
        self, sender, app_data, user_data,
    ):
        self._stop_fbdc()

    # -- actions ------------------------------------------------------ #

    def _launch_fbdc(self) -> None:
        """Launch Fly Bowl Data Capture via MATLAB."""
        import dearpygui.dearpygui as dpg

        matlab_path = dpg.get_value("fbdc_matlab_path")
        fbdc_dir = dpg.get_value("fbdc_dir")

        if not matlab_path or not matlab_path.strip():
            self._fbdc_launch_status = (
                "No MATLAB executable path configured."
            )
            return

        if not fbdc_dir or not fbdc_dir.strip():
            self._fbdc_launch_status = (
                "No FBDC directory configured."
            )
            return

        matlab_path = matlab_path.strip()
        fbdc_dir = fbdc_dir.strip()

        matlab_cmd = (
            f"cd('{fbdc_dir}'); FlyBowlDataCapture"
        )
        cmd = [matlab_path, "-r", matlab_cmd]

        logger.info("Launching FBDC: %s", cmd)

        try:
            self._fbdc_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._fbdc_running = True
            self._fbdc_launch_status = (
                f"Launched FBDC/MATLAB "
                f"(PID {self._fbdc_process.pid})"
            )
            logger.info(
                "FBDC started: PID %d",
                self._fbdc_process.pid,
            )
        except Exception as exc:
            self._fbdc_launch_status = (
                f"Failed to launch: {exc}"
            )
            logger.error(
                "Failed to launch FBDC: %s", exc,
            )

    def _stop_fbdc(self) -> None:
        """Stop the running FBDC/MATLAB subprocess."""
        if self._fbdc_process is not None:
            self._fbdc_process.terminate()
            self._fbdc_launch_status = (
                "FBDC/MATLAB terminated."
            )
            logger.info("FBDC/MATLAB terminated")
