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
    from virtual_reality.config.schema import VirtualRealityConfig

logger = logging.getLogger(__name__)

# Stimulus options with display names and module paths
STIMULUS_TYPES = [
    ("Fly 3D (GLB)", "fly_3d", "virtual_reality.stimulus.fly_3d"),
    ("Fly 2D (Sprite)", "fly_sprite", "virtual_reality.stimulus.fly_sprite"),
    ("Warp Circle (Calibration)", "warp_circle", "virtual_reality.stimulus.warp_circle"),
]


class StimulusPanel:
    """Panel for stimulus selection and configuration.

    Args:
        config: Application configuration (mutable).
    """

    def __init__(self, config: VirtualRealityConfig) -> None:
        self._config = config
        self._selected_idx = 0
        self._running = False
        self._process: subprocess.Popen | None = None
        self._status_msg = ""

    def draw(self) -> None:
        """Render the stimulus panel contents."""
        import imgui

        imgui.begin("Stimulus Control")

        # Stimulus selection
        imgui.text("Stimulus Type:")
        for i, (label, _key, _mod) in enumerate(STIMULUS_TYPES):
            if imgui.radio_button(label, self._selected_idx == i):
                self._selected_idx = i
        imgui.separator()

        # Key parameters
        cfg = self._config
        imgui.text("Arena & Fly:")

        changed, val = imgui.input_float(
            "Arena Radius (mm)", cfg.arena.radius_mm, 1.0, 5.0,
        )
        if changed:
            cfg.arena.radius_mm = max(1.0, val)

        changed, val = imgui.input_float(
            "Fly Size (mm)", cfg.fly_model.phys_length_mm,
            0.1, 0.5,
        )
        if changed:
            cfg.fly_model.phys_length_mm = max(0.1, val)

        imgui.separator()
        imgui.text("Camera:")

        changed, val = imgui.input_float(
            "FOV X (deg)", cfg.camera.fov_x_deg, 5.0, 10.0,
        )
        if changed:
            cfg.camera.fov_x_deg = max(10.0, min(359.0, val))

        proj_modes = ["perspective", "equirect", "equidistant"]
        current = (
            proj_modes.index(cfg.camera.projection)
            if cfg.camera.projection in proj_modes
            else 0
        )
        changed, new_idx = imgui.combo(
            "Projection", current, proj_modes,
        )
        if changed:
            cfg.camera.projection = proj_modes[new_idx]

        imgui.separator()
        imgui.text("Movement:")

        changed, val = imgui.checkbox(
            "Autonomous Mode", cfg.autonomous.enabled,
        )
        if changed:
            cfg.autonomous.enabled = val

        changed, val = imgui.input_float(
            "Speed (mm/s)", cfg.movement.speed_mm_s, 1.0, 5.0,
        )
        if changed:
            cfg.movement.speed_mm_s = max(0.0, val)

        imgui.separator()
        imgui.text("Collision:")

        changed, val = imgui.slider_float(
            "Near-Plane Safety",
            cfg.scaling.near_plane_safety,
            0.1, 3.0, "%.2f",
        )
        if changed:
            cfg.scaling.near_plane_safety = val

        changed, val = imgui.checkbox(
            "Auto Min Distance",
            cfg.scaling.auto_min_distance,
        )
        if changed:
            cfg.scaling.auto_min_distance = val

        if not cfg.scaling.auto_min_distance:
            changed, val = imgui.input_float(
                "Min Distance (mm)",
                cfg.scaling.min_cam_fly_dist_mm, 0.5, 1.0,
            )
            if changed:
                cfg.scaling.min_cam_fly_dist_mm = max(0.1, val)

        imgui.separator()

        # Check if subprocess is still running
        if self._process is not None:
            ret = self._process.poll()
            if ret is not None:
                self._running = False
                if ret == 0:
                    self._status_msg = "Stimulus exited normally."
                else:
                    self._status_msg = f"Stimulus exited with code {ret}."
                self._process = None

        # Launch / Stop button
        if not self._running:
            if imgui.button("Launch Stimulus"):
                self._launch_stimulus()
        else:
            if imgui.button("Stop Stimulus"):
                self._stop_stimulus()
            imgui.same_line()
            imgui.text_colored("Running...", 0.4, 1.0, 0.4)

        if self._status_msg:
            imgui.text(self._status_msg)

        imgui.end()

    def _launch_stimulus(self) -> None:
        """Launch the selected stimulus as a subprocess."""
        _, key, module = STIMULUS_TYPES[self._selected_idx]
        logger.info("Launching stimulus: %s", key)

        # Save current config to a temp YAML file
        try:
            from virtual_reality.config.loader import save_config

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

        # Set PYTHONPATH so the subprocess finds virtual_reality
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
            self._status_msg = f"Launched {key} (PID {self._process.pid})"
            logger.info(
                "Stimulus subprocess started: PID %d", self._process.pid,
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
