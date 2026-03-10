"""Main DearPyGui application — single-window tabbed layout.

Provides a unified GUI with a top bar (experiment mode selector,
hardware status indicators), workflow tabs that adapt to the selected
experiment mode, and a status bar.

Requires ``dearpygui>=2.0``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flocroscope.gui.layout import (
    ExperimentMode,
    HARDWARE_SECTIONS,
    Tab,
    TAB_VISIBILITY,
)

if TYPE_CHECKING:
    from flocroscope.comms.hub import CommsHub
    from flocroscope.config.schema import FlocroscopeConfig

logger = logging.getLogger(__name__)

# Hardware indicator abbreviations shown in the top bar.
_HW_INDICATORS = [
    ("FT", "fictrac"),
    ("SI", "scanimage"),
    ("LED", "led"),
    ("PRES", "presenter"),
]

# Map Tab enum → DPG tag for the tab widget.
_TAB_TAGS: dict[Tab, str] = {
    Tab.SESSION: "tab_session",
    Tab.STIMULUS: "tab_stimulus",
    Tab.HARDWARE: "tab_hardware",
    Tab.CALIBRATION: "tab_calibration",
    Tab.SETTINGS: "tab_settings",
}


class FlocroscopeApp:
    """Main GUI application.

    Single primary window with experiment-mode-aware tabs.
    All panels degrade gracefully when their backing subsystem
    (comms, session, etc.) is not configured.

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
        self._experiment_mode = ExperimentMode.BEHAVIOR

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
        dpg.create_viewport(
            title="Flocroscope", width=1280, height=720,
            decorated=True,
        )

        # Apply dark theme
        from flocroscope.gui.theme import create_theme
        theme_id = create_theme()
        dpg.bind_theme(theme_id)

        # Start comms if configured
        if self._config.comms.enabled:
            try:
                from flocroscope.comms.hub import CommsHub
                self._comms = CommsHub(self._config.comms)
                self._comms.start_all()
                logger.info("CommsHub started from GUI")
            except Exception as exc:
                logger.warning(
                    "Failed to start comms: %s", exc,
                )
                self._comms = None

        # Create Flomington client if configured
        flomington_client = None
        try:
            from flocroscope.comms.flomington import (
                FlomingtonClient,
                FlomingtonConfig,
            )
            flom_cfg = getattr(
                self._config, "flomington",
                FlomingtonConfig(),
            )
            if flom_cfg.enabled:
                flomington_client = FlomingtonClient(flom_cfg)
                flomington_client.connect()
        except Exception as exc:
            logger.warning(
                "Failed to create Flomington client: %s", exc,
            )

        # Create panels
        self._create_panels(flomington_client)

        # Build primary window
        self._build_primary_window(dpg)

        # Viewport resize handler
        with dpg.item_handler_registry(
            tag="viewport_resize_handler",
        ):
            pass  # DPG has no direct resize callback

        logger.info("GUI started")

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        self._running = True

        try:
            while (
                dpg.is_dearpygui_running() and self._running
            ):
                self._update_tab_visibility(dpg)
                self._update_hw_indicators(dpg)
                self._update_status_bar(dpg)
                self._update_content_height(dpg)
                self._update_visible_panels(dpg)
                dpg.render_dearpygui_frame()
        finally:
            if self._comms is not None:
                self._comms.stop_all()
            dpg.destroy_context()
            logger.info("GUI closed")

    # ------------------------------------------------------------------ #
    #  Panel creation
    # ------------------------------------------------------------------ #

    def _create_panels(
        self, flomington_client: object | None,
    ) -> None:
        """Instantiate all panels."""
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
        self._tracking_panel = TrackingPanel(
            comms=self._comms,
            arena_radius_mm=self._config.arena.radius_mm,
        )

    # ------------------------------------------------------------------ #
    #  Primary window
    # ------------------------------------------------------------------ #

    def _build_primary_window(self, dpg: object) -> None:
        """Build the single primary window with all UI elements."""
        import dearpygui.dearpygui as dpg

        with dpg.window(tag="primary_window"):
            # -- Top bar --
            self._build_top_bar(dpg)
            dpg.add_separator(tag="top_sep")

            # -- Tab content area (scrollable) --
            with dpg.child_window(
                tag="tab_content_area",
                border=False,
                autosize_x=True,
            ):
                with dpg.tab_bar(tag="main_tab_bar"):
                    self._build_session_tab(dpg)
                    self._build_stimulus_tab(dpg)
                    self._build_hardware_tab(dpg)
                    self._build_calibration_tab(dpg)
                    self._build_settings_tab(dpg)

            # -- Status bar --
            dpg.add_separator(tag="status_sep")
            self._build_status_bar(dpg)

    def _build_top_bar(self, dpg: object) -> None:
        """Build the top bar with title, mode selector, and HW dots."""
        import dearpygui.dearpygui as dpg
        from flocroscope.gui.theme import ACCENT, STATUS_OFF

        with dpg.group(horizontal=True, tag="top_bar"):
            dpg.add_text(
                "FLOCROSCOPE", color=ACCENT,
            )
            dpg.add_spacer(width=20)

            dpg.add_combo(
                items=[m.value for m in ExperimentMode],
                tag="top_exp_mode",
                default_value=self._experiment_mode.value,
                width=140,
                callback=self._on_experiment_mode,
            )

            dpg.add_spacer(width=40)

            # Hardware status indicators
            for abbrev, ep_name in _HW_INDICATORS:
                dpg.add_text(
                    abbrev,
                    tag=f"top_hw_{ep_name}",
                    color=STATUS_OFF,
                )
                dpg.add_spacer(width=8)

            dpg.add_spacer()  # flexible spacer

            dpg.add_button(
                label="Quit",
                tag="top_quit_btn",
                callback=self._on_quit,
            )

    def _build_session_tab(self, dpg: object) -> None:
        """Build the Session tab (SessionPanel + FlomingtonPanel)."""
        import dearpygui.dearpygui as dpg

        with dpg.tab(
            label="Session", tag="tab_session",
        ):
            with dpg.child_window(
                autosize_x=True, autosize_y=True,
                border=False,
            ):
                self._session_panel.build(
                    parent=dpg.last_container(),
                )
                dpg.add_spacer(
                    height=16,
                    parent=dpg.last_container(),
                )
                dpg.add_separator(
                    parent=dpg.last_container(),
                )
                dpg.add_spacer(
                    height=8,
                    parent=dpg.last_container(),
                )
                self._flomington_panel.build(
                    parent=dpg.last_container(),
                )

    def _build_stimulus_tab(self, dpg: object) -> None:
        """Build the Stimulus tab."""
        import dearpygui.dearpygui as dpg

        with dpg.tab(
            label="Stimulus", tag="tab_stimulus",
        ):
            with dpg.child_window(
                autosize_x=True, autosize_y=True,
                border=False,
            ):
                self._stimulus_panel.build(
                    parent=dpg.last_container(),
                )

    def _build_hardware_tab(self, dpg: object) -> None:
        """Build the Hardware tab with collapsing sections."""
        import dearpygui.dearpygui as dpg

        # Map section names → (panel, tag)
        self._hw_sections: dict[str, tuple[object, str]] = {}

        with dpg.tab(
            label="Hardware", tag="tab_hardware",
        ):
            with dpg.child_window(
                autosize_x=True, autosize_y=True,
                border=False,
            ):
                container = dpg.last_container()

                # FicTrac / Treadmill
                with dpg.collapsing_header(
                    label="FicTrac / Treadmill",
                    tag="hw_sec_fictrac",
                    parent=container,
                    default_open=True,
                ):
                    self._fictrac_panel.build(
                        parent=dpg.last_container(),
                    )
                self._hw_sections["FicTrac / Treadmill"] = (
                    self._fictrac_panel, "hw_sec_fictrac",
                )

                # Tracking
                with dpg.collapsing_header(
                    label="Tracking",
                    tag="hw_sec_tracking",
                    parent=container,
                    default_open=True,
                ):
                    self._tracking_panel.build(
                        parent=dpg.last_container(),
                    )
                self._hw_sections["Tracking"] = (
                    self._tracking_panel, "hw_sec_tracking",
                )

                # ScanImage / 2-Photon
                with dpg.collapsing_header(
                    label="ScanImage / 2-Photon",
                    tag="hw_sec_scanimage",
                    parent=container,
                    default_open=True,
                ):
                    self._scanimage_panel.build(
                        parent=dpg.last_container(),
                    )
                self._hw_sections["ScanImage / 2-Photon"] = (
                    self._scanimage_panel, "hw_sec_scanimage",
                )

                # Optogenetics / LED
                with dpg.collapsing_header(
                    label="Optogenetics / LED",
                    tag="hw_sec_optogenetics",
                    parent=container,
                    default_open=True,
                ):
                    self._optogenetics_panel.build(
                        parent=dpg.last_container(),
                    )
                self._hw_sections["Optogenetics / LED"] = (
                    self._optogenetics_panel, "hw_sec_optogenetics",
                )

                # Communications (collapsed by default)
                with dpg.collapsing_header(
                    label="Communications",
                    tag="hw_sec_comms",
                    parent=container,
                    default_open=False,
                ):
                    self._comms_panel.build(
                        parent=dpg.last_container(),
                    )
                self._hw_sections["Communications"] = (
                    self._comms_panel, "hw_sec_comms",
                )

    def _build_calibration_tab(self, dpg: object) -> None:
        """Build the Calibration tab."""
        import dearpygui.dearpygui as dpg

        with dpg.tab(
            label="Calibration", tag="tab_calibration",
        ):
            with dpg.child_window(
                autosize_x=True, autosize_y=True,
                border=False,
            ):
                self._calibration_panel.build(
                    parent=dpg.last_container(),
                )
                dpg.add_spacer(
                    height=16,
                    parent=dpg.last_container(),
                )
                dpg.add_separator(
                    parent=dpg.last_container(),
                )
                dpg.add_spacer(
                    height=8,
                    parent=dpg.last_container(),
                )
                self._mapping_panel.build(
                    parent=dpg.last_container(),
                )

    def _build_settings_tab(self, dpg: object) -> None:
        """Build the Settings tab."""
        import dearpygui.dearpygui as dpg

        with dpg.tab(
            label="Settings", tag="tab_settings",
        ):
            with dpg.child_window(
                autosize_x=True, autosize_y=True,
                border=False,
            ):
                self._config_panel.build(
                    parent=dpg.last_container(),
                )

    def _build_status_bar(self, dpg: object) -> None:
        """Build the bottom status bar."""
        import dearpygui.dearpygui as dpg
        from flocroscope.gui.theme import (
            STATUS_OFF, TEXT_SECONDARY,
        )

        with dpg.group(horizontal=True, tag="status_bar"):
            dpg.add_text(
                "IDLE", tag="sb_recording",
                color=STATUS_OFF,
            )
            dpg.add_text(
                "  |  ", color=TEXT_SECONDARY,
            )
            dpg.add_text(
                "No active session", tag="sb_session",
                color=TEXT_SECONDARY,
            )
            dpg.add_text(
                "  |  ", color=TEXT_SECONDARY,
            )
            dpg.add_text(
                "Comms: disabled", tag="sb_comms",
                color=TEXT_SECONDARY,
            )

    # ------------------------------------------------------------------ #
    #  Per-frame updates
    # ------------------------------------------------------------------ #

    def _update_tab_visibility(self, dpg: object) -> None:
        """Show/hide tabs based on the current experiment mode."""
        import dearpygui.dearpygui as dpg

        visible = TAB_VISIBILITY[self._experiment_mode]
        for tab, tag in _TAB_TAGS.items():
            dpg.configure_item(tag, show=(tab in visible))

        # Show/hide hardware collapsing sections
        if hasattr(self, "_hw_sections"):
            for section_name, (_, tag) in (
                self._hw_sections.items()
            ):
                modes = HARDWARE_SECTIONS.get(
                    section_name, set(),
                )
                dpg.configure_item(
                    tag,
                    show=(self._experiment_mode in modes),
                )

    def _update_hw_indicators(self, dpg: object) -> None:
        """Update top-bar hardware dots."""
        import dearpygui.dearpygui as dpg
        from flocroscope.gui.theme import STATUS_OK, STATUS_OFF

        for _, ep_name in _HW_INDICATORS:
            tag = f"top_hw_{ep_name}"
            if self._comms is not None:
                status = self._comms.status
                connected = status.get(ep_name, False)
            else:
                connected = False

            dpg.configure_item(
                tag,
                color=STATUS_OK if connected else STATUS_OFF,
            )

    def _update_status_bar(self, dpg: object) -> None:
        """Update the bottom status bar."""
        import dearpygui.dearpygui as dpg
        from flocroscope.gui.theme import (
            STATUS_ERR, STATUS_OK, STATUS_OFF,
            TEXT_SECONDARY,
        )

        # Recording state (from session panel)
        session = getattr(
            self._session_panel, "_session", None,
        )
        if session is not None and session.is_running:
            dpg.set_value("sb_recording", "REC")
            dpg.configure_item(
                "sb_recording", color=STATUS_ERR,
            )
            summary = session.summary()
            dpg.set_value(
                "sb_session",
                f"Session: {summary['session_id']}  "
                f"Trials: {summary['trial_count']}",
            )
            dpg.configure_item(
                "sb_session", color=STATUS_OK,
            )
        elif session is not None:
            dpg.set_value("sb_recording", "IDLE")
            dpg.configure_item(
                "sb_recording", color=STATUS_OFF,
            )
            dpg.set_value(
                "sb_session",
                f"Last: {session.trial_count} trials",
            )
            dpg.configure_item(
                "sb_session", color=TEXT_SECONDARY,
            )
        else:
            dpg.set_value("sb_recording", "IDLE")
            dpg.configure_item(
                "sb_recording", color=STATUS_OFF,
            )
            dpg.set_value("sb_session", "No active session")
            dpg.configure_item(
                "sb_session", color=TEXT_SECONDARY,
            )

        # Comms
        if self._comms is not None:
            n_connected = sum(
                1 for v in self._comms.status.values() if v
            )
            n_total = len(self._comms.status)
            dpg.set_value(
                "sb_comms",
                f"Comms: {n_connected}/{n_total}",
            )
            color = (
                STATUS_OK if n_connected > 0
                else TEXT_SECONDARY
            )
            dpg.configure_item("sb_comms", color=color)
        else:
            enabled = self._config.comms.enabled
            dpg.set_value(
                "sb_comms",
                "Comms: disabled"
                if not enabled else "Comms: not started",
            )
            dpg.configure_item(
                "sb_comms", color=TEXT_SECONDARY,
            )

    def _update_content_height(self, dpg: object) -> None:
        """Adjust tab content area height to fill viewport."""
        import dearpygui.dearpygui as dpg

        vh = dpg.get_viewport_height()
        # Top bar ~40px + status bar ~30px + separators ~8px
        # + padding ~16px = ~94px overhead
        content_h = max(100, vh - 94)
        dpg.configure_item(
            "tab_content_area", height=content_h,
        )

    def _update_visible_panels(self, dpg: object) -> None:
        """Call update() on panels whose tabs are visible."""
        import dearpygui.dearpygui as dpg

        visible = TAB_VISIBILITY[self._experiment_mode]

        if Tab.SESSION in visible:
            self._session_panel.update()
            self._flomington_panel.update()

        if Tab.STIMULUS in visible:
            self._stimulus_panel.update()

        if Tab.HARDWARE in visible:
            mode = self._experiment_mode
            for section_name, (panel, _) in (
                self._hw_sections.items()
            ):
                modes = HARDWARE_SECTIONS.get(
                    section_name, set(),
                )
                if mode in modes:
                    panel.update()

        if Tab.CALIBRATION in visible:
            self._calibration_panel.update()
            self._mapping_panel.update()

        if Tab.SETTINGS in visible:
            self._config_panel.update()

    # ------------------------------------------------------------------ #
    #  Callbacks
    # ------------------------------------------------------------------ #

    def _on_experiment_mode(
        self, sender, app_data, user_data,
    ) -> None:
        """Handle experiment mode change."""
        try:
            self._experiment_mode = ExperimentMode(app_data)
            logger.info(
                "Experiment mode changed to %s",
                self._experiment_mode.value,
            )
        except ValueError:
            logger.warning(
                "Unknown experiment mode: %s", app_data,
            )

    def _on_quit(
        self, sender=None, app_data=None, user_data=None,
    ) -> None:
        """Handle quit button."""
        self._running = False


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
