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
        self.group_tag = "grp_flomington"

    @property
    def window_tag(self) -> str:
        return self.group_tag

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

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(
            parent=parent, tag=self.group_tag,
        ):
            # Connection status
            dpg.add_text("Flomington Integration")
            dpg.add_separator()
            dpg.add_text(
                "Not configured", tag="flom_not_configured",
                color=(153, 153, 153),
            )
            dpg.add_text(
                "Set flomington.enabled = true in config",
                tag="flom_hint",
            )

            with dpg.group(
                tag="flom_configured", show=False,
            ):
                with dpg.group(horizontal=True):
                    dpg.add_text(
                        "", tag="flom_enabled_status",
                    )
                    dpg.add_text(" | ")
                    dpg.add_text(
                        "", tag="flom_conn_status",
                    )
                dpg.add_button(
                    label="Connect", tag="flom_connect_btn",
                    callback=self._on_connect,
                )

            dpg.add_spacer(height=4)
            dpg.add_separator()

            # Lookup controls
            dpg.add_text("Lookup:")
            dpg.add_radio_button(
                items=["Stock", "Cross"],
                tag="flom_lookup_type",
                default_value="Stock",
                horizontal=True,
                callback=self._on_lookup_type,
            )
            dpg.add_input_text(
                label="ID", tag="flom_lookup_id",
                callback=self._on_lookup_id,
            )
            dpg.add_button(
                label="Look Up",
                callback=self._on_lookup,
            )

            dpg.add_spacer(height=4)
            dpg.add_separator()

            # Stock info
            with dpg.group(
                tag="flom_stock_info", show=False,
            ):
                dpg.add_text("Stock Info:")
                dpg.add_separator()
                dpg.add_text("", tag="flom_stock_name")
                dpg.add_text("", tag="flom_stock_genotype")
                dpg.add_text("", tag="flom_stock_source")
                dpg.add_text("", tag="flom_stock_tags")
                dpg.add_text(
                    "", tag="flom_stock_notes", wrap=400,
                )

            # Cross info
            with dpg.group(
                tag="flom_cross_info", show=False,
            ):
                dpg.add_text("Cross Info:")
                dpg.add_separator()
                dpg.add_text("", tag="flom_cross_id")
                dpg.add_text("", tag="flom_cross_virgin")
                dpg.add_text("", tag="flom_cross_male")
                dpg.add_text("", tag="flom_cross_status")
                dpg.add_text("", tag="flom_cross_exp")
                dpg.add_text(
                    "", tag="flom_cross_notes", wrap=400,
                )

            # Link button
            dpg.add_spacer(height=4)
            dpg.add_button(
                label="Link to Session",
                tag="flom_link_btn",
                callback=self._on_link,
                show=False,
            )

            # Status
            dpg.add_separator()
            dpg.add_text(
                "", tag="flom_status", wrap=400,
            )

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        if self._client is None:
            dpg.show_item("flom_not_configured")
            dpg.show_item("flom_hint")
            dpg.hide_item("flom_configured")
        else:
            dpg.hide_item("flom_not_configured")
            dpg.hide_item("flom_hint")
            dpg.show_item("flom_configured")

            enabled = self._client._config.enabled
            connected = self._client.connected

            if enabled:
                dpg.set_value(
                    "flom_enabled_status", "Enabled",
                )
                dpg.configure_item(
                    "flom_enabled_status",
                    color=(51, 230, 51),
                )
            else:
                dpg.set_value(
                    "flom_enabled_status", "Disabled",
                )
                dpg.configure_item(
                    "flom_enabled_status",
                    color=(230, 77, 77),
                )

            if connected:
                dpg.set_value(
                    "flom_conn_status", "Connected",
                )
                dpg.configure_item(
                    "flom_conn_status",
                    color=(51, 230, 51),
                )
                dpg.hide_item("flom_connect_btn")
            else:
                dpg.set_value(
                    "flom_conn_status", "Disconnected",
                )
                dpg.configure_item(
                    "flom_conn_status",
                    color=(230, 77, 77),
                )
                dpg.show_item("flom_connect_btn")

        # Stock/cross display
        if self._stock is not None:
            dpg.show_item("flom_stock_info")
            dpg.hide_item("flom_cross_info")
            dpg.show_item("flom_link_btn")

            stock = self._stock
            dpg.set_value(
                "flom_stock_name",
                f"  Name: {stock.name or '(unnamed)'}",
            )
            dpg.set_value(
                "flom_stock_genotype",
                f"  Genotype: "
                f"{stock.genotype or '(unknown)'}",
            )
            dpg.set_value(
                "flom_stock_source",
                f"  Source: {stock.source or '(unknown)'}",
            )
            tags = (
                ", ".join(stock.genetic_tags)
                if stock.genetic_tags else "(none)"
            )
            dpg.set_value(
                "flom_stock_tags", f"  Tags: {tags}",
            )
            dpg.set_value(
                "flom_stock_notes",
                f"Notes: {stock.notes}" if stock.notes
                else "",
            )
        elif self._cross is not None:
            dpg.hide_item("flom_stock_info")
            dpg.show_item("flom_cross_info")
            dpg.show_item("flom_link_btn")

            cross = self._cross
            dpg.set_value(
                "flom_cross_id",
                f"  Cross ID: {cross.cross_id}",
            )
            dpg.set_value(
                "flom_cross_virgin",
                f"  Virgin: "
                f"{cross.virgin_parent or '(unknown)'} "
                f"({cross.virgin_genotype or '?'})",
            )
            dpg.set_value(
                "flom_cross_male",
                f"  Male: "
                f"{cross.male_parent or '(unknown)'} "
                f"({cross.male_genotype or '?'})",
            )
            dpg.set_value(
                "flom_cross_status",
                f"  Status: {cross.status}",
            )
            dpg.set_value(
                "flom_cross_exp",
                f"  Experiment: {cross.experiment_type}"
                if cross.experiment_type else "",
            )
            dpg.set_value(
                "flom_cross_notes",
                f"Notes: {cross.notes}" if cross.notes
                else "",
            )
        else:
            dpg.hide_item("flom_stock_info")
            dpg.hide_item("flom_cross_info")
            dpg.hide_item("flom_link_btn")

        dpg.set_value("flom_status", self._status_msg)

    # -- callbacks --

    def _on_connect(self, sender, app_data, user_data):
        if self._client is None:
            return
        ok = self._client.connect()
        if ok:
            self._status_msg = "Connected to Flomington"
        else:
            self._status_msg = (
                "Connection failed (not yet implemented)"
            )

    def _on_lookup_type(
        self, sender, app_data, user_data,
    ):
        self._lookup_type = (
            0 if app_data == "Stock" else 1
        )

    def _on_lookup_id(self, sender, app_data, user_data):
        self._lookup_id = app_data

    def _on_lookup(self, sender, app_data, user_data):
        self._do_lookup()

    def _on_link(self, sender, app_data, user_data):
        self._link_to_session()

    def _do_lookup(self) -> None:
        """Perform a stock or cross lookup."""
        lookup_id = self._lookup_id
        if not lookup_id or not lookup_id.strip():
            self._status_msg = (
                "Enter a stock or cross ID to look up."
            )
            return

        if self._client is None:
            self._status_msg = (
                "Flomington client not configured."
            )
            return

        lookup_id = lookup_id.strip()

        if self._lookup_type == 0:
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
            self._stock = None
            self._cross = self._client.get_cross(
                lookup_id,
            )
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

    def _link_to_session(self) -> None:
        """Placeholder for linking to session."""
        if self._stock is not None:
            self._status_msg = (
                f"Link requested: stock "
                f"'{self._stock.name}' "
                "(session linking not yet implemented)"
            )
            logger.info(
                "Flomington link requested: stock=%s",
                self._stock.stock_id,
            )
        elif self._cross is not None:
            self._status_msg = (
                f"Link requested: cross "
                f"'{self._cross.cross_id}' "
                "(session linking not yet implemented)"
            )
            logger.info(
                "Flomington link requested: cross=%s",
                self._cross.cross_id,
            )
        else:
            self._status_msg = "No record to link."
