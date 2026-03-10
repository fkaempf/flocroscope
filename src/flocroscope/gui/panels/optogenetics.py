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
        self.group_tag = "grp_optogenetics"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public helpers for tests --

    @property
    def pulse_count(self) -> int:
        return self._pulse_count

    @property
    def intensity(self) -> float:
        return self._intensity

    # -- widget creation --

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            dpg.add_text(
                "LED not connected",
                tag="opto_inactive",
                color=(153, 153, 153),
            )
            dpg.add_text(
                "Configure comms.led_port to enable.",
                tag="opto_hint",
            )

            with dpg.group(
                tag="opto_active", show=False,
            ):
                dpg.add_text("", tag="opto_conn_status")
                dpg.add_separator()

                dpg.add_text("Quick Controls:")
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="ON",
                        callback=self._on_led_on,
                    )
                    dpg.add_button(
                        label="OFF",
                        callback=self._on_led_off,
                    )
                    dpg.add_button(
                        label="PULSE",
                        callback=self._on_led_pulse,
                    )

                dpg.add_separator()
                dpg.add_text("Parameters:")
                dpg.add_slider_float(
                    label="Intensity",
                    tag="opto_intensity",
                    default_value=self._intensity,
                    min_value=0.0,
                    max_value=1.0,
                    callback=self._on_intensity,
                )
                dpg.add_slider_float(
                    label="Pulse (ms)",
                    tag="opto_duration",
                    default_value=self._duration_ms,
                    min_value=1.0,
                    max_value=1000.0,
                    callback=self._on_duration,
                )
                dpg.add_input_int(
                    label="Channel",
                    tag="opto_channel",
                    default_value=self._channel,
                    callback=self._on_channel,
                )

                dpg.add_separator()
                dpg.add_text("Presets:")
                for i, (label, cmd, inten, dur) in enumerate(
                    _PRESETS,
                ):
                    dpg.add_button(
                        label=label,
                        callback=self._on_preset,
                        user_data=i,
                    )

                dpg.add_separator()
                dpg.add_text(
                    "", tag="opto_pulse_count",
                )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._comms is None:
            dpg.show_item("opto_inactive")
            dpg.show_item("opto_hint")
            dpg.hide_item("opto_active")
            return

        dpg.hide_item("opto_inactive")
        dpg.hide_item("opto_hint")
        dpg.show_item("opto_active")

        status = self._comms.status
        connected = status.get("led", False)
        if connected:
            dpg.set_value("opto_conn_status", "Connected")
            dpg.configure_item(
                "opto_conn_status", color=(51, 230, 51),
            )
        else:
            dpg.set_value(
                "opto_conn_status",
                "Waiting for LED controller...",
            )
            dpg.configure_item(
                "opto_conn_status", color=(230, 153, 51),
            )

        dpg.set_value(
            "opto_pulse_count",
            f"Pulses sent: {self._pulse_count}",
        )

    # -- callbacks --

    def _on_intensity(self, sender, app_data, user_data):
        self._intensity = app_data

    def _on_duration(self, sender, app_data, user_data):
        self._duration_ms = app_data

    def _on_channel(self, sender, app_data, user_data):
        self._channel = app_data

    def _on_led_on(self, sender, app_data, user_data):
        self._send("on", self._intensity)

    def _on_led_off(self, sender, app_data, user_data):
        self._send("off", 0.0)

    def _on_led_pulse(self, sender, app_data, user_data):
        self._send(
            "pulse", self._intensity, self._duration_ms,
        )
        self._pulse_count += 1

    def _on_preset(self, sender, app_data, user_data):
        idx = user_data
        _, cmd, inten, dur = _PRESETS[idx]
        self._send(cmd, inten, dur)
        if cmd == "pulse":
            self._pulse_count += 1

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
