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
    from virtual_reality.comms.hub import CommsHub

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

    # -- public helpers for tests --

    @property
    def trial_count(self) -> int:
        return self._trial_count

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # -- drawing --

    def draw(self) -> None:
        """Render the ScanImage panel."""
        import imgui

        imgui.begin("ScanImage / 2-Photon")

        if self._comms is None:
            imgui.text_colored(
                "ScanImage not connected", 0.6, 0.6, 0.6,
            )
            imgui.text(
                "Configure comms.scanimage_port to enable.",
            )
            imgui.end()
            return

        status = self._comms.status
        connected = status.get("scanimage", False)
        if connected:
            imgui.text_colored(
                "Connected", 0.2, 0.9, 0.2,
            )
        else:
            imgui.text_colored(
                "Waiting for ScanImage...", 0.9, 0.6, 0.2,
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

        imgui.separator()

        # Acquisition status
        if self._acquiring:
            imgui.text_colored(
                "ACQUIRING", 0.2, 0.9, 0.2,
            )
        else:
            imgui.text_colored(
                "IDLE", 0.9, 0.9, 0.2,
            )

        imgui.spacing()
        imgui.text(f"Trials:      {self._trial_count}")
        imgui.text(f"Frame ticks: {self._frame_count}")

        # Event log
        imgui.separator()
        imgui.text("Event Log:")
        if self._event_log:
            for line in list(self._event_log)[-10:]:
                imgui.bullet_text(line)
        else:
            imgui.text_colored(
                "No events yet", 0.6, 0.6, 0.6,
            )

        imgui.end()
