"""Configuration editor panel.

Provides YAML config loading, editing, and saving from the GUI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.config.schema import FlocroscopeConfig

logger = logging.getLogger(__name__)


class ConfigEditorPanel:
    """Panel for loading and saving YAML configuration.

    Args:
        config: Application configuration (mutable reference).
    """

    def __init__(self, config: FlocroscopeConfig) -> None:
        self._config = config
        self._config_path = ""
        self._status_msg = ""
        self.group_tag = "grp_config"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(parent=parent, tag=self.group_tag):
            dpg.add_input_text(
                label="Config YAML",
                tag="cfg_path",
                callback=self._on_path_change,
            )

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Load",
                    callback=self._on_load,
                )
                dpg.add_button(
                    label="Save",
                    callback=self._on_save,
                )
                dpg.add_button(
                    label="Reset Defaults",
                    callback=self._on_reset,
                )

            dpg.add_text("", tag="cfg_status")
            dpg.add_separator()

            dpg.add_text("Current Configuration:")
            dpg.add_text("", tag="cfg_arena")
            dpg.add_text("", tag="cfg_camera")
            dpg.add_text("", tag="cfg_fly")
            dpg.add_text("", tag="cfg_movement")
            dpg.add_text("", tag="cfg_comms")
            dpg.add_text("", tag="cfg_display")

    def update(self) -> None:
        """Push live config summary each frame."""
        import dearpygui.dearpygui as dpg

        cfg = self._config
        dpg.set_value("cfg_status", self._status_msg)
        dpg.set_value(
            "cfg_arena",
            f"  Arena: {cfg.arena.radius_mm:.1f} mm radius",
        )
        dpg.set_value(
            "cfg_camera",
            f"  Camera: {cfg.camera.projection} "
            f"FOV={cfg.camera.fov_x_deg:.0f}deg",
        )
        dpg.set_value(
            "cfg_fly",
            f"  Fly: {cfg.fly_model.phys_length_mm:.1f} mm",
        )
        mode = (
            "autonomous" if cfg.autonomous.enabled
            else "keyboard"
        )
        dpg.set_value(
            "cfg_movement",
            f"  Movement: {mode} "
            f"{cfg.movement.speed_mm_s:.0f} mm/s",
        )
        dpg.set_value(
            "cfg_comms",
            f"  Comms: "
            f"{'enabled' if cfg.comms.enabled else 'disabled'}",
        )
        wm = (
            "borderless" if cfg.display.borderless
            else "windowed"
        )
        dpg.set_value(
            "cfg_display",
            f"  Display: {cfg.display.target_fps} FPS {wm}",
        )

    # -- callbacks --

    def _on_path_change(self, sender, app_data, user_data):
        self._config_path = app_data

    def _on_load(self, sender, app_data, user_data):
        self._load_config()

    def _on_save(self, sender, app_data, user_data):
        self._save_config()

    def _on_reset(self, sender, app_data, user_data):
        self._reset_defaults()

    def _load_config(self) -> None:
        """Load config from the specified YAML file."""
        path = self._config_path
        if not path:
            self._status_msg = "No path specified"
            return
        try:
            from flocroscope.config.loader import load_config
            loaded = load_config(path)
            import dataclasses
            for f in dataclasses.fields(loaded):
                setattr(
                    self._config, f.name,
                    getattr(loaded, f.name),
                )
            self._status_msg = f"Loaded: {path}"
            logger.info("Config loaded from %s", path)
        except Exception as exc:
            self._status_msg = f"Error: {exc}"
            logger.warning("Config load failed: %s", exc)

    def _save_config(self) -> None:
        """Save current config to the specified YAML file."""
        path = self._config_path
        if not path:
            self._status_msg = "No path specified"
            return
        try:
            from flocroscope.config.loader import save_config
            save_config(self._config, path)
            self._status_msg = f"Saved: {path}"
            logger.info("Config saved to %s", path)
        except Exception as exc:
            self._status_msg = f"Error: {exc}"
            logger.warning("Config save failed: %s", exc)

    def _reset_defaults(self) -> None:
        """Reset config to default values."""
        from flocroscope.config.schema import FlocroscopeConfig
        import dataclasses
        defaults = FlocroscopeConfig()
        for f in dataclasses.fields(defaults):
            setattr(
                self._config, f.name,
                getattr(defaults, f.name),
            )
        self._status_msg = "Reset to defaults"
        logger.info("Config reset to defaults")
