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
                VirtualRealityConfig,
            )
            config = VirtualRealityConfig()
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
        pygame.display.set_mode(
            size,
            pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE,
        )
        pygame.display.set_caption("Virtual Reality")

        imgui.create_context()
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
                imgui.end_menu()
            imgui.end_main_menu_bar()

    def _draw_panels(self) -> None:
        """Draw all visible panels."""
        import imgui

        if self._show_stimulus:
            self._stimulus_panel.draw()
        if self._show_session:
            self._session_panel.draw()
        if self._show_config:
            self._config_panel.draw()
        if self._show_comms:
            self._comms_panel.draw()
        if self._show_calibration:
            self._calibration_panel.draw()
        if self._show_mapping:
            self._mapping_panel.draw()
        if self._show_flomington:
            self._flomington_panel.draw()

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
