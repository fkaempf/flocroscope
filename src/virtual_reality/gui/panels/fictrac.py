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
    from virtual_reality.comms.hub import CommsHub
    from virtual_reality.config.schema import CommsConfig

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

    # -- public helpers for tests --

    @property
    def frames_received(self) -> int:
        return self._frames_received

    # -- drawing --

    def draw(self) -> None:
        """Render the FicTrac panel."""
        import imgui

        imgui.begin("FicTrac / Treadmill")

        if self._comms is None:
            imgui.text_colored(
                "FicTrac not connected", 0.6, 0.6, 0.6,
            )
            imgui.text(
                "Configure comms.fictrac_port to enable.",
            )
            imgui.end()
            return

        status = self._comms.status
        connected = status.get("fictrac", False)
        if connected:
            imgui.text_colored(
                "Connected", 0.2, 0.9, 0.2,
            )
        else:
            imgui.text_colored(
                "Waiting for FicTrac...", 0.9, 0.6, 0.2,
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
                ball_r = self._config.fictrac_ball_radius_mm
            self._heading_deg = math.degrees(frame.heading_rad)
            self._speed = frame.speed * ball_r
            self._x_mm = frame.x_rad * ball_r
            self._y_mm = frame.y_rad * ball_r
            self._speed_history.append(self._speed)

        imgui.separator()

        # Ball config
        if self._config is not None:
            imgui.text(
                f"Ball radius: "
                f"{self._config.fictrac_ball_radius_mm:.1f} mm",
            )

        # Live data
        imgui.spacing()
        imgui.text(f"Heading:  {self._heading_deg:7.1f} deg")
        imgui.text(f"Speed:    {self._speed:7.2f} mm/s")
        imgui.text(f"X:        {self._x_mm:7.2f} mm")
        imgui.text(f"Y:        {self._y_mm:7.2f} mm")
        imgui.text(f"Frames:   {self._frames_received}")

        # Speed sparkline placeholder
        imgui.separator()
        imgui.text("Speed history:")
        if self._speed_history:
            imgui.text(
                "[sparkline placeholder — "
                f"{len(self._speed_history)} samples]",
            )
        else:
            imgui.text_colored(
                "No data yet", 0.6, 0.6, 0.6,
            )

        imgui.end()
