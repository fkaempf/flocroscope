"""ScanImage / 2-photon imaging panel.

Dedicated panel for monitoring the ScanImage 2-photon microscopy
connection: trial events (start/stop), frame clock ticks, and
acquisition status.  Includes controls to launch ScanImage
via MATLAB -- ScanImage is a MATLAB application, not a standalone
executable.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import CommsConfig

logger = logging.getLogger(__name__)

_EVENT_LOG_MAX = 50

# Default MATLAB executable hints per platform
_MATLAB_EXE_HINTS: dict[str, str] = {
    "win32": r"C:\Program Files\MATLAB\R2024a\bin\matlab.exe",
    "linux": "/usr/local/MATLAB/R2024a/bin/matlab",
    "darwin": (
        "/Applications/MATLAB_R2024a.app/bin/matlab"
    ),
}


class ScanImagePanel:
    """Panel for ScanImage 2-photon sync status and launch.

    Args:
        comms: Optional CommsHub that owns the ScanImage endpoint.
        config: Optional CommsConfig for scanimage_path.
    """

    def __init__(
        self,
        comms: CommsHub | None = None,
        config: CommsConfig | None = None,
    ) -> None:
        self._comms = comms
        self._config = config
        self._event_log: deque[str] = deque(
            maxlen=_EVENT_LOG_MAX,
        )
        self._trial_count: int = 0
        self._frame_count: int = 0
        self._acquiring: bool = False
        self._si_process: subprocess.Popen | None = None
        self._si_running: bool = False
        self._si_launch_status: str = ""
        self.group_tag = "grp_scanimage"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public helpers for tests --

    @property
    def trial_count(self) -> int:
        return self._trial_count

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def si_running(self) -> bool:
        """Whether a ScanImage process was launched from this panel."""
        return self._si_running

    # -- widget creation --

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            dpg.add_text(
                "ScanImage not connected",
                tag="si_inactive",
                color=(153, 153, 153),
            )
            dpg.add_text(
                "Configure comms.scanimage_port to enable.",
                tag="si_hint",
            )

            with dpg.group(
                tag="si_active", show=False,
            ):
                dpg.add_text("", tag="si_conn_status")
                dpg.add_separator()

                dpg.add_text("", tag="si_acq_status")
                dpg.add_spacer(height=4)
                dpg.add_text("", tag="si_trials")
                dpg.add_text("", tag="si_frames")

                dpg.add_separator()
                dpg.add_text("Event Log:")
                for i in range(10):
                    dpg.add_text("", tag=f"si_ev_{i}")
                dpg.add_text(
                    "No events yet",
                    tag="si_no_events",
                    color=(153, 153, 153),
                )

            # -- Launch ScanImage section --
            dpg.add_separator()
            dpg.add_text("Launch ScanImage:")
            dpg.add_text(
                "ScanImage runs inside MATLAB "
                "(not a standalone executable).",
                color=(140, 140, 155),
            )

            hint = _MATLAB_EXE_HINTS.get(
                sys.platform, "",
            )
            default_path = ""
            if (
                self._config is not None
                and self._config.scanimage_path
            ):
                default_path = self._config.scanimage_path

            dpg.add_input_text(
                label="MATLAB executable",
                tag="si_launch_path",
                default_value=default_path,
                hint=hint or "path/to/matlab",
                width=400,
                callback=self._on_path_change,
            )
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Launch ScanImage",
                    tag="si_launch_btn",
                    callback=self._on_launch,
                    width=160,
                )
                dpg.add_button(
                    label="Stop ScanImage",
                    tag="si_stop_btn",
                    callback=self._on_stop,
                    show=False,
                    width=140,
                )
                dpg.add_text(
                    "", tag="si_launch_running",
                    color=(102, 255, 102),
                )
            dpg.add_text(
                "", tag="si_launch_status",
                wrap=400,
            )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._comms is None:
            dpg.show_item("si_inactive")
            dpg.show_item("si_hint")
            dpg.hide_item("si_active")
        else:
            dpg.hide_item("si_inactive")
            dpg.hide_item("si_hint")
            dpg.show_item("si_active")
            self._update_comms(dpg)

        self._update_launch_status(dpg)

    def _update_comms(self, dpg: object) -> None:
        """Update the comms monitoring section."""
        import dearpygui.dearpygui as dpg

        status = self._comms.status
        connected = status.get("scanimage", False)
        if connected:
            dpg.set_value("si_conn_status", "Connected")
            dpg.configure_item(
                "si_conn_status", color=(51, 230, 51),
            )
        else:
            dpg.set_value(
                "si_conn_status",
                "Waiting for ScanImage...",
            )
            dpg.configure_item(
                "si_conn_status", color=(230, 153, 51),
            )

        # Poll events
        events = self._comms.poll_scanimage()
        if events:
            for ev in events:
                label = (
                    f"{ev.event_type}: {ev.metadata}"
                    if hasattr(ev, "metadata") else str(ev)
                )
                self._event_log.append(label)
                if ev.event_type == "trial_start":
                    self._trial_count += 1
                    self._acquiring = True
                elif ev.event_type == "trial_stop":
                    self._acquiring = False
                elif ev.event_type == "frame_clock":
                    self._frame_count += 1

        # Acquisition status
        if self._acquiring:
            dpg.set_value("si_acq_status", "ACQUIRING")
            dpg.configure_item(
                "si_acq_status", color=(51, 230, 51),
            )
        else:
            dpg.set_value("si_acq_status", "IDLE")
            dpg.configure_item(
                "si_acq_status", color=(230, 230, 51),
            )

        dpg.set_value(
            "si_trials",
            f"Trials:      {self._trial_count}",
        )
        dpg.set_value(
            "si_frames",
            f"Frame ticks: {self._frame_count}",
        )

        # Event log
        log_list = list(self._event_log)[-10:]
        if log_list:
            dpg.hide_item("si_no_events")
            for i in range(10):
                if i < len(log_list):
                    dpg.set_value(
                        f"si_ev_{i}",
                        f"  {log_list[i]}",
                    )
                    dpg.show_item(f"si_ev_{i}")
                else:
                    dpg.set_value(f"si_ev_{i}", "")
                    dpg.hide_item(f"si_ev_{i}")
        else:
            dpg.show_item("si_no_events")
            for i in range(10):
                dpg.hide_item(f"si_ev_{i}")

    def _update_launch_status(self, dpg: object) -> None:
        """Update the launch subprocess status."""
        import dearpygui.dearpygui as dpg

        # Poll subprocess
        if self._si_process is not None:
            ret = self._si_process.poll()
            if ret is not None:
                self._si_running = False
                if ret == 0:
                    self._si_launch_status = (
                        "ScanImage/MATLAB exited normally."
                    )
                else:
                    self._si_launch_status = (
                        f"ScanImage/MATLAB exited with "
                        f"code {ret}."
                    )
                self._si_process = None

        if self._si_running:
            dpg.configure_item(
                "si_launch_btn", show=False,
            )
            dpg.configure_item(
                "si_stop_btn", show=True,
            )
            dpg.set_value(
                "si_launch_running", "Running...",
            )
        else:
            dpg.configure_item(
                "si_launch_btn", show=True,
            )
            dpg.configure_item(
                "si_stop_btn", show=False,
            )
            dpg.set_value("si_launch_running", "")

        dpg.set_value(
            "si_launch_status", self._si_launch_status,
        )

    # -- callbacks ---------------------------------------------------- #

    def _on_path_change(self, sender, app_data, user_data):
        if self._config is not None:
            self._config.scanimage_path = app_data

    def _on_launch(self, sender, app_data, user_data):
        self._launch_scanimage()

    def _on_stop(self, sender, app_data, user_data):
        self._stop_scanimage()

    # -- actions ------------------------------------------------------ #

    def _launch_scanimage(self) -> None:
        """Launch ScanImage via MATLAB.

        Reads the MATLAB executable path from the input field and
        invokes ``matlab -r "scanimage"`` to start ScanImage
        within a MATLAB session.
        """
        import dearpygui.dearpygui as dpg

        matlab_path = dpg.get_value("si_launch_path")
        if not matlab_path or not matlab_path.strip():
            self._si_launch_status = (
                "No MATLAB executable path configured. "
                "Set comms.scanimage_path or enter the "
                "path to your MATLAB installation."
            )
            return

        matlab_path = matlab_path.strip()
        cmd = [matlab_path, "-r", "scanimage"]
        logger.info(
            "Launching ScanImage via MATLAB: %s", cmd,
        )

        try:
            self._si_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._si_running = True
            self._si_launch_status = (
                f"Launched ScanImage/MATLAB "
                f"(PID {self._si_process.pid})"
            )
            logger.info(
                "ScanImage/MATLAB started: PID %d",
                self._si_process.pid,
            )
        except Exception as exc:
            self._si_launch_status = (
                f"Failed to launch: {exc}"
            )
            logger.error(
                "Failed to launch ScanImage: %s", exc,
            )

    def _stop_scanimage(self) -> None:
        """Stop the running ScanImage/MATLAB subprocess."""
        if self._si_process is not None:
            self._si_process.terminate()
            self._si_launch_status = (
                "ScanImage/MATLAB terminated."
            )
            logger.info("ScanImage/MATLAB terminated")
