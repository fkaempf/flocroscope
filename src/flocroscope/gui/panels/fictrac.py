"""FicTrac treadmill panel.

Dedicated panel for monitoring ball-tracking data from FicTrac,
displaying heading, speed, integrated position, and ball radius
configuration.  Provides a richer view than the summary line in
:class:`CommsPanel`.

Also includes controls to launch and stop the FicTrac executable
directly from the GUI.
"""

from __future__ import annotations

import logging
import math
import subprocess
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import CommsConfig

logger = logging.getLogger(__name__)

# Ring-buffer length for the speed history sparkline.
_HISTORY_LEN = 200


class FicTracPanel:
    """Panel for live FicTrac treadmill data and launch controls.

    Args:
        comms: Optional CommsHub that owns the FicTrac endpoint.
        config: Optional CommsConfig for ball-radius display.
    """

    def __init__(
        self,
        comms: CommsHub | None = None,
        config: CommsConfig | None = None,
    ) -> None:
        self._comms = comms
        self._config = config
        self._speed_history: deque[float] = deque(
            maxlen=_HISTORY_LEN,
        )
        self._heading_deg: float = 0.0
        self._speed: float = 0.0
        self._x_mm: float = 0.0
        self._y_mm: float = 0.0
        self._frames_received: int = 0
        self.group_tag = "grp_fictrac"

        # FicTrac launch state
        self._ft_exe_path: str = ""
        self._ft_config_path: str = ""
        self._ft_process: subprocess.Popen | None = None
        self._ft_running: bool = False
        self._ft_launch_status: str = ""

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public helpers for tests --

    @property
    def frames_received(self) -> int:
        return self._frames_received

    @property
    def ft_running(self) -> bool:
        """Whether a FicTrac process was launched from this panel."""
        return self._ft_running

    # -- widget creation --

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            dpg.add_text(
                "FicTrac not connected",
                tag="ft_inactive",
                color=(153, 153, 153),
            )
            dpg.add_text(
                "Configure comms.fictrac_port to enable.",
                tag="ft_hint",
            )

            with dpg.group(
                tag="ft_active", show=False,
            ):
                dpg.add_text(
                    "", tag="ft_conn_status",
                )
                dpg.add_separator()

                dpg.add_text("", tag="ft_ball_radius")
                dpg.add_spacer(height=4)
                dpg.add_text("", tag="ft_heading")
                dpg.add_text("", tag="ft_speed")
                dpg.add_text("", tag="ft_x")
                dpg.add_text("", tag="ft_y")
                dpg.add_text("", tag="ft_frames")

                dpg.add_separator()
                dpg.add_text("Speed history:")
                dpg.add_text(
                    "", tag="ft_sparkline",
                    color=(153, 153, 153),
                )

            # -- Launch FicTrac section --
            dpg.add_separator()
            dpg.add_text("Launch FicTrac:")

            dpg.add_input_text(
                label="Executable",
                tag="ft_exe_path",
                default_value="",
                hint="path/to/fictrac",
                width=400,
                callback=self._on_exe_path_change,
            )
            dpg.add_input_text(
                label="Config file",
                tag="ft_config_path",
                default_value="",
                hint="path/to/config.txt",
                width=400,
                callback=self._on_config_path_change,
            )
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Launch FicTrac",
                    tag="ft_launch_btn",
                    callback=self._on_launch,
                    width=160,
                )
                dpg.add_button(
                    label="Stop FicTrac",
                    tag="ft_stop_btn",
                    callback=self._on_stop,
                    show=False,
                    width=140,
                )
                dpg.add_text(
                    "", tag="ft_launch_running",
                    color=(102, 255, 102),
                )
            dpg.add_text(
                "", tag="ft_launch_status",
                wrap=400,
            )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._comms is None:
            dpg.show_item("ft_inactive")
            dpg.show_item("ft_hint")
            dpg.hide_item("ft_active")
        else:
            dpg.hide_item("ft_inactive")
            dpg.hide_item("ft_hint")
            dpg.show_item("ft_active")
            self._update_comms(dpg)

        self._update_launch_status(dpg)

    def _update_comms(self, dpg: object) -> None:
        """Update the comms monitoring section."""
        import dearpygui.dearpygui as dpg

        status = self._comms.status
        connected = status.get("fictrac", False)
        if connected:
            dpg.set_value("ft_conn_status", "Connected")
            dpg.configure_item(
                "ft_conn_status", color=(51, 230, 51),
            )
        else:
            dpg.set_value(
                "ft_conn_status",
                "Waiting for FicTrac...",
            )
            dpg.configure_item(
                "ft_conn_status", color=(230, 153, 51),
            )

        # Poll latest frame
        frame = self._comms.poll_fictrac()
        if frame is not None:
            self._frames_received += 1
            ball_r = 1.0
            if (
                self._config is not None
                and self._config.fictrac_ball_radius_mm > 0
            ):
                ball_r = (
                    self._config.fictrac_ball_radius_mm
                )
            self._heading_deg = math.degrees(
                frame.heading_rad,
            )
            self._speed = frame.speed * ball_r
            self._x_mm = frame.x_rad * ball_r
            self._y_mm = frame.y_rad * ball_r
            self._speed_history.append(self._speed)

        # Ball config
        if self._config is not None:
            dpg.set_value(
                "ft_ball_radius",
                f"Ball radius: "
                f"{self._config.fictrac_ball_radius_mm:.1f}"
                " mm",
            )

        # Live data
        dpg.set_value(
            "ft_heading",
            f"Heading:  {self._heading_deg:7.1f} deg",
        )
        dpg.set_value(
            "ft_speed",
            f"Speed:    {self._speed:7.2f} mm/s",
        )
        dpg.set_value(
            "ft_x", f"X:        {self._x_mm:7.2f} mm",
        )
        dpg.set_value(
            "ft_y", f"Y:        {self._y_mm:7.2f} mm",
        )
        dpg.set_value(
            "ft_frames",
            f"Frames:   {self._frames_received}",
        )

        # Speed sparkline placeholder
        if self._speed_history:
            dpg.set_value(
                "ft_sparkline",
                f"[sparkline placeholder - "
                f"{len(self._speed_history)} samples]",
            )
        else:
            dpg.set_value("ft_sparkline", "No data yet")

    def _update_launch_status(self, dpg: object) -> None:
        """Update the launch subprocess status."""
        import dearpygui.dearpygui as dpg

        # Poll subprocess
        if self._ft_process is not None:
            ret = self._ft_process.poll()
            if ret is not None:
                self._ft_running = False
                if ret == 0:
                    self._ft_launch_status = (
                        "FicTrac exited normally."
                    )
                else:
                    self._ft_launch_status = (
                        f"FicTrac exited with code {ret}."
                    )
                self._ft_process = None

        if self._ft_running:
            dpg.configure_item(
                "ft_launch_btn", show=False,
            )
            dpg.configure_item(
                "ft_stop_btn", show=True,
            )
            dpg.set_value(
                "ft_launch_running", "Running...",
            )
        else:
            dpg.configure_item(
                "ft_launch_btn", show=True,
            )
            dpg.configure_item(
                "ft_stop_btn", show=False,
            )
            dpg.set_value("ft_launch_running", "")

        dpg.set_value(
            "ft_launch_status", self._ft_launch_status,
        )

    # -- callbacks ---------------------------------------------------- #

    def _on_exe_path_change(
        self, sender, app_data, user_data,
    ):
        self._ft_exe_path = app_data

    def _on_config_path_change(
        self, sender, app_data, user_data,
    ):
        self._ft_config_path = app_data

    def _on_launch(self, sender, app_data, user_data):
        self._launch_fictrac()

    def _on_stop(self, sender, app_data, user_data):
        self._stop_fictrac()

    # -- actions ------------------------------------------------------ #

    def _launch_fictrac(self) -> None:
        """Launch FicTrac via the configured executable path."""
        import dearpygui.dearpygui as dpg

        exe_path = dpg.get_value("ft_exe_path")
        config_path = dpg.get_value("ft_config_path")

        if not exe_path or not exe_path.strip():
            self._ft_launch_status = (
                "No FicTrac executable path configured."
            )
            return

        exe_path = exe_path.strip()
        cmd: list[str] = [exe_path]
        if config_path and config_path.strip():
            cmd.append(config_path.strip())

        logger.info("Launching FicTrac: %s", cmd)

        try:
            self._ft_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._ft_running = True
            self._ft_launch_status = (
                f"Launched FicTrac "
                f"(PID {self._ft_process.pid})"
            )
            logger.info(
                "FicTrac started: PID %d",
                self._ft_process.pid,
            )
        except Exception as exc:
            self._ft_launch_status = (
                f"Failed to launch: {exc}"
            )
            logger.error(
                "Failed to launch FicTrac: %s", exc,
            )

    def _stop_fictrac(self) -> None:
        """Stop the running FicTrac subprocess."""
        if self._ft_process is not None:
            self._ft_process.terminate()
            self._ft_launch_status = (
                "FicTrac terminated."
            )
            logger.info("FicTrac terminated")
