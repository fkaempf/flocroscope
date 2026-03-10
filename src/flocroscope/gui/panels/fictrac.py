"""FicTrac treadmill panel.

Dedicated panel for monitoring ball-tracking data from FicTrac,
displaying heading, speed, integrated position, and ball radius
configuration.  Provides a richer view than the summary line in
:class:`CommsPanel`.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import CommsConfig

logger = logging.getLogger(__name__)

# Ring-buffer length for the speed history sparkline.
_HISTORY_LEN = 200


class FicTracPanel:
    """Panel for live FicTrac treadmill data.

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

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public helpers for tests --

    @property
    def frames_received(self) -> int:
        return self._frames_received

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

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._comms is None:
            dpg.show_item("ft_inactive")
            dpg.show_item("ft_hint")
            dpg.hide_item("ft_active")
            return

        dpg.hide_item("ft_inactive")
        dpg.hide_item("ft_hint")
        dpg.show_item("ft_active")

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
