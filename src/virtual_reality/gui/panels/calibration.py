"""Calibration pipeline panel.

Displays camera/projector calibration settings, file paths for
intrinsic parameters, and provides buttons for running the
calibration pipeline.  The actual calibration requires hardware
and is triggered as a placeholder action.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.config.schema import CalibrationConfig

logger = logging.getLogger(__name__)

# Fisheye intrinsic file names (K, D, xi)
_FISHEYE_FILES = ("fisheye.K.npy", "fisheye.D.npy", "fisheye.xi.npy")

# Pinhole intrinsic file names (K, D)
_PINHOLE_FILES = ("pinhole.K.npy", "pinhole.D.npy")


class CalibrationPanel:
    """Panel for camera calibration pipeline control and status.

    Shows the current calibration settings (camera type, projector
    resolution, mode, exposure), expected intrinsic file paths, and
    provides a placeholder button to run the calibration pipeline.

    Args:
        config: Calibration configuration (mutable).
    """

    def __init__(self, config: CalibrationConfig) -> None:
        self._config = config
        self._status_msg = ""
        self._last_rms: float | None = None

    def draw(self) -> None:
        """Render the calibration panel contents."""
        import imgui

        imgui.begin("Calibration")

        # --- Hardware settings ---
        imgui.text("Hardware Settings:")
        imgui.separator()

        imgui.bullet_text(
            f"Camera: {self._config.camera_type}",
        )
        imgui.bullet_text(
            f"Projector: {self._config.proj_w}"
            f"x{self._config.proj_h}",
        )
        imgui.bullet_text(
            f"Mode: {self._config.mode}",
        )
        imgui.bullet_text(
            f"Exposure: {self._config.exposure_ms} ms",
        )

        imgui.spacing()

        # --- Intrinsic file paths ---
        imgui.text("Intrinsic Files:")
        imgui.separator()

        if self._config.camera_type == "alvium":
            imgui.text("  Fisheye (omnidir):")
            for fname in _FISHEYE_FILES:
                imgui.bullet_text(fname)
        else:
            imgui.text("  Pinhole:")
            for fname in _PINHOLE_FILES:
                imgui.bullet_text(fname)

        imgui.spacing()

        # --- Run calibration button ---
        if imgui.button("Run Calibration"):
            self._run_calibration()

        # --- Status area ---
        imgui.separator()
        imgui.text("Status:")

        if self._status_msg:
            imgui.text_wrapped(self._status_msg)

        if self._last_rms is not None:
            imgui.text(f"Last RMS: {self._last_rms:.4f} px")

        imgui.end()

    def _run_calibration(self) -> None:
        """Placeholder for running the calibration pipeline.

        In a full implementation this would launch the camera
        capture and chessboard detection pipeline.  For now it
        sets a status message indicating the action.
        """
        self._status_msg = (
            f"Calibration requested for {self._config.camera_type} "
            f"camera ({self._config.mode} mode). "
            "Connect hardware and run from CLI."
        )
        logger.info(
            "Calibration run requested: camera=%s, mode=%s",
            self._config.camera_type,
            self._config.mode,
        )
