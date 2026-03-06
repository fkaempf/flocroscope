"""Tracking panel — virtual fly vs real fly relationship.

Displays a top-down arena view showing the real fly position
(from FicTrac) alongside the virtual stimulus fly, with heading
arrows, distance readout, and angular offset.  This lets the
experimenter verify that the closed-loop coupling is correct.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.comms.hub import CommsHub

logger = logging.getLogger(__name__)


class TrackingPanel:
    """Panel showing virtual-fly / real-fly relationship.

    Args:
        comms: Optional CommsHub for live FicTrac data.
        arena_radius_mm: Arena radius for the top-down view.
    """

    def __init__(
        self,
        comms: CommsHub | None = None,
        arena_radius_mm: float = 40.0,
    ) -> None:
        self._comms = comms
        self._arena_radius = arena_radius_mm

        # Real fly state (from FicTrac)
        self._real_x: float = 0.0
        self._real_y: float = 0.0
        self._real_heading_deg: float = 0.0

        # Virtual fly state (set externally by stimulus loop)
        self._virtual_x: float = 0.0
        self._virtual_y: float = 0.0
        self._virtual_heading_deg: float = 0.0

    # -- public setters for stimulus loop to push state --

    def set_virtual_state(
        self, x: float, y: float, heading_deg: float,
    ) -> None:
        """Update the virtual fly state from the stimulus."""
        self._virtual_x = x
        self._virtual_y = y
        self._virtual_heading_deg = heading_deg

    def set_real_state(
        self, x: float, y: float, heading_deg: float,
    ) -> None:
        """Update the real fly state manually or from FicTrac."""
        self._real_x = x
        self._real_y = y
        self._real_heading_deg = heading_deg

    # -- computed properties --

    @property
    def distance_mm(self) -> float:
        """Euclidean distance between virtual and real fly."""
        dx = self._virtual_x - self._real_x
        dy = self._virtual_y - self._real_y
        return math.hypot(dx, dy)

    @property
    def heading_offset_deg(self) -> float:
        """Signed heading difference (virtual - real), in degrees."""
        diff = self._virtual_heading_deg - self._real_heading_deg
        # Normalise to [-180, +180]
        return (diff + 180.0) % 360.0 - 180.0

    # -- drawing --

    def draw(self) -> None:
        """Render the tracking panel."""
        import imgui

        imgui.begin("Tracking (Virtual vs Real)")

        # Poll FicTrac for real fly position
        if self._comms is not None:
            frame = self._comms.poll_fictrac()
            if frame is not None:
                ball_r = 1.0
                self._real_heading_deg = math.degrees(
                    frame.heading_rad,
                )
                self._real_x = frame.x_rad * ball_r
                self._real_y = frame.y_rad * ball_r

        # Top-down arena view (text placeholder for now)
        imgui.text("Arena Top-Down View:")
        imgui.separator()

        # Real fly
        imgui.text_colored("Real Fly (FicTrac):", 0.3, 0.8, 1.0)
        imgui.text(
            f"  Pos:     ({self._real_x:6.1f}, "
            f"{self._real_y:6.1f}) mm",
        )
        imgui.text(
            f"  Heading: {self._real_heading_deg:6.1f} deg",
        )

        imgui.spacing()

        # Virtual fly
        imgui.text_colored(
            "Virtual Fly (Stimulus):", 0.2, 0.9, 0.2,
        )
        imgui.text(
            f"  Pos:     ({self._virtual_x:6.1f}, "
            f"{self._virtual_y:6.1f}) mm",
        )
        imgui.text(
            f"  Heading: {self._virtual_heading_deg:6.1f} deg",
        )

        imgui.separator()

        # Relationship metrics
        imgui.text("Relationship:")
        imgui.text(
            f"  Distance:       {self.distance_mm:6.1f} mm",
        )
        imgui.text(
            f"  Heading offset: "
            f"{self.heading_offset_deg:+6.1f} deg",
        )

        # Visual indicator
        imgui.separator()
        d = self.distance_mm
        if d < 5.0:
            imgui.text_colored(
                "Flies are close together",
                0.2, 0.9, 0.2,
            )
        elif d < self._arena_radius:
            imgui.text_colored(
                "Moderate separation",
                0.9, 0.9, 0.2,
            )
        else:
            imgui.text_colored(
                "Flies are far apart",
                0.9, 0.3, 0.3,
            )

        # Placeholder for canvas-based top-down drawing
        imgui.spacing()
        imgui.text_colored(
            "[Top-down arena drawing placeholder]",
            0.5, 0.5, 0.5,
        )

        imgui.end()
