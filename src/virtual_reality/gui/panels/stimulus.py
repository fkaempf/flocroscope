"""Stimulus control panel.

Provides controls for selecting, configuring, and launching
stimulus types from the GUI.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.config.schema import VirtualRealityConfig

logger = logging.getLogger(__name__)

# Stimulus options with display names
STIMULUS_TYPES = [
    ("Fly 3D (GLB)", "fly_3d"),
    ("Fly 2D (Sprite)", "fly_sprite"),
    ("Warp Circle (Calibration)", "warp_circle"),
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

    def draw(self) -> None:
        """Render the stimulus panel contents."""
        import imgui

        imgui.begin("Stimulus Control")

        # Stimulus selection
        imgui.text("Stimulus Type:")
        for i, (label, _key) in enumerate(STIMULUS_TYPES):
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

        # Launch button
        if not self._running:
            if imgui.button("Launch Stimulus (CLI)"):
                _, key = STIMULUS_TYPES[self._selected_idx]
                logger.info("Launch requested: %s", key)
                imgui.text("Use CLI: vr-fly3d / vr-fly2d")
        else:
            imgui.text("Stimulus running...")

        imgui.end()
