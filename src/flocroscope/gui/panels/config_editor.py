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
            dpg.add_text("Configuration")
            dpg.add_separator()

            dpg.add_input_text(
                label="Config YAML",
                tag="cfg_path",
                width=300,
                callback=self._on_path_change,
            )

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Load",
                    callback=self._on_load,
                    width=80,
                )
                dpg.add_button(
                    label="Save",
                    callback=self._on_save,
                    width=80,
                )
                dpg.add_button(
                    label="Reset Defaults",
                    callback=self._on_reset,
                    width=120,
                )

            dpg.add_text("", tag="cfg_status")
            dpg.add_separator()

            # -- Per-section collapsing headers --
            with dpg.collapsing_header(
                label="Arena", default_open=True,
            ):
                dpg.add_input_float(
                    label="Radius (mm)",
                    tag="cfg_arena_radius",
                    width=150,
                    default_value=self._config.arena.radius_mm,
                    callback=self._on_arena_radius,
                )

            with dpg.collapsing_header(
                label="Camera", default_open=True,
            ):
                dpg.add_combo(
                    items=[
                        "equidistant", "equisolid",
                        "stereographic", "rectilinear",
                    ],
                    label="Projection",
                    tag="cfg_cam_proj",
                    width=150,
                    default_value=self._config.camera.projection,
                    callback=self._on_cam_proj,
                )
                dpg.add_input_float(
                    label="FOV X (deg)",
                    tag="cfg_cam_fov",
                    width=150,
                    default_value=self._config.camera.fov_x_deg,
                    callback=self._on_cam_fov,
                )

            with dpg.collapsing_header(
                label="Fly Model", default_open=False,
            ):
                dpg.add_input_float(
                    label="Length (mm)",
                    tag="cfg_fly_len",
                    width=150,
                    default_value=(
                        self._config.fly_model.phys_length_mm
                    ),
                    callback=self._on_fly_len,
                )

            with dpg.collapsing_header(
                label="Movement", default_open=False,
            ):
                dpg.add_input_float(
                    label="Speed (mm/s)",
                    tag="cfg_mov_speed",
                    width=150,
                    default_value=(
                        self._config.movement.speed_mm_s
                    ),
                    callback=self._on_mov_speed,
                )
                dpg.add_checkbox(
                    label="Autonomous",
                    tag="cfg_mov_auto",
                    default_value=(
                        self._config.autonomous.enabled
                    ),
                    callback=self._on_mov_auto,
                )

            with dpg.collapsing_header(
                label="Communications", default_open=False,
            ):
                dpg.add_checkbox(
                    label="Enabled",
                    tag="cfg_comms_en",
                    default_value=self._config.comms.enabled,
                    callback=self._on_comms_en,
                )
                dpg.add_text("", tag="cfg_comms_summary")

            with dpg.collapsing_header(
                label="Display", default_open=False,
            ):
                dpg.add_input_int(
                    label="Target FPS",
                    tag="cfg_disp_fps",
                    width=100,
                    default_value=(
                        self._config.display.target_fps
                    ),
                    callback=self._on_disp_fps,
                )
                dpg.add_checkbox(
                    label="Borderless",
                    tag="cfg_disp_border",
                    default_value=(
                        self._config.display.borderless
                    ),
                    callback=self._on_disp_border,
                )

    def update(self) -> None:
        """Push live config summary each frame."""
        import dearpygui.dearpygui as dpg

        dpg.set_value("cfg_status", self._status_msg)
        comms = self._config.comms
        ports = []
        if comms.fictrac_port > 0:
            ports.append(f"FT:{comms.fictrac_port}")
        if comms.scanimage_port > 0:
            ports.append(f"SI:{comms.scanimage_port}")
        if comms.led_port > 0:
            ports.append(f"LED:{comms.led_port}")
        dpg.set_value(
            "cfg_comms_summary",
            "  " + (", ".join(ports) if ports else "No ports"),
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

    def _on_arena_radius(self, sender, app_data, user_data):
        self._config.arena.radius_mm = app_data

    def _on_cam_proj(self, sender, app_data, user_data):
        self._config.camera.projection = app_data

    def _on_cam_fov(self, sender, app_data, user_data):
        self._config.camera.fov_x_deg = app_data

    def _on_fly_len(self, sender, app_data, user_data):
        self._config.fly_model.phys_length_mm = app_data

    def _on_mov_speed(self, sender, app_data, user_data):
        self._config.movement.speed_mm_s = app_data

    def _on_mov_auto(self, sender, app_data, user_data):
        self._config.autonomous.enabled = app_data

    def _on_comms_en(self, sender, app_data, user_data):
        self._config.comms.enabled = app_data

    def _on_disp_fps(self, sender, app_data, user_data):
        self._config.display.target_fps = app_data

    def _on_disp_border(self, sender, app_data, user_data):
        self._config.display.borderless = app_data

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
            self._sync_widgets_to_config()
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
        self._sync_widgets_to_config()

    def _sync_widgets_to_config(self) -> None:
        """Push current config values to all editor widgets."""
        try:
            import dearpygui.dearpygui as dpg
            cfg = self._config
            dpg.set_value(
                "cfg_arena_radius", cfg.arena.radius_mm,
            )
            dpg.set_value(
                "cfg_cam_proj", cfg.camera.projection,
            )
            dpg.set_value(
                "cfg_cam_fov", cfg.camera.fov_x_deg,
            )
            dpg.set_value(
                "cfg_fly_len", cfg.fly_model.phys_length_mm,
            )
            dpg.set_value(
                "cfg_mov_speed", cfg.movement.speed_mm_s,
            )
            dpg.set_value(
                "cfg_mov_auto", cfg.autonomous.enabled,
            )
            dpg.set_value(
                "cfg_comms_en", cfg.comms.enabled,
            )
            dpg.set_value(
                "cfg_disp_fps", cfg.display.target_fps,
            )
            dpg.set_value(
                "cfg_disp_border", cfg.display.borderless,
            )
        except Exception:
            pass
