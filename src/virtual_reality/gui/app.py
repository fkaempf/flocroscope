"""Main Dear ImGui application window.

Provides a unified GUI that integrates stimulus control, session
management, configuration editing, calibration, mapping, and
communications into a single application with a menu bar and
dockable panels.

Requires ``imgui[pygame]>=2.0``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.comms.hub import CommsHub
    from virtual_reality.config.schema import VirtualRealityConfig

logger = logging.getLogger(__name__)


class VirtualRealityApp:
    """Main GUI application.

    Manages the pygame/OpenGL window, Dear ImGui context, and
    panel layout.  All panels degrade gracefully when their
    backing subsystem (comms, session, etc.) is not configured.

    Args:
        config: Optional configuration.  If provided, enables
            live parameter editing and comms integration.
    """

    def __init__(
        self, config: VirtualRealityConfig | None = None,
    ) -> None:
        self._running = False
        if config is None:
            from virtual_reality.config.schema import (
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
            import imgui
            from imgui.integrations.pygame import PygameRenderer
        except ImportError:
            print(
                "Dear ImGui not installed. Install with:\n"
                "  pip install 'imgui[pygame]>=2.0'"
            )
            return

        import pygame
        from OpenGL import GL

        pygame.init()
        size = (1280, 720)
        screen = pygame.display.set_mode(
            size,
            pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE,
        )
        pygame.display.set_caption("Virtual Reality")

        imgui.create_context()
        io = imgui.get_io()
        io.display_size = float(size[0]), float(size[1])
        renderer = PygameRenderer()
        self._running = True
        clock = pygame.time.Clock()

        # Start comms if configured
        if self._config.comms.enabled:
            try:
                from virtual_reality.comms.hub import CommsHub
                self._comms = CommsHub(self._config.comms)
                self._comms.start_all()
                logger.info("CommsHub started from GUI")
            except Exception as exc:
                logger.warning("Failed to start comms: %s", exc)
                self._comms = None

        # Create panels
        from virtual_reality.gui.panels.stimulus import (
            StimulusPanel,
        )
        from virtual_reality.gui.panels.session import (
            SessionPanel,
        )
        from virtual_reality.gui.panels.config_editor import (
            ConfigEditorPanel,
        )
        from virtual_reality.gui.panels.comms import CommsPanel
        from virtual_reality.gui.panels.calibration import (
            CalibrationPanel,
        )
        from virtual_reality.gui.panels.mapping import MappingPanel
        from virtual_reality.gui.panels.flomington import (
            FlomingtonPanel,
        )
        from virtual_reality.gui.panels.fictrac import FicTracPanel
        from virtual_reality.gui.panels.scanimage import (
            ScanImagePanel,
        )
        from virtual_reality.gui.panels.optogenetics import (
            OptogeneticsPanel,
        )
        from virtual_reality.gui.panels.behaviour import (
            BehaviourPanel,
        )
        from virtual_reality.gui.panels.tracking import (
            TrackingPanel,
        )

        # Create Flomington client if configured
        flomington_client = None
        try:
            from virtual_reality.comms.flomington import (
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

        logger.info("GUI started")

        try:
            while self._running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    renderer.process_event(event)

                renderer.process_inputs()
                imgui.new_frame()

                self._draw_menu_bar()
                self._draw_panels()

                GL.glClearColor(0.1, 0.1, 0.1, 1.0)
                GL.glClear(GL.GL_COLOR_BUFFER_BIT)

                imgui.render()
                renderer.render(imgui.get_draw_data())
                pygame.display.flip()
                clock.tick(60)
        finally:
            if self._comms is not None:
                self._comms.stop_all()
            renderer.shutdown()
            pygame.quit()
            logger.info("GUI closed")

    def _draw_menu_bar(self) -> None:
        """Draw the main menu bar."""
        import imgui

        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File"):
                clicked, _ = imgui.menu_item("Quit", "Ctrl+Q")
                if clicked:
                    self._running = False
                imgui.end_menu()
            if imgui.begin_menu("Panels"):
                clicked, _ = imgui.menu_item("Reorganize")
                if clicked:
                    self._needs_reorganize = True
                imgui.separator()
                _, self._show_stimulus = imgui.menu_item(
                    "Stimulus", None, self._show_stimulus,
                )
                _, self._show_session = imgui.menu_item(
                    "Session", None, self._show_session,
                )
                _, self._show_config = imgui.menu_item(
                    "Configuration", None, self._show_config,
                )
                _, self._show_comms = imgui.menu_item(
                    "Communications", None, self._show_comms,
                )
                _, self._show_calibration = imgui.menu_item(
                    "Calibration", None, self._show_calibration,
                )
                _, self._show_mapping = imgui.menu_item(
                    "Mapping", None, self._show_mapping,
                )
                _, self._show_flomington = imgui.menu_item(
                    "Flomington", None, self._show_flomington,
                )
                imgui.separator()
                _, self._show_fictrac = imgui.menu_item(
                    "FicTrac / Treadmill", None,
                    self._show_fictrac,
                )
                _, self._show_scanimage = imgui.menu_item(
                    "ScanImage / 2-Photon", None,
                    self._show_scanimage,
                )
                _, self._show_optogenetics = imgui.menu_item(
                    "Optogenetics / LED", None,
                    self._show_optogenetics,
                )
                _, self._show_behaviour = imgui.menu_item(
                    "Behaviour", None, self._show_behaviour,
                )
                _, self._show_tracking = imgui.menu_item(
                    "Tracking (Virtual vs Real)", None,
                    self._show_tracking,
                )
                imgui.end_menu()
            imgui.end_main_menu_bar()

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

    def _draw_panels(self) -> None:
        """Draw all visible panels in a tiled grid layout."""
        import imgui

        panels = self._get_visible_panels()
        dw, dh = imgui.get_io().display_size
        layout = self._compute_layout(len(panels), dw, dh)

        for panel, (x, y, w, h) in zip(panels, layout):
            if self._needs_reorganize:
                imgui.set_next_window_position(x, y, imgui.ALWAYS)
                imgui.set_next_window_size(w, h, imgui.ALWAYS)
            # Keep every panel unfolded
            imgui.set_next_window_collapsed(False, imgui.ALWAYS)
            panel.draw()

        self._needs_reorganize = False

def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the GUI CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch the Virtual Reality GUI application.",
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

    from virtual_reality.logging_config import setup_logging

    parser = _build_parser()
    args = parser.parse_args()

    setup_logging(level=args.log_level)

    config = None
    if args.config is not None:
        from virtual_reality.config.loader import load_config
        config = load_config(args.config)

    app = VirtualRealityApp(config=config)
    app.run()


if __name__ == "__main__":
    main()
