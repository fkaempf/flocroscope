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
        self.group_tag = "grp_comms"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    @property
    def comms(self) -> CommsHub | None:
        """The current CommsHub."""
        return self._comms

    @comms.setter
    def comms(self, value: CommsHub | None) -> None:
        self._comms = value

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(parent=parent, tag=self.group_tag):
            dpg.add_text(
                "Comms not active", tag="comms_inactive",
                color=(153, 153, 153),
            )
            dpg.add_text(
                "Enable in config: comms.enabled = true",
                tag="comms_hint",
            )

            with dpg.group(tag="comms_active", show=False):
                dpg.add_text("Endpoint Status:")
                dpg.add_separator()

                # Pre-create endpoint status lines
                _endpoints = [
                    "fictrac", "scanimage", "led", "presenter",
                ]
                for ep in _endpoints:
                    with dpg.group(horizontal=True):
                        dpg.add_text(
                            f"  {ep}",
                            tag=f"comms_ep_{ep}_name",
                        )
                        dpg.add_text(
                            "disconnected",
                            tag=f"comms_ep_{ep}_status",
                        )

                dpg.add_separator()

                # FicTrac data section
                with dpg.group(
                    tag="comms_fictrac_section", show=False,
                ):
                    dpg.add_text("FicTrac Data:")
                    dpg.add_text(
                        "", tag="comms_ft_heading",
                    )
                    dpg.add_text(
                        "", tag="comms_ft_speed",
                    )
                    dpg.add_text(
                        "", tag="comms_ft_pos",
                    )

                # ScanImage section
                with dpg.group(
                    tag="comms_si_section", show=False,
                ):
                    dpg.add_text("ScanImage:")
                    dpg.add_text("", tag="comms_si_ev0")
                    dpg.add_text("", tag="comms_si_ev1")
                    dpg.add_text("", tag="comms_si_ev2")

                # LED controls
                with dpg.group(
                    tag="comms_led_section", show=False,
                ):
                    dpg.add_separator()
                    dpg.add_text("LED Control:")
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="LED On",
                            callback=self._on_led_on,
                        )
                        dpg.add_button(
                            label="LED Off",
                            callback=self._on_led_off,
                        )
                        dpg.add_button(
                            label="Pulse",
                            callback=self._on_led_pulse,
                        )

                # Presenter controls
                with dpg.group(
                    tag="comms_pres_section", show=False,
                ):
                    dpg.add_separator()
                    dpg.add_text("Fly Presenter:")
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Present",
                            callback=self._on_present,
                        )
                        dpg.add_button(
                            label="Retract",
                            callback=self._on_retract,
                        )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._comms is None:
            dpg.show_item("comms_inactive")
            dpg.show_item("comms_hint")
            dpg.hide_item("comms_active")
            return

        dpg.hide_item("comms_inactive")
        dpg.hide_item("comms_hint")
        dpg.show_item("comms_active")

        status = self._comms.status
        _endpoints = [
            "fictrac", "scanimage", "led", "presenter",
        ]
        for ep in _endpoints:
            connected = status.get(ep, False)
            if connected:
                dpg.configure_item(
                    f"comms_ep_{ep}_name",
                    color=(51, 230, 51),
                )
                dpg.set_value(
                    f"comms_ep_{ep}_status", "connected",
                )
            else:
                dpg.configure_item(
                    f"comms_ep_{ep}_name",
                    color=(230, 77, 77),
                )
                dpg.set_value(
                    f"comms_ep_{ep}_status", "disconnected",
                )

        # FicTrac data
        if status.get("fictrac"):
            dpg.show_item("comms_fictrac_section")
            frame = self._comms.poll_fictrac()
            if frame is not None:
                dpg.set_value(
                    "comms_ft_heading",
                    f"  Heading: {frame.heading_rad:.2f} rad",
                )
                dpg.set_value(
                    "comms_ft_speed",
                    f"  Speed: {frame.speed:.4f}",
                )
                dpg.set_value(
                    "comms_ft_pos",
                    f"  Position: ({frame.x_rad:.3f}, "
                    f"{frame.y_rad:.3f}) rad",
                )
        else:
            dpg.hide_item("comms_fictrac_section")

        # ScanImage events
        if status.get("scanimage"):
            dpg.show_item("comms_si_section")
            events = self._comms.poll_scanimage()
            if events:
                for i, ev in enumerate(events[-3:]):
                    tag = f"comms_si_ev{i}"
                    dpg.set_value(
                        tag,
                        f"  {ev.event_type}: {ev.metadata}",
                    )
        else:
            dpg.hide_item("comms_si_section")

        # LED controls visibility
        if status.get("led"):
            dpg.show_item("comms_led_section")
        else:
            dpg.hide_item("comms_led_section")

        # Presenter controls visibility
        if status.get("presenter"):
            dpg.show_item("comms_pres_section")
        else:
            dpg.hide_item("comms_pres_section")

    # -- callbacks --

    def _on_led_on(self, sender, app_data, user_data):
        from flocroscope.comms.base import LedCommand
        if self._comms:
            self._comms.send_led(
                LedCommand(command="on", intensity=1.0),
            )

    def _on_led_off(self, sender, app_data, user_data):
        from flocroscope.comms.base import LedCommand
        if self._comms:
            self._comms.send_led(
                LedCommand(command="off", intensity=0.0),
            )

    def _on_led_pulse(self, sender, app_data, user_data):
        from flocroscope.comms.base import LedCommand
        if self._comms:
            self._comms.send_led(LedCommand(
                command="pulse", intensity=1.0,
                duration_ms=50.0,
            ))

    def _on_present(self, sender, app_data, user_data):
        from flocroscope.comms.base import PresenterCommand
        if self._comms:
            self._comms.send_presenter(
                PresenterCommand(command="present"),
            )

    def _on_retract(self, sender, app_data, user_data):
        from flocroscope.comms.base import PresenterCommand
        if self._comms:
            self._comms.send_presenter(
                PresenterCommand(command="retract"),
            )
