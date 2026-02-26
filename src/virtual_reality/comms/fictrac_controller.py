"""FicTrac-driven fly movement controller.

Drop-in replacement for :class:`AutonomousFlyController` and
:class:`KeyboardFlyController` that reads position and heading
from a live FicTrac connection via the :class:`CommsHub`.
"""

from __future__ import annotations

import math
import logging
from typing import TYPE_CHECKING

from virtual_reality.math_utils.arena import clamp_to_arena

if TYPE_CHECKING:
    from virtual_reality.comms.hub import CommsHub

logger = logging.getLogger(__name__)


class FicTracController:
    """Movement controller driven by FicTrac treadmill data.

    Converts FicTrac's integrated position (radians on the ball
    surface) to arena coordinates (mm) using the ball radius.

    Args:
        hub: The :class:`CommsHub` providing FicTrac data.
        ball_radius_mm: Physical radius of the treadmill ball.
        arena_radius: Arena boundary radius in mm.
        gain: Scaling factor applied to FicTrac displacements.
    """

    def __init__(
        self,
        hub: CommsHub,
        ball_radius_mm: float = 4.5,
        arena_radius: float = 40.0,
        gain: float = 1.0,
    ) -> None:
        self._hub = hub
        self._ball_radius = ball_radius_mm
        self._arena_radius = arena_radius
        self._gain = gain

        self.x: float = 0.0
        self.y: float = 0.0
        self.heading_deg: float = 0.0
        self.speed: float = 0.0

        self._frames_received = 0

    def update(self, dt: float) -> None:
        """Poll FicTrac and update position.

        If no new data is available, position is unchanged (the fly
        stays where it was).

        Args:
            dt: Time step in seconds (unused — timing comes from
                FicTrac).
        """
        frame = self._hub.poll_fictrac()
        if frame is None:
            return

        self._frames_received += 1

        # Convert integrated radians to mm
        self.x = frame.x_rad * self._ball_radius * self._gain
        self.y = frame.y_rad * self._ball_radius * self._gain
        self.heading_deg = math.degrees(frame.heading_rad) % 360.0
        self.speed = frame.speed

        # Clamp to arena
        self.x, self.y = clamp_to_arena(
            self.x, self.y, self._arena_radius,
        )

    @property
    def heading_rad(self) -> float:
        """Current heading in radians."""
        return math.radians(self.heading_deg)

    @property
    def frames_received(self) -> int:
        """Total number of FicTrac frames processed."""
        return self._frames_received

    @property
    def connected(self) -> bool:
        """Whether FicTrac is actively sending data."""
        return (
            self._hub.fictrac is not None
            and self._hub.fictrac.connected
        )
