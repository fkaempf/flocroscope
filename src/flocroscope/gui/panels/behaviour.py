"""Behaviour overview panel.

Combines experiment-level status from all subsystems into a single
dashboard: current experiment type, hardware readiness, active
recording state, and a checklist of connected components.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import FlocroscopeConfig
    from flocroscope.session.session import Session

logger = logging.getLogger(__name__)

# Experiment types the system supports.
EXPERIMENT_TYPES = [
    "Behavior",
    "VR",
    "2P",
    "2P+VR",
    "Optogenetics",
]


class BehaviourPanel:
    """Dashboard panel for experiment / behaviour overview.

    Args:
        config: Full configuration.
        comms: Optional CommsHub for hardware status.
        session: Optional active Session for recording state.
    """

    def __init__(
        self,
        config: FlocroscopeConfig | None = None,
        comms: CommsHub | None = None,
        session: Session | None = None,
    ) -> None:
        self._config = config
        self._comms = comms
        self._session = session
        self._experiment_type_idx: int = 0

    # -- public helpers --

    @property
    def experiment_type(self) -> str:
        return EXPERIMENT_TYPES[self._experiment_type_idx]

    @property
    def session(self) -> Session | None:
        return self._session

    @session.setter
    def session(self, value: Session | None) -> None:
        self._session = value

    # -- drawing --

    def draw(self) -> None:
        """Render the behaviour dashboard panel."""
        import imgui

        imgui.begin("Behaviour")

        # Experiment type selector
        imgui.text("Experiment Type:")
        changed, self._experiment_type_idx = imgui.combo(
            "##exp_type",
            self._experiment_type_idx,
            EXPERIMENT_TYPES,
        )

        imgui.separator()

        # Hardware checklist
        imgui.text("Hardware Checklist:")
        self._draw_checklist_item(
            "FicTrac (treadmill)", "fictrac",
        )
        self._draw_checklist_item(
            "ScanImage (2P)", "scanimage",
        )
        self._draw_checklist_item(
            "LED (optogenetics)", "led",
        )
        self._draw_checklist_item(
            "Presenter", "presenter",
        )

        imgui.separator()

        # Session status
        imgui.text("Session:")
        if self._session is not None:
            imgui.text_colored(
                "Active", 0.2, 0.9, 0.2,
            )
            imgui.text(
                f"  Trials: {self._session.trial_count}",
            )
        else:
            imgui.text_colored(
                "No active session", 0.6, 0.6, 0.6,
            )

        # Recording status
        imgui.separator()
        imgui.text("Recording:")
        if (
            self._session is not None
            and self._session.is_running
        ):
            imgui.text_colored(
                "RECORDING", 0.9, 0.2, 0.2,
            )
        else:
            imgui.text_colored(
                "Not recording", 0.6, 0.6, 0.6,
            )

        imgui.end()

    def _draw_checklist_item(
        self, label: str, endpoint_name: str,
    ) -> None:
        """Draw a single hardware checklist row."""
        import imgui

        if self._comms is not None:
            status = self._comms.status
            connected = status.get(endpoint_name, False)
        else:
            connected = False

        if connected:
            imgui.text_colored(
                f"  [x] {label}", 0.2, 0.9, 0.2,
            )
        else:
            imgui.text_colored(
                f"  [ ] {label}", 0.5, 0.5, 0.5,
            )
