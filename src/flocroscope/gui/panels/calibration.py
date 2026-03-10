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
    from flocroscope.config.schema import CalibrationConfig

logger = logging.getLogger(__name__)

# Fisheye intrinsic file names (K, D, xi)
_FISHEYE_FILES = ("fisheye.K.npy", "fisheye.D.npy", "fisheye.xi.npy")

# Pinhole intrinsic file names (K, D)
_PINHOLE_FILES = ("pinhole.K.npy", "pinhole.D.npy")


class CalibrationPanel:
    """Panel for camera calibration pipeline control and status.

    Args:
        config: Calibration configuration (mutable).
    """

    def __init__(self, config: CalibrationConfig) -> None:
        self._config = config
        self._status_msg = ""
        self._last_rms: float | None = None
        self._calibration_thread: threading.Thread | None = None
        self._calibrating = False
        self.window_tag = "win_calibration"

    @property
    def is_calibrating(self) -> bool:
        """Whether a calibration is currently running."""
        return self._calibrating

    def build(self) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.window(
            label="Calibration", tag=self.window_tag,
        ):
            dpg.add_text("Hardware Settings:")
            dpg.add_separator()
            dpg.add_text("", tag="cal_camera")
            dpg.add_text("", tag="cal_projector")
            dpg.add_text("", tag="cal_mode")
            dpg.add_text("", tag="cal_exposure")
            dpg.add_spacer(height=4)

            dpg.add_text("Intrinsic Files:")
            dpg.add_separator()
            dpg.add_text("", tag="cal_intrinsic_type")
            for i in range(3):
                dpg.add_text("", tag=f"cal_file_{i}")
            dpg.add_spacer(height=4)

            dpg.add_text(
                "", tag="cal_progress",
                color=(230, 179, 51),
            )
            dpg.add_button(
                label="Run Calibration",
                tag="cal_run_btn",
                callback=self._on_run,
            )

            dpg.add_separator()
            dpg.add_text("Status:")
            dpg.add_text("", tag="cal_status", wrap=400)
            dpg.add_text("", tag="cal_rms")

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        cfg = self._config
        dpg.set_value(
            "cal_camera", f"  Camera: {cfg.camera_type}",
        )
        dpg.set_value(
            "cal_projector",
            f"  Projector: {cfg.proj_w}x{cfg.proj_h}",
        )
        dpg.set_value("cal_mode", f"  Mode: {cfg.mode}")
        dpg.set_value(
            "cal_exposure",
            f"  Exposure: {cfg.exposure_ms} ms",
        )

        # Intrinsic files
        if cfg.camera_type == "alvium":
            dpg.set_value(
                "cal_intrinsic_type", "  Fisheye (omnidir):",
            )
            files = _FISHEYE_FILES
        else:
            dpg.set_value(
                "cal_intrinsic_type", "  Pinhole:",
            )
            files = _PINHOLE_FILES

        for i in range(3):
            if i < len(files):
                dpg.set_value(
                    f"cal_file_{i}", f"    {files[i]}",
                )
                dpg.show_item(f"cal_file_{i}")
            else:
                dpg.set_value(f"cal_file_{i}", "")
                dpg.hide_item(f"cal_file_{i}")

        # Calibration state
        if self._calibrating:
            dpg.set_value(
                "cal_progress",
                "Calibration in progress...",
            )
            dpg.configure_item(
                "cal_run_btn", enabled=False,
            )
        else:
            dpg.set_value("cal_progress", "")
            dpg.configure_item(
                "cal_run_btn", enabled=True,
            )

        dpg.set_value("cal_status", self._status_msg)

        if self._last_rms is not None:
            dpg.set_value(
                "cal_rms",
                f"Last RMS: {self._last_rms:.4f} px",
            )

    # -- callbacks --

    def _on_run(self, sender, app_data, user_data):
        self._run_calibration()

    def _run_calibration(self) -> None:
        """Launch the calibration pipeline in a background thread."""
        if self._calibrating:
            self._status_msg = (
                "Calibration already in progress."
            )
            return

        self._calibrating = True
        self._status_msg = (
            f"Running calibration for "
            f"{self._config.camera_type} camera "
            f"({self._config.mode} mode)..."
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
        """Background thread target."""
        try:
            result_msg = self._do_calibration()
            self._status_msg = result_msg
            logger.info(
                "Calibration completed: %s", result_msg,
            )
        except Exception as exc:
            self._status_msg = f"Calibration failed: {exc}"
            logger.exception("Calibration failed")
        finally:
            self._calibrating = False

    def _do_calibration(self) -> str:
        """Execute the calibration pipeline (placeholder)."""
        logger.info(
            "Calibration started: camera=%s, mode=%s, "
            "projector=%dx%d, exposure=%.1f ms",
            self._config.camera_type,
            self._config.mode,
            self._config.proj_w,
            self._config.proj_h,
            self._config.exposure_ms,
        )

        self._status_msg = "Detecting chessboard patterns..."
        time.sleep(0.01)
        self._status_msg = "Computing intrinsics..."
        time.sleep(0.01)
        self._status_msg = "Running structured-light mapping..."
        time.sleep(0.01)

        return (
            f"Calibration complete for "
            f"{self._config.camera_type} camera "
            f"({self._config.mode} mode). "
            "Replace _do_calibration() with real pipeline."
        )
