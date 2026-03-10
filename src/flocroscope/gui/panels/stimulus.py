"""Stimulus control panel.

Provides controls for selecting, configuring, and launching
stimulus types from the GUI.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.config.schema import FlocroscopeConfig

logger = logging.getLogger(__name__)

# Stimulus options with display names and module paths
STIMULUS_TYPES = [
    ("Fly 3D (GLB)", "fly_3d", "flocroscope.stimulus.fly_3d"),
    ("Fly 2D (Sprite)", "fly_sprite", "flocroscope.stimulus.fly_sprite"),
    ("Warp Circle (Calibration)", "warp_circle", "flocroscope.stimulus.warp_circle"),
]


class StimulusPanel:
    """Panel for stimulus selection and configuration.

    Args:
        config: Application configuration (mutable).
    """

    def __init__(self, config: FlocroscopeConfig) -> None:
        self._config = config
        self._selected_idx = 0
        self._running = False
        self._process: subprocess.Popen | None = None
        self._status_msg = ""
        self.window_tag = "win_stimulus"

    def build(self) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.window(
            label="Stimulus Control",
            tag=self.window_tag,
        ):
            dpg.add_text("Stimulus Type:")
            dpg.add_radio_button(
                items=[t[0] for t in STIMULUS_TYPES],
                tag="stim_type",
                callback=self._on_type_change,
                default_value=STIMULUS_TYPES[0][0],
            )
            dpg.add_separator()

            dpg.add_text("Arena & Fly:")
            dpg.add_input_float(
                label="Arena Radius (mm)",
                tag="stim_arena_radius",
                default_value=self._config.arena.radius_mm,
                step=1.0,
                step_fast=5.0,
                callback=self._on_arena_radius,
            )
            dpg.add_input_float(
                label="Fly Size (mm)",
                tag="stim_fly_size",
                default_value=self._config.fly_model.phys_length_mm,
                step=0.1,
                step_fast=0.5,
                callback=self._on_fly_size,
            )

            dpg.add_separator()
            dpg.add_text("Camera:")
            dpg.add_input_float(
                label="FOV X (deg)",
                tag="stim_fov_x",
                default_value=self._config.camera.fov_x_deg,
                step=5.0,
                step_fast=10.0,
                callback=self._on_fov_x,
            )

            proj_modes = [
                "perspective", "equirect", "equidistant",
            ]
            dpg.add_combo(
                items=proj_modes,
                label="Projection",
                tag="stim_projection",
                default_value=self._config.camera.projection,
                callback=self._on_projection,
            )

            dpg.add_separator()
            dpg.add_text("Movement:")
            dpg.add_checkbox(
                label="Autonomous Mode",
                tag="stim_autonomous",
                default_value=self._config.autonomous.enabled,
                callback=self._on_autonomous,
            )
            dpg.add_input_float(
                label="Speed (mm/s)",
                tag="stim_speed",
                default_value=self._config.movement.speed_mm_s,
                step=1.0,
                step_fast=5.0,
                callback=self._on_speed,
            )

            dpg.add_separator()
            dpg.add_text("Collision:")
            dpg.add_slider_float(
                label="Near-Plane Safety",
                tag="stim_near_plane",
                default_value=(
                    self._config.scaling.near_plane_safety
                ),
                min_value=0.1,
                max_value=3.0,
                format="%.2f",
                callback=self._on_near_plane,
            )
            dpg.add_checkbox(
                label="Auto Min Distance",
                tag="stim_auto_min",
                default_value=(
                    self._config.scaling.auto_min_distance
                ),
                callback=self._on_auto_min,
            )
            dpg.add_input_float(
                label="Min Distance (mm)",
                tag="stim_min_dist",
                default_value=(
                    self._config.scaling.min_cam_fly_dist_mm
                ),
                step=0.5,
                step_fast=1.0,
                callback=self._on_min_dist,
            )

            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Launch Stimulus",
                    tag="stim_launch_btn",
                    callback=self._on_launch,
                )
                dpg.add_text(
                    "", tag="stim_running_text",
                    color=(102, 255, 102),
                )
            dpg.add_text("", tag="stim_status_text")

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        cfg = self._config

        # Show/hide min distance based on auto toggle
        if cfg.scaling.auto_min_distance:
            dpg.hide_item("stim_min_dist")
        else:
            dpg.show_item("stim_min_dist")

        # Poll subprocess
        if self._process is not None:
            ret = self._process.poll()
            if ret is not None:
                self._running = False
                if ret == 0:
                    self._status_msg = (
                        "Stimulus exited normally."
                    )
                else:
                    self._status_msg = (
                        f"Stimulus exited with code {ret}."
                    )
                self._process = None

        # Update button label and status
        if self._running:
            dpg.configure_item(
                "stim_launch_btn", label="Stop Stimulus",
            )
            dpg.set_value(
                "stim_running_text", "Running...",
            )
        else:
            dpg.configure_item(
                "stim_launch_btn", label="Launch Stimulus",
            )
            dpg.set_value("stim_running_text", "")

        dpg.set_value("stim_status_text", self._status_msg)

    # -- callbacks --

    def _on_type_change(self, sender, app_data, user_data):
        labels = [t[0] for t in STIMULUS_TYPES]
        if app_data in labels:
            self._selected_idx = labels.index(app_data)

    def _on_arena_radius(self, sender, app_data, user_data):
        self._config.arena.radius_mm = max(1.0, app_data)

    def _on_fly_size(self, sender, app_data, user_data):
        self._config.fly_model.phys_length_mm = max(
            0.1, app_data,
        )

    def _on_fov_x(self, sender, app_data, user_data):
        self._config.camera.fov_x_deg = max(
            10.0, min(359.0, app_data),
        )

    def _on_projection(self, sender, app_data, user_data):
        self._config.camera.projection = app_data

    def _on_autonomous(self, sender, app_data, user_data):
        self._config.autonomous.enabled = app_data

    def _on_speed(self, sender, app_data, user_data):
        self._config.movement.speed_mm_s = max(0.0, app_data)

    def _on_near_plane(self, sender, app_data, user_data):
        self._config.scaling.near_plane_safety = app_data

    def _on_auto_min(self, sender, app_data, user_data):
        self._config.scaling.auto_min_distance = app_data

    def _on_min_dist(self, sender, app_data, user_data):
        self._config.scaling.min_cam_fly_dist_mm = max(
            0.1, app_data,
        )

    def _on_launch(self, sender, app_data, user_data):
        if self._running:
            self._stop_stimulus()
        else:
            self._launch_stimulus()

    def _launch_stimulus(self) -> None:
        """Launch the selected stimulus as a subprocess."""
        _, key, module = STIMULUS_TYPES[self._selected_idx]
        logger.info("Launching stimulus: %s", key)

        # Save current config to a temp YAML file
        try:
            from flocroscope.config.loader import save_config

            tmp = Path(tempfile.mkdtemp()) / "vr_gui_config.yaml"
            save_config(self._config, tmp)
            config_path = str(tmp)
        except Exception as exc:
            logger.warning("Could not save temp config: %s", exc)
            config_path = None

        # Build command
        cmd = [sys.executable, "-m", module]
        if config_path:
            cmd.append(config_path)

        # Set PYTHONPATH so the subprocess finds flocroscope
        import os
        env = os.environ.copy()
        src_dir = str(Path(__file__).resolve().parents[3])
        existing = env.get("PYTHONPATH", "")
        if src_dir not in existing:
            env["PYTHONPATH"] = (
                src_dir + os.pathsep + existing if existing
                else src_dir
            )

        try:
            self._process = subprocess.Popen(cmd, env=env)
            self._running = True
            self._status_msg = (
                f"Launched {key} (PID {self._process.pid})"
            )
            logger.info(
                "Stimulus subprocess started: PID %d",
                self._process.pid,
            )
        except Exception as exc:
            self._status_msg = f"Failed to launch: {exc}"
            logger.error("Failed to launch stimulus: %s", exc)

    def _stop_stimulus(self) -> None:
        """Stop the running stimulus subprocess."""
        if self._process is not None:
            self._process.terminate()
            self._status_msg = "Stimulus terminated."
            logger.info("Stimulus subprocess terminated")
