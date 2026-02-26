"""Calibration pipeline panel.

Displays camera/projector calibration settings, file paths for
intrinsic parameters, and provides buttons for running the
calibration pipeline.  The actual calibration requires hardware
and is triggered in a background thread.
"""

from __future__ import annotations

import logging
import threading
import time
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
    provides a button to run the calibration pipeline in a background
    thread.

    Args:
        config: Calibration configuration (mutable).
    """

    def __init__(self, config: CalibrationConfig) -> None:
        self._config = config
        self._status_msg = ""
        self._last_rms: float | None = None
        self._calibration_thread: threading.Thread | None = None
        self._calibrating = False

    @property
    def is_calibrating(self) -> bool:
        """Whether a calibration is currently running."""
        return self._calibrating

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
        if self._calibrating:
            imgui.text_colored(
                "Calibration in progress...", 0.9, 0.7, 0.2,
            )
        else:
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
        """Launch the calibration pipeline in a background thread.

        Sets status to running, starts a daemon thread that calls
        :meth:`_do_calibration`, and updates the status message on
        completion.  If a calibration is already in progress, the
        request is ignored.
        """
        if self._calibrating:
            self._status_msg = "Calibration already in progress."
            return

        self._calibrating = True
        self._status_msg = (
            f"Running calibration for {self._config.camera_type} "
            f"camera ({self._config.mode} mode)..."
        )
        logger.info(
            "Calibration run requested: camera=%s, mode=%s",
            self._config.camera_type,
            self._config.mode,
        )

        self._calibration_thread = threading.Thread(
            target=self._calibration_worker,
            daemon=True,
            name="calibration-worker",
        )
        self._calibration_thread.start()

    def _calibration_worker(self) -> None:
        """Background thread target that runs the calibration.

        Calls :meth:`_do_calibration` and updates the panel state
        with the result.  Exceptions are caught and reported via
        the status message.
        """
        try:
            result_msg = self._do_calibration()
            self._status_msg = result_msg
            logger.info("Calibration completed: %s", result_msg)
        except Exception as exc:
            self._status_msg = f"Calibration failed: {exc}"
            logger.exception("Calibration failed")
        finally:
            self._calibrating = False

    def _do_calibration(self) -> str:
        """Execute the calibration pipeline.

        This is the method that will be replaced with the real
        pipeline call once hardware integration is implemented.
        Currently it simulates progress and returns a placeholder
        result.

        When the real pipeline is ready, replace the body with::

            from virtual_reality.pipeline.calibration_pipeline import (
                run_calibration_pipeline,
            )
            result = run_calibration_pipeline(self._config)
            self._last_rms = result.rms  # if available
            return f"Calibration complete (RMS={result.rms:.4f} px)"

        Returns:
            A human-readable result summary string.
        """
        logger.info(
            "Calibration started: camera=%s, mode=%s, "
            "projector=%dx%d, exposure=%.1f ms",
            self._config.camera_type,
            self._config.mode,
            self._config.proj_w,
            self._config.proj_h,
            self._config.exposure_ms,
        )

        # Placeholder: simulate pipeline stages
        self._status_msg = "Detecting chessboard patterns..."
        time.sleep(0.01)  # Yield to allow GUI to refresh

        self._status_msg = "Computing intrinsics..."
        time.sleep(0.01)

        self._status_msg = "Running structured-light mapping..."
        time.sleep(0.01)

        return (
            f"Calibration complete for {self._config.camera_type} "
            f"camera ({self._config.mode} mode). "
            "Replace _do_calibration() with real pipeline."
        )
