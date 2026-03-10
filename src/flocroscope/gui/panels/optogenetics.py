"""Optogenetics / LED control panel.

Dedicated panel for controlling optogenetics LEDs: on/off, pulse
trains, PWM intensity, channel selection, and protocol presets.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub

logger = logging.getLogger(__name__)

# Preset pulse protocols: (label, command, intensity, duration_ms)
_PRESETS: list[tuple[str, str, float, float]] = [
    ("Single 50ms", "pulse", 1.0, 50.0),
    ("Single 100ms", "pulse", 1.0, 100.0),
    ("Sustained ON", "on", 1.0, 0.0),
    ("Half power", "on", 0.5, 0.0),
]


class OptogeneticsPanel:
    """Panel for LED / optogenetics control.

    Args:
        comms: Optional CommsHub that owns the LED endpoint.
    """

    def __init__(
        self,
        comms: CommsHub | None = None,
    ) -> None:
        self._comms = comms
        self._intensity: float = 1.0
        self._duration_ms: float = 50.0
        self._channel: int = 0
        self._pulse_count: int = 0
        self._selected_preset: int = 0

    # -- public helpers for tests --

    @property
    def pulse_count(self) -> int:
        return self._pulse_count

    @property
    def intensity(self) -> float:
        return self._intensity

    # -- drawing --

    def draw(self) -> None:
        """Render the optogenetics panel."""
        import imgui

        imgui.begin("Optogenetics / LED")

        if self._comms is None:
            imgui.text_colored(
                "LED not connected", 0.6, 0.6, 0.6,
            )
            imgui.text(
                "Configure comms.led_port to enable.",
            )
            imgui.end()
            return

        status = self._comms.status
        connected = status.get("led", False)
        if connected:
            imgui.text_colored(
                "Connected", 0.2, 0.9, 0.2,
            )
        else:
            imgui.text_colored(
                "Waiting for LED controller...",
                0.9, 0.6, 0.2,
            )

        imgui.separator()

        # Quick controls
        imgui.text("Quick Controls:")
        if imgui.button("ON"):
            self._send("on", self._intensity)
        imgui.same_line()
        if imgui.button("OFF"):
            self._send("off", 0.0)
        imgui.same_line()
        if imgui.button("PULSE"):
            self._send(
                "pulse", self._intensity, self._duration_ms,
            )
            self._pulse_count += 1

        # Parameters
        imgui.separator()
        imgui.text("Parameters:")
        _, self._intensity = imgui.slider_float(
            "Intensity", self._intensity, 0.0, 1.0,
        )
        _, self._duration_ms = imgui.slider_float(
            "Pulse (ms)", self._duration_ms, 1.0, 1000.0,
        )
        _, self._channel = imgui.input_int(
            "Channel", self._channel,
        )

        # Presets
        imgui.separator()
        imgui.text("Presets:")
        for i, (label, cmd, inten, dur) in enumerate(_PRESETS):
            if imgui.button(label):
                self._send(cmd, inten, dur)
                self._pulse_count += 1 if cmd == "pulse" else 0

        imgui.separator()
        imgui.text(f"Pulses sent: {self._pulse_count}")

        imgui.end()

    def _send(
        self,
        command: str,
        intensity: float,
        duration_ms: float = 0.0,
    ) -> None:
        """Send an LED command via the CommsHub."""
        if self._comms is None:
            return
        try:
            from flocroscope.comms.base import LedCommand
            self._comms.send_led(LedCommand(
                command=command,
                intensity=intensity,
                duration_ms=duration_ms,
                channel=self._channel,
            ))
        except Exception as exc:
            logger.warning("LED send failed: %s", exc)
