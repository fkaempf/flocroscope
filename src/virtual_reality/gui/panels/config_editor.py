"""Configuration editor panel.

Provides YAML config loading, editing, and saving from the GUI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.config.schema import VirtualRealityConfig

logger = logging.getLogger(__name__)


class ConfigEditorPanel:
    """Panel for loading and saving YAML configuration.

    Args:
        config: Application configuration (mutable reference).
    """

    def __init__(self, config: VirtualRealityConfig) -> None:
        self._config = config
        self._config_path = ""
        self._status_msg = ""

    def draw(self) -> None:
        """Render the config editor panel."""
        import imgui

        imgui.begin("Configuration")

        # File path input
        changed, self._config_path = imgui.input_text(
            "Config YAML", self._config_path, 256,
        )

        if imgui.button("Load"):
            self._load_config()
        imgui.same_line()
        if imgui.button("Save"):
            self._save_config()
        imgui.same_line()
        if imgui.button("Reset Defaults"):
            self._reset_defaults()

        if self._status_msg:
            imgui.text(self._status_msg)

        imgui.separator()

        # Display current config summary
        cfg = self._config
        imgui.text("Current Configuration:")
        imgui.bullet_text(
            f"Arena: {cfg.arena.radius_mm:.1f} mm radius",
        )
        imgui.bullet_text(
            f"Camera: {cfg.camera.projection} "
            f"FOV={cfg.camera.fov_x_deg:.0f}deg",
        )
        imgui.bullet_text(
            f"Fly: {cfg.fly_model.phys_length_mm:.1f} mm",
        )
        imgui.bullet_text(
            f"Movement: {'autonomous' if cfg.autonomous.enabled else 'keyboard'} "
            f"{cfg.movement.speed_mm_s:.0f} mm/s",
        )
        imgui.bullet_text(
            f"Comms: {'enabled' if cfg.comms.enabled else 'disabled'}",
        )
        imgui.bullet_text(
            f"Display: {cfg.display.target_fps} FPS "
            f"{'borderless' if cfg.display.borderless else 'windowed'}",
        )

        imgui.end()

    def _load_config(self) -> None:
        """Load config from the specified YAML file."""
        if not self._config_path:
            self._status_msg = "No path specified"
            return
        try:
            from virtual_reality.config.loader import load_config
            loaded = load_config(self._config_path)
            # Copy all fields from loaded config
            import dataclasses
            for f in dataclasses.fields(loaded):
                setattr(self._config, f.name, getattr(loaded, f.name))
            self._status_msg = f"Loaded: {self._config_path}"
            logger.info("Config loaded from %s", self._config_path)
        except Exception as exc:
            self._status_msg = f"Error: {exc}"
            logger.warning("Config load failed: %s", exc)

    def _save_config(self) -> None:
        """Save current config to the specified YAML file."""
        if not self._config_path:
            self._status_msg = "No path specified"
            return
        try:
            from virtual_reality.config.loader import save_config
            save_config(self._config, self._config_path)
            self._status_msg = f"Saved: {self._config_path}"
            logger.info("Config saved to %s", self._config_path)
        except Exception as exc:
            self._status_msg = f"Error: {exc}"
            logger.warning("Config save failed: %s", exc)

    def _reset_defaults(self) -> None:
        """Reset config to default values."""
        from virtual_reality.config.schema import VirtualRealityConfig
        import dataclasses
        defaults = VirtualRealityConfig()
        for f in dataclasses.fields(defaults):
            setattr(self._config, f.name, getattr(defaults, f.name))
        self._status_msg = "Reset to defaults"
        logger.info("Config reset to defaults")
