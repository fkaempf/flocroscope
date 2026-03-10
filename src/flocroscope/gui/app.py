"""Main DearPyGui application window.

Provides a unified GUI that integrates stimulus control, session
management, configuration editing, calibration, mapping, and
communications into a single application with a menu bar and
dockable panels.

Requires ``dearpygui>=2.0``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import FlocroscopeConfig

logger = logging.getLogger(__name__)


class FlocroscopeApp:
    """Main GUI application.

    Manages the DearPyGui viewport, docking layout, and panel
    lifecycle.  All panels degrade gracefully when their backing
    subsystem (comms, session, etc.) is not configured.

    Args:
        config: Optional configuration.  If provided, enables
            live parameter editing and comms integration.
    """

    def __init__(
        self, config: FlocroscopeConfig | None = None,
    ) -> None:
        self._running = False
        if config is None:
            from flocroscope.config.schema import (
                _resolve_default_paths,
            )
            config = _resolve_default_paths()
        self._config = config
        self._comms: CommsHub | None = None

        # Panel visibility flags
        self._show_stimulus = True
        self._show_session = True
        self._show_config = True
        self._show_comms = True
        self._show_calibration = False
        self._show_mapping = False
        self._show_flomington = False
        self._show_fictrac = False
        self._show_scanimage = False
        self._show_optogenetics = False
        self._show_behaviour = False
        self._show_tracking = False

        # Layout: tile panels on first frame
        self._needs_reorganize = True

    def run(self) -> None:
        """Launch the GUI main loop."""
        try:
            import dearpygui.dearpygui as dpg
        except ImportError:
            print(
                "DearPyGui not installed. Install with:\n"
                "  pip install 'dearpygui>=2.0'"
            )
            return

        dpg.create_context()
        dpg.configure_app(docking=True, docking_space=True)
        dpg.create_viewport(
            title="Flocroscope", width=1280, height=720,
        )

        # Start comms if configured
        if self._config.comms.enabled:
            try:
                from flocroscope.comms.hub import CommsHub
                self._comms = CommsHub(self._config.comms)
                self._comms.start_all()
                logger.info("CommsHub started from GUI")
            except Exception as exc:
                logger.warning("Failed to start comms: %s", exc)
                self._comms = None

        # Create Flomington client if configured
        flomington_client = None
        try:
            from flocroscope.comms.flomington import (
                FlomingtonClient,
                FlomingtonConfig,
            )
            flom_cfg = getattr(
                self._config, "flomington", FlomingtonConfig(),
            )
            if flom_cfg.enabled:
                flomington_client = FlomingtonClient(flom_cfg)
                flomington_client.connect()
        except Exception as exc:
            logger.warning(
                "Failed to create Flomington client: %s", exc,
            )

        # Create panels (deferred imports)
        from flocroscope.gui.panels.stimulus import (
            StimulusPanel,
        )
        from flocroscope.gui.panels.session import (
            SessionPanel,
        )
        from flocroscope.gui.panels.config_editor import (
            ConfigEditorPanel,
        )
        from flocroscope.gui.panels.comms import CommsPanel
        from flocroscope.gui.panels.calibration import (
            CalibrationPanel,
        )
        from flocroscope.gui.panels.mapping import MappingPanel
        from flocroscope.gui.panels.flomington import (
            FlomingtonPanel,
        )
        from flocroscope.gui.panels.fictrac import FicTracPanel
        from flocroscope.gui.panels.scanimage import (
            ScanImagePanel,
        )
        from flocroscope.gui.panels.optogenetics import (
            OptogeneticsPanel,
        )
        from flocroscope.gui.panels.behaviour import (
            BehaviourPanel,
        )
        from flocroscope.gui.panels.tracking import (
            TrackingPanel,
        )

        self._stimulus_panel = StimulusPanel(self._config)
        self._session_panel = SessionPanel(
            self._config,
            flomington_client=flomington_client,
        )
        self._config_panel = ConfigEditorPanel(self._config)
        self._comms_panel = CommsPanel(self._comms)
        self._calibration_panel = CalibrationPanel(
            self._config.calibration,
        )
        self._mapping_panel = MappingPanel(self._config.warp)
        self._flomington_panel = FlomingtonPanel(
            client=flomington_client,
        )
        self._fictrac_panel = FicTracPanel(
            comms=self._comms,
            config=self._config.comms,
        )
        self._scanimage_panel = ScanImagePanel(
            comms=self._comms,
        )
        self._optogenetics_panel = OptogeneticsPanel(
            comms=self._comms,
        )
        self._behaviour_panel = BehaviourPanel(
            config=self._config,
            comms=self._comms,
        )
        self._tracking_panel = TrackingPanel(
            comms=self._comms,
            arena_radius_mm=self._config.arena.radius_mm,
        )

        # Build all panel windows
        self._panels = [
            ("_show_stimulus", self._stimulus_panel),
            ("_show_session", self._session_panel),
            ("_show_config", self._config_panel),
            ("_show_comms", self._comms_panel),
            ("_show_calibration", self._calibration_panel),
            ("_show_mapping", self._mapping_panel),
            ("_show_flomington", self._flomington_panel),
            ("_show_fictrac", self._fictrac_panel),
            ("_show_scanimage", self._scanimage_panel),
            ("_show_optogenetics", self._optogenetics_panel),
            ("_show_behaviour", self._behaviour_panel),
            ("_show_tracking", self._tracking_panel),
        ]

        # Build menu bar
        self._build_menu_bar(dpg)

        # Build all panel widgets
        for _, panel in self._panels:
            panel.build()

        logger.info("GUI started")

        dpg.setup_dearpygui()
        dpg.show_viewport()
        self._running = True

        try:
            while dpg.is_dearpygui_running() and self._running:
                # Update panel visibility
                for flag_name, panel in self._panels:
                    visible = getattr(self, flag_name)
                    if visible:
                        dpg.show_item(panel.window_tag)
                    else:
                        dpg.hide_item(panel.window_tag)

                # Update panels with live data
                for flag_name, panel in self._panels:
                    if getattr(self, flag_name):
                        panel.update()

                dpg.render_dearpygui_frame()
        finally:
            if self._comms is not None:
                self._comms.stop_all()
            dpg.destroy_context()
            logger.info("GUI closed")

    def _build_menu_bar(self, dpg: object) -> None:
        """Build the viewport menu bar."""
        import dearpygui.dearpygui as dpg

        with dpg.viewport_menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(
                    label="Quit",
                    shortcut="Ctrl+Q",
                    callback=lambda: setattr(
                        self, "_running", False,
                    ),
                )
            with dpg.menu(label="Panels"):
                dpg.add_menu_item(
                    label="Reorganize",
                    callback=self._on_reorganize,
                )
                dpg.add_separator()
                self._add_panel_toggle(
                    dpg, "Stimulus", "_show_stimulus",
                )
                self._add_panel_toggle(
                    dpg, "Session", "_show_session",
                )
                self._add_panel_toggle(
                    dpg, "Configuration", "_show_config",
                )
                self._add_panel_toggle(
                    dpg, "Communications", "_show_comms",
                )
                self._add_panel_toggle(
                    dpg, "Calibration", "_show_calibration",
                )
                self._add_panel_toggle(
                    dpg, "Mapping", "_show_mapping",
                )
                self._add_panel_toggle(
                    dpg, "Flomington", "_show_flomington",
                )
                dpg.add_separator()
                self._add_panel_toggle(
                    dpg, "FicTrac / Treadmill",
                    "_show_fictrac",
                )
                self._add_panel_toggle(
                    dpg, "ScanImage / 2-Photon",
                    "_show_scanimage",
                )
                self._add_panel_toggle(
                    dpg, "Optogenetics / LED",
                    "_show_optogenetics",
                )
                self._add_panel_toggle(
                    dpg, "Behaviour", "_show_behaviour",
                )
                self._add_panel_toggle(
                    dpg, "Tracking (Virtual vs Real)",
                    "_show_tracking",
                )

    def _add_panel_toggle(
        self, dpg: object, label: str, flag_name: str,
    ) -> None:
        """Add a checkable menu item for a panel toggle."""
        import dearpygui.dearpygui as dpg

        tag = f"menu_{flag_name}"
        dpg.add_menu_item(
            label=label,
            check=True,
            default_value=getattr(self, flag_name),
            tag=tag,
            callback=lambda s, a, u: setattr(
                self, u, dpg.get_value(s),
            ),
            user_data=flag_name,
        )

    def _on_reorganize(self) -> None:
        """Reset docking layout by showing all visible panels."""
        self._needs_reorganize = True

    def _get_visible_panels(self) -> list:
        """Return visible panel instances in display order."""
        panels = []
        if self._show_stimulus:
            panels.append(self._stimulus_panel)
        if self._show_session:
            panels.append(self._session_panel)
        if self._show_config:
            panels.append(self._config_panel)
        if self._show_comms:
            panels.append(self._comms_panel)
        if self._show_calibration:
            panels.append(self._calibration_panel)
        if self._show_mapping:
            panels.append(self._mapping_panel)
        if self._show_flomington:
            panels.append(self._flomington_panel)
        if self._show_fictrac:
            panels.append(self._fictrac_panel)
        if self._show_scanimage:
            panels.append(self._scanimage_panel)
        if self._show_optogenetics:
            panels.append(self._optogenetics_panel)
        if self._show_behaviour:
            panels.append(self._behaviour_panel)
        if self._show_tracking:
            panels.append(self._tracking_panel)
        return panels

    @staticmethod
    def _compute_layout(
        n: int, display_w: float, display_h: float,
    ) -> list[tuple[float, float, float, float]]:
        """Compute ``(x, y, w, h)`` for *n* panels in a tiled grid."""
        if n == 0:
            return []

        menu_h = 20.0
        avail_h = display_h - menu_h
        pad = 2.0

        if n == 1:
            cols = 1
        elif n <= 4:
            cols = 2
        elif n <= 9:
            cols = 3
        else:
            cols = 4

        rows = -(-n // cols)  # ceil division
        cell_w = display_w / cols
        cell_h = avail_h / rows

        positions: list[tuple[float, float, float, float]] = []
        for i in range(n):
            c = i % cols
            r = i // cols
            positions.append((
                c * cell_w + pad,
                menu_h + r * cell_h + pad,
                cell_w - 2 * pad,
                cell_h - 2 * pad,
            ))
        return positions


def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the GUI CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch the Flocroscope GUI application.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to a YAML configuration file.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO).",
    )
    return parser


def main() -> None:
    """CLI entry point for the GUI."""
    import argparse

    from flocroscope.logging_config import setup_logging

    parser = _build_parser()
    args = parser.parse_args()

    setup_logging(level=args.log_level)

    config = None
    if args.config is not None:
        from flocroscope.config.loader import load_config
        config = load_config(args.config)

    app = FlocroscopeApp(config=config)
    app.run()


if __name__ == "__main__":
    main()
