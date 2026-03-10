"""Tracking panel -- virtual fly vs real fly relationship.

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
    from flocroscope.comms.hub import CommsHub

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

        self.group_tag = "grp_tracking"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public setters for stimulus loop --

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
        """Update the real fly state manually."""
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
        """Signed heading difference (virtual - real)."""
        diff = (
            self._virtual_heading_deg
            - self._real_heading_deg
        )
        return (diff + 180.0) % 360.0 - 180.0

    # -- widget creation --

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            dpg.add_text("Arena Top-Down View:")
            dpg.add_separator()

            dpg.add_text(
                "Real Fly (FicTrac):",
                tag="trk_real_label",
                color=(77, 204, 255),
            )
            dpg.add_text("", tag="trk_real_pos")
            dpg.add_text("", tag="trk_real_heading")

            dpg.add_spacer(height=4)

            dpg.add_text(
                "Virtual Fly (Stimulus):",
                tag="trk_virt_label",
                color=(51, 230, 51),
            )
            dpg.add_text("", tag="trk_virt_pos")
            dpg.add_text("", tag="trk_virt_heading")

            dpg.add_separator()

            dpg.add_text("Relationship:")
            dpg.add_text("", tag="trk_distance")
            dpg.add_text("", tag="trk_heading_offset")

            dpg.add_separator()
            dpg.add_text("", tag="trk_indicator")

            dpg.add_spacer(height=4)
            dpg.add_text(
                "[Top-down arena drawing placeholder]",
                color=(128, 128, 128),
            )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

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

        # Real fly
        dpg.set_value(
            "trk_real_pos",
            f"  Pos:     ({self._real_x:6.1f}, "
            f"{self._real_y:6.1f}) mm",
        )
        dpg.set_value(
            "trk_real_heading",
            f"  Heading: {self._real_heading_deg:6.1f} deg",
        )

        # Virtual fly
        dpg.set_value(
            "trk_virt_pos",
            f"  Pos:     ({self._virtual_x:6.1f}, "
            f"{self._virtual_y:6.1f}) mm",
        )
        dpg.set_value(
            "trk_virt_heading",
            f"  Heading: "
            f"{self._virtual_heading_deg:6.1f} deg",
        )

        # Relationship
        dpg.set_value(
            "trk_distance",
            f"  Distance:       {self.distance_mm:6.1f} mm",
        )
        dpg.set_value(
            "trk_heading_offset",
            f"  Heading offset: "
            f"{self.heading_offset_deg:+6.1f} deg",
        )

        # Visual indicator
        d = self.distance_mm
        if d < 5.0:
            dpg.set_value(
                "trk_indicator",
                "Flies are close together",
            )
            dpg.configure_item(
                "trk_indicator", color=(51, 230, 51),
            )
        elif d < self._arena_radius:
            dpg.set_value(
                "trk_indicator", "Moderate separation",
            )
            dpg.configure_item(
                "trk_indicator", color=(230, 230, 51),
            )
        else:
            dpg.set_value(
                "trk_indicator", "Flies are far apart",
            )
            dpg.configure_item(
                "trk_indicator", color=(230, 77, 77),
            )
