"""ScanImage / 2-photon imaging panel.

Dedicated panel for monitoring the ScanImage 2-photon microscopy
connection: trial events (start/stop), frame clock ticks, and
acquisition status.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub

logger = logging.getLogger(__name__)

_EVENT_LOG_MAX = 50


class ScanImagePanel:
    """Panel for ScanImage 2-photon sync status.

    Args:
        comms: Optional CommsHub that owns the ScanImage endpoint.
    """

    def __init__(
        self,
        comms: CommsHub | None = None,
    ) -> None:
        self._comms = comms
        self._event_log: deque[str] = deque(
            maxlen=_EVENT_LOG_MAX,
        )
        self._trial_count: int = 0
        self._frame_count: int = 0
        self._acquiring: bool = False
        self.group_tag = "grp_scanimage"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    # -- public helpers for tests --

    @property
    def trial_count(self) -> int:
        return self._trial_count

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # -- widget creation --

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            dpg.add_text(
                "ScanImage not connected",
                tag="si_inactive",
                color=(153, 153, 153),
            )
            dpg.add_text(
                "Configure comms.scanimage_port to enable.",
                tag="si_hint",
            )

            with dpg.group(
                tag="si_active", show=False,
            ):
                dpg.add_text("", tag="si_conn_status")
                dpg.add_separator()

                dpg.add_text(
                    "", tag="si_acq_status",
                )
                dpg.add_spacer(height=4)
                dpg.add_text("", tag="si_trials")
                dpg.add_text("", tag="si_frames")

                dpg.add_separator()
                dpg.add_text("Event Log:")
                for i in range(10):
                    dpg.add_text(
                        "", tag=f"si_ev_{i}",
                    )
                dpg.add_text(
                    "No events yet",
                    tag="si_no_events",
                    color=(153, 153, 153),
                )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._comms is None:
            dpg.show_item("si_inactive")
            dpg.show_item("si_hint")
            dpg.hide_item("si_active")
            return

        dpg.hide_item("si_inactive")
        dpg.hide_item("si_hint")
        dpg.show_item("si_active")

        status = self._comms.status
        connected = status.get("scanimage", False)
        if connected:
            dpg.set_value("si_conn_status", "Connected")
            dpg.configure_item(
                "si_conn_status", color=(51, 230, 51),
            )
        else:
            dpg.set_value(
                "si_conn_status",
                "Waiting for ScanImage...",
            )
            dpg.configure_item(
                "si_conn_status", color=(230, 153, 51),
            )

        # Poll events
        events = self._comms.poll_scanimage()
        if events:
            for ev in events:
                label = (
                    f"{ev.event_type}: {ev.metadata}"
                    if hasattr(ev, "metadata") else str(ev)
                )
                self._event_log.append(label)
                if ev.event_type == "trial_start":
                    self._trial_count += 1
                    self._acquiring = True
                elif ev.event_type == "trial_stop":
                    self._acquiring = False
                elif ev.event_type == "frame_clock":
                    self._frame_count += 1

        # Acquisition status
        if self._acquiring:
            dpg.set_value("si_acq_status", "ACQUIRING")
            dpg.configure_item(
                "si_acq_status", color=(51, 230, 51),
            )
        else:
            dpg.set_value("si_acq_status", "IDLE")
            dpg.configure_item(
                "si_acq_status", color=(230, 230, 51),
            )

        dpg.set_value(
            "si_trials",
            f"Trials:      {self._trial_count}",
        )
        dpg.set_value(
            "si_frames",
            f"Frame ticks: {self._frame_count}",
        )

        # Event log
        log_list = list(self._event_log)[-10:]
        if log_list:
            dpg.hide_item("si_no_events")
            for i in range(10):
                if i < len(log_list):
                    dpg.set_value(
                        f"si_ev_{i}",
                        f"  {log_list[i]}",
                    )
                    dpg.show_item(f"si_ev_{i}")
                else:
                    dpg.set_value(f"si_ev_{i}", "")
                    dpg.hide_item(f"si_ev_{i}")
        else:
            dpg.show_item("si_no_events")
            for i in range(10):
                dpg.hide_item(f"si_ev_{i}")
