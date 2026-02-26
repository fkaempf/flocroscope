"""Session management panel.

Provides GUI controls for starting/stopping experimental sessions,
managing trials, and viewing session status.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.config.schema import VirtualRealityConfig
    from virtual_reality.session.session import Session

logger = logging.getLogger(__name__)


class SessionPanel:
    """Panel for experiment session management.

    Args:
        config: Application configuration.
    """

    def __init__(self, config: VirtualRealityConfig) -> None:
        self._config = config
        self._session: Session | None = None
        self._experimenter = ""
        self._fly_genotype = ""
        self._fly_id = ""
        self._notes = ""
        self._status_msg = ""

    def draw(self) -> None:
        """Render the session panel."""
        import imgui

        imgui.begin("Session")

        if self._session is None or not self._session.is_running:
            self._draw_setup()
        else:
            self._draw_active()

        if self._status_msg:
            imgui.separator()
            imgui.text(self._status_msg)

        imgui.end()

    def _draw_setup(self) -> None:
        """Draw session setup form."""
        import imgui

        imgui.text("New Session")
        imgui.separator()

        _, self._experimenter = imgui.input_text(
            "Experimenter", self._experimenter, 64,
        )
        _, self._fly_genotype = imgui.input_text(
            "Fly Genotype", self._fly_genotype, 256,
        )
        _, self._fly_id = imgui.input_text(
            "Fly/Cross ID", self._fly_id, 32,
        )
        _, self._notes = imgui.input_text_multiline(
            "Notes", self._notes, 512, 200, 60,
        )

        imgui.separator()
        if imgui.button("Start Session"):
            self._start_session()

        if self._session is not None:
            imgui.same_line()
            imgui.text(
                f"Last session: {self._session.trial_count} trials",
            )

    def _draw_active(self) -> None:
        """Draw active session controls."""
        import imgui

        session = self._session
        assert session is not None

        summary = session.summary()

        imgui.text(f"Session: {summary['session_id']}")
        imgui.text(
            f"Trials: {summary['trial_count']}  "
            f"Duration: {summary['total_duration_s']:.1f}s",
        )

        if summary["current_trial"] is not None:
            imgui.text_colored(
                f"Trial {summary['current_trial']} active",
                0.2, 0.9, 0.2,
            )
        else:
            imgui.text("No trial active")

        imgui.separator()

        # Trial controls
        if session.current_trial is None:
            if imgui.button("Begin Trial"):
                session.begin_trial(metadata={
                    "genotype": self._fly_genotype,
                    "fly_id": self._fly_id,
                })
                self._status_msg = (
                    f"Trial {session.current_trial.trial_number} "
                    f"started"
                )
        else:
            if imgui.button("End Trial"):
                trial = session.end_trial()
                if trial:
                    self._status_msg = (
                        f"Trial {trial.trial_number} ended "
                        f"({trial.duration_s:.1f}s)"
                    )

        imgui.separator()

        # Session controls
        if imgui.button("Save Session"):
            path = session.save()
            self._status_msg = f"Saved to {path}"

        imgui.same_line()
        if imgui.button("Stop Session"):
            session.stop()
            path = session.save()
            self._status_msg = (
                f"Session stopped, saved to {path}"
            )

    def _start_session(self) -> None:
        """Create and start a new session."""
        from virtual_reality.session.session import Session

        self._session = Session(
            config=self._config,
            experimenter=self._experimenter,
            stimulus_type="gui",
        )
        self._session.metadata.fly_genotype = self._fly_genotype
        if self._fly_id:
            self._session.metadata.fly_stock_id = self._fly_id
        self._session.metadata.notes = self._notes
        self._session.start()
        self._status_msg = (
            f"Session {self._session.session_id} started"
        )
        logger.info("Session started from GUI")
