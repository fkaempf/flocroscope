"""Communications status panel.

Displays endpoint connection status, live FicTrac data, ScanImage
events, and LED/presenter controls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub

logger = logging.getLogger(__name__)


class CommsPanel:
    """Panel for communications endpoint status and control.

    Args:
        comms: Optional CommsHub instance.  If None, the panel
            shows a disabled state.
    """

    def __init__(self, comms: CommsHub | None = None) -> None:
        self._comms = comms

    @property
    def comms(self) -> CommsHub | None:
        """The current CommsHub."""
        return self._comms

    @comms.setter
    def comms(self, value: CommsHub | None) -> None:
        self._comms = value

    def draw(self) -> None:
        """Render the comms panel."""
        import imgui

        imgui.begin("Communications")

        if self._comms is None:
            imgui.text_colored(
                "Comms not active", 0.6, 0.6, 0.6,
            )
            imgui.text("Enable in config: comms.enabled = true")
            imgui.end()
            return

        status = self._comms.status
        imgui.text("Endpoint Status:")
        imgui.separator()

        for name, connected in status.items():
            if connected:
                imgui.text_colored(
                    f"  {name}", 0.2, 0.9, 0.2,
                )
                imgui.same_line()
                imgui.text("connected")
            else:
                imgui.text_colored(
                    f"  {name}", 0.9, 0.3, 0.3,
                )
                imgui.same_line()
                imgui.text("disconnected")

        imgui.separator()

        # FicTrac live data
        if status.get("fictrac"):
            self._draw_fictrac()

        # ScanImage events
        if status.get("scanimage"):
            self._draw_scanimage()

        # LED controls
        if status.get("led"):
            self._draw_led_controls()

        # Presenter controls
        if status.get("presenter"):
            self._draw_presenter_controls()

        imgui.end()

    def _draw_fictrac(self) -> None:
        """Draw FicTrac live data section."""
        import imgui

        imgui.text("FicTrac Data:")
        frame = self._comms.poll_fictrac()
        if frame is not None:
            imgui.text(
                f"  Heading: {frame.heading_rad:.2f} rad",
            )
            imgui.text(f"  Speed: {frame.speed:.4f}")
            imgui.text(
                f"  Position: ({frame.x_rad:.3f}, "
                f"{frame.y_rad:.3f}) rad",
            )

    def _draw_scanimage(self) -> None:
        """Draw ScanImage events section."""
        import imgui

        imgui.text("ScanImage:")
        events = self._comms.poll_scanimage()
        if events:
            for ev in events[-3:]:
                imgui.text(
                    f"  {ev.event_type}: {ev.metadata}",
                )

    def _draw_led_controls(self) -> None:
        """Draw LED control buttons."""
        import imgui
        from flocroscope.comms.base import LedCommand

        imgui.separator()
        imgui.text("LED Control:")
        if imgui.button("LED On"):
            self._comms.send_led(
                LedCommand(command="on", intensity=1.0),
            )
        imgui.same_line()
        if imgui.button("LED Off"):
            self._comms.send_led(
                LedCommand(command="off", intensity=0.0),
            )
        imgui.same_line()
        if imgui.button("Pulse"):
            self._comms.send_led(LedCommand(
                command="pulse", intensity=1.0,
                duration_ms=50.0,
            ))

    def _draw_presenter_controls(self) -> None:
        """Draw presenter control buttons."""
        import imgui
        from flocroscope.comms.base import PresenterCommand

        imgui.separator()
        imgui.text("Fly Presenter:")
        if imgui.button("Present"):
            self._comms.send_presenter(
                PresenterCommand(command="present"),
            )
        imgui.same_line()
        if imgui.button("Retract"):
            self._comms.send_presenter(
                PresenterCommand(command="retract"),
            )
