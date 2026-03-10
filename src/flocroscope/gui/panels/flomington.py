"""Flomington stock management integration panel.

Provides GUI controls for connecting to the Flomington Drosophila
stock management system, looking up stocks and crosses by ID, and
linking experimental sessions to specific fly records.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.flomington import (
        FlomingtonClient,
        FlyCross,
        FlyStock,
    )

logger = logging.getLogger(__name__)


class FlomingtonPanel:
    """Panel for Flomington stock management integration.

    Shows connection status, provides stock/cross ID lookup, displays
    retrieved record information, and offers a placeholder button to
    link records to the current experimental session.

    All functionality uses :class:`~flocroscope.comms.flomington.FlomingtonClient`,
    which returns defaults when not connected, so the panel gracefully
    shows a "Not connected" state without errors.

    Args:
        client: Optional FlomingtonClient instance.  If ``None``,
            the panel shows a disconnected state.
    """

    def __init__(
        self, client: FlomingtonClient | None = None,
    ) -> None:
        self._client = client
        self._lookup_id = ""
        self._lookup_type = 0  # 0 = stock, 1 = cross
        self._status_msg = ""
        self._stock: FlyStock | None = None
        self._cross: FlyCross | None = None

    @property
    def client(self) -> FlomingtonClient | None:
        """The current FlomingtonClient."""
        return self._client

    @client.setter
    def client(self, value: FlomingtonClient | None) -> None:
        self._client = value

    @property
    def stock(self) -> FlyStock | None:
        """The last looked-up stock record."""
        return self._stock

    @property
    def cross(self) -> FlyCross | None:
        """The last looked-up cross record."""
        return self._cross

    def draw(self) -> None:
        """Render the Flomington panel."""
        import imgui

        imgui.begin("Flomington")

        # --- Connection status ---
        self._draw_connection_status()

        imgui.spacing()
        imgui.separator()

        # --- Lookup controls ---
        self._draw_lookup()

        imgui.spacing()
        imgui.separator()

        # --- Record display ---
        if self._stock is not None:
            self._draw_stock_info()
        elif self._cross is not None:
            self._draw_cross_info()

        # --- Link to session button ---
        imgui.spacing()
        if self._stock is not None or self._cross is not None:
            if imgui.button("Link to Session"):
                self._link_to_session()

        # --- Status area ---
        if self._status_msg:
            imgui.separator()
            imgui.text_wrapped(self._status_msg)

        imgui.end()

    def _draw_connection_status(self) -> None:
        """Draw the Flomington connection status section."""
        import imgui

        imgui.text("Flomington Integration")
        imgui.separator()

        if self._client is None:
            imgui.text_colored(
                "Not configured", 0.6, 0.6, 0.6,
            )
            imgui.text("Set flomington.enabled = true in config")
            return

        enabled = self._client._config.enabled
        connected = self._client.connected

        # Enabled/disabled
        if enabled:
            imgui.text_colored("Enabled", 0.2, 0.9, 0.2)
        else:
            imgui.text_colored("Disabled", 0.9, 0.3, 0.3)

        imgui.same_line()
        imgui.text(" | ")
        imgui.same_line()

        # Connected/disconnected
        if connected:
            imgui.text_colored("Connected", 0.2, 0.9, 0.2)
        else:
            imgui.text_colored("Disconnected", 0.9, 0.3, 0.3)

        if not connected:
            if imgui.button("Connect"):
                ok = self._client.connect()
                if ok:
                    self._status_msg = "Connected to Flomington"
                else:
                    self._status_msg = (
                        "Connection failed (not yet implemented)"
                    )

    def _draw_lookup(self) -> None:
        """Draw the stock/cross ID lookup controls."""
        import imgui

        imgui.text("Lookup:")

        # Lookup type radio buttons
        if imgui.radio_button("Stock", self._lookup_type == 0):
            self._lookup_type = 0
        imgui.same_line()
        if imgui.radio_button("Cross", self._lookup_type == 1):
            self._lookup_type = 1

        # ID input
        _, self._lookup_id = imgui.input_text(
            "ID", self._lookup_id, 64,
        )

        # Lookup button
        if imgui.button("Look Up"):
            self._do_lookup()

    def _do_lookup(self) -> None:
        """Perform a stock or cross lookup using the client."""
        if not self._lookup_id.strip():
            self._status_msg = "Enter a stock or cross ID to look up."
            return

        if self._client is None:
            self._status_msg = (
                "Flomington client not configured."
            )
            return

        lookup_id = self._lookup_id.strip()

        if self._lookup_type == 0:
            # Stock lookup
            self._cross = None
            self._stock = self._client.get_stock(lookup_id)
            if self._stock is None:
                self._status_msg = (
                    f"Stock '{lookup_id}' not found."
                )
            else:
                self._status_msg = (
                    f"Found stock: {self._stock.name}"
                )
                logger.info(
                    "Flomington stock lookup: %s -> %s",
                    lookup_id, self._stock.name,
                )
        else:
            # Cross lookup
            self._stock = None
            self._cross = self._client.get_cross(lookup_id)
            if self._cross is None:
                self._status_msg = (
                    f"Cross '{lookup_id}' not found."
                )
            else:
                self._status_msg = (
                    f"Found cross: {self._cross.cross_id} "
                    f"({self._cross.status})"
                )
                logger.info(
                    "Flomington cross lookup: %s -> %s",
                    lookup_id, self._cross.status,
                )

    def _draw_stock_info(self) -> None:
        """Draw stock record information."""
        import imgui

        stock = self._stock
        assert stock is not None

        imgui.text("Stock Info:")
        imgui.separator()

        imgui.bullet_text(f"Name: {stock.name or '(unnamed)'}")
        imgui.bullet_text(
            f"Genotype: {stock.genotype or '(unknown)'}",
        )
        imgui.bullet_text(
            f"Source: {stock.source or '(unknown)'}",
        )

        if stock.genetic_tags:
            imgui.bullet_text(
                f"Tags: {', '.join(stock.genetic_tags)}",
            )
        else:
            imgui.bullet_text("Tags: (none)")

        if stock.notes:
            imgui.text_wrapped(f"Notes: {stock.notes}")

    def _draw_cross_info(self) -> None:
        """Draw cross record information."""
        import imgui

        cross = self._cross
        assert cross is not None

        imgui.text("Cross Info:")
        imgui.separator()

        imgui.bullet_text(f"Cross ID: {cross.cross_id}")
        imgui.bullet_text(
            f"Virgin: {cross.virgin_parent or '(unknown)'} "
            f"({cross.virgin_genotype or '?'})",
        )
        imgui.bullet_text(
            f"Male: {cross.male_parent or '(unknown)'} "
            f"({cross.male_genotype or '?'})",
        )
        imgui.bullet_text(f"Status: {cross.status}")

        if cross.experiment_type:
            imgui.bullet_text(
                f"Experiment: {cross.experiment_type}",
            )

        if cross.notes:
            imgui.text_wrapped(f"Notes: {cross.notes}")

    def _link_to_session(self) -> None:
        """Placeholder for linking a record to the current session.

        In a full implementation this would call
        :meth:`FlomingtonClient.tag_session` to associate the
        looked-up stock or cross with the active session.
        """
        if self._stock is not None:
            self._status_msg = (
                f"Link requested: stock '{self._stock.name}' "
                "(session linking not yet implemented)"
            )
            logger.info(
                "Flomington link requested: stock=%s",
                self._stock.stock_id,
            )
        elif self._cross is not None:
            self._status_msg = (
                f"Link requested: cross '{self._cross.cross_id}' "
                "(session linking not yet implemented)"
            )
            logger.info(
                "Flomington link requested: cross=%s",
                self._cross.cross_id,
            )
        else:
            self._status_msg = "No record to link."
