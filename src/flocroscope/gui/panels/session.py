"""Session management panel.

Provides GUI controls for starting/stopping experimental sessions,
managing trials, and viewing session status.  Optionally integrates
with Flomington for auto-populating fly metadata from stock/cross
records.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.flomington import FlomingtonClient
    from flocroscope.config.schema import FlocroscopeConfig
    from flocroscope.session.session import Session

logger = logging.getLogger(__name__)


class SessionPanel:
    """Panel for experiment session management.

    Args:
        config: Application configuration.
        flomington_client: Optional Flomington client for stock/cross
            lookups. When ``None``, the Flomington integration section
            is hidden and the panel works exactly as before.
    """

    def __init__(
        self,
        config: FlocroscopeConfig,
        flomington_client: FlomingtonClient | None = None,
    ) -> None:
        self._config = config
        self._flomington = flomington_client
        self._session: Session | None = None
        self._experimenter = ""
        self._fly_genotype = ""
        self._fly_id = ""
        self._notes = ""
        self._status_msg = ""
        self._flomington_lookup_done = False

    @property
    def flomington_client(self) -> FlomingtonClient | None:
        """The Flomington client, if configured."""
        return self._flomington

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
        changed, self._fly_id = imgui.input_text(
            "Fly/Cross ID", self._fly_id, 32,
        )
        if changed:
            # Reset the lookup flag when the ID changes
            self._flomington_lookup_done = False

        _, self._notes = imgui.input_text_multiline(
            "Notes", self._notes, 512, 200, 60,
        )

        # --- Flomington integration ---
        self._draw_flomington_section()

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

    def _draw_flomington_section(self) -> None:
        """Draw the Flomington integration section in setup form.

        Shows connection status and a lookup button.  When
        Flomington is not configured (``None``), this section is
        hidden entirely so the panel works as before.
        """
        import imgui

        if self._flomington is None:
            return

        imgui.spacing()
        imgui.text("Flomington:")

        connected = self._flomington.connected
        if connected:
            imgui.same_line()
            imgui.text_colored("Connected", 0.2, 0.9, 0.2)
        else:
            imgui.same_line()
            imgui.text_colored("Disconnected", 0.9, 0.3, 0.3)

        # Auto-lookup button
        if self._fly_id.strip() and not self._flomington_lookup_done:
            if imgui.button("Lookup from Flomington"):
                self._lookup_from_flomington()

        if self._flomington_lookup_done:
            imgui.text_colored(
                "Genotype populated from Flomington",
                0.5, 0.8, 0.5,
            )

    def _lookup_from_flomington(self) -> None:
        """Look up fly/cross info from Flomington and populate fields.

        Tries a stock lookup first, then a cross lookup.  If found,
        the genotype field is auto-populated.
        """
        if self._flomington is None or not self._fly_id.strip():
            return

        fly_id = self._fly_id.strip()

        # Try stock lookup first
        stock = self._flomington.get_stock(fly_id)
        if stock is not None and stock.genotype:
            self._fly_genotype = stock.genotype
            self._flomington_lookup_done = True
            self._status_msg = (
                f"Populated genotype from stock: {stock.name}"
            )
            logger.info(
                "Flomington stock lookup for session: %s -> %s",
                fly_id, stock.genotype,
            )
            return

        # Try cross lookup
        cross = self._flomington.get_cross(fly_id)
        if cross is not None:
            # Build genotype from parent genotypes
            parts = []
            if cross.virgin_genotype:
                parts.append(cross.virgin_genotype)
            if cross.male_genotype:
                parts.append(cross.male_genotype)
            if parts:
                self._fly_genotype = " x ".join(parts)
                self._flomington_lookup_done = True
                self._status_msg = (
                    f"Populated genotype from cross: "
                    f"{cross.cross_id} ({cross.status})"
                )
                logger.info(
                    "Flomington cross lookup for session: %s -> %s",
                    fly_id, self._fly_genotype,
                )
                return

        self._status_msg = (
            f"ID '{fly_id}' not found in Flomington"
        )

    def _start_session(self) -> None:
        """Create and start a new session."""
        from flocroscope.session.session import Session

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
