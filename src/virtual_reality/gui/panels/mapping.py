"""Projector-camera mapping panel.

Displays warp map paths and dimensions, and provides buttons for
loading warp maps and running the structured-light mapping pipeline
in a background thread.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.config.schema import WarpConfig
    from virtual_reality.mapping.warp import WarpMap

logger = logging.getLogger(__name__)


class MappingPanel:
    """Panel for projector-camera warp map management.

    Shows the configured warp map file paths, their dimensions
    when loaded, and provides buttons for loading maps and running
    the mapping pipeline in a background thread.

    Args:
        config: Warp configuration (mutable).
    """

    def __init__(self, config: WarpConfig) -> None:
        self._config = config
        self._status_msg = ""
        self._map_shape: tuple[int, int] | None = None
        self._warp_map: WarpMap | None = None
        self._mapping_thread: threading.Thread | None = None
        self._mapping_running = False

    @property
    def warp_map(self) -> WarpMap | None:
        """The currently loaded WarpMap, or None."""
        return self._warp_map

    @property
    def is_mapping(self) -> bool:
        """Whether the mapping pipeline is currently running."""
        return self._mapping_running

    def draw(self) -> None:
        """Render the mapping panel contents."""
        import imgui

        imgui.begin("Mapping")

        # --- Warp map paths ---
        imgui.text("Warp Map Paths:")
        imgui.separator()

        imgui.bullet_text(
            f"mapx: {self._config.mapx_path or '(not set)'}",
        )
        imgui.bullet_text(
            f"mapy: {self._config.mapy_path or '(not set)'}",
        )

        imgui.spacing()

        # --- Warp map dimensions ---
        if self._map_shape is not None:
            imgui.text("Loaded Map Dimensions:")
            imgui.bullet_text(
                f"Size: {self._map_shape[0]} x {self._map_shape[1]}"
                " (w x h)",
            )
            if self._warp_map is not None:
                imgui.bullet_text(
                    f"Camera: {self._warp_map.cam_w} x "
                    f"{self._warp_map.cam_h} (inferred)",
                )
        else:
            imgui.text_colored(
                "No warp map loaded", 0.6, 0.6, 0.6,
            )

        imgui.spacing()

        # --- Action buttons ---
        if imgui.button("Load Warp Map"):
            self._load_warp_map()

        imgui.same_line()

        if self._mapping_running:
            imgui.text_colored(
                "Mapping in progress...", 0.9, 0.7, 0.2,
            )
        else:
            if imgui.button("Run Mapping Pipeline"):
                self._run_mapping_pipeline()

        # --- Status area ---
        imgui.separator()
        imgui.text("Status:")

        if self._status_msg:
            imgui.text_wrapped(self._status_msg)

        imgui.end()

    def _load_warp_map(self) -> None:
        """Load warp map files using the mapping.warp module.

        Calls :func:`~virtual_reality.mapping.warp.load_warp_map`
        with the configured paths, stores the result, and updates
        the panel display with the loaded dimensions.  Errors are
        caught and reported via the status message.
        """
        mapx = self._config.mapx_path
        mapy = self._config.mapy_path

        if not mapx or not mapy:
            self._status_msg = (
                "Cannot load: mapx and/or mapy path not configured."
            )
            return

        try:
            from virtual_reality.mapping.warp import load_warp_map

            warp = load_warp_map(mapx, mapy)
            self._warp_map = warp
            self._map_shape = (warp.proj_w, warp.proj_h)

            valid_pct = (
                warp.valid_mask.sum() / warp.valid_mask.size * 100
            )
            self._status_msg = (
                f"Loaded warp map: {warp.proj_w}x{warp.proj_h} "
                f"(projector), {warp.cam_w}x{warp.cam_h} "
                f"(camera), {valid_pct:.1f}% valid pixels"
            )
            logger.info(
                "Warp map loaded: proj=%dx%d, cam=%dx%d, "
                "valid=%.1f%%",
                warp.proj_w, warp.proj_h,
                warp.cam_w, warp.cam_h,
                valid_pct,
            )
        except FileNotFoundError as exc:
            self._status_msg = f"File not found: {exc}"
            logger.error("Warp map file not found: %s", exc)
        except RuntimeError as exc:
            self._status_msg = f"Invalid warp map: {exc}"
            logger.error("Invalid warp map: %s", exc)
        except Exception as exc:
            self._status_msg = f"Failed to load warp map: {exc}"
            logger.exception("Unexpected error loading warp map")

    def _run_mapping_pipeline(self) -> None:
        """Launch the structured-light mapping pipeline in a thread.

        Starts a daemon thread that calls :meth:`_do_mapping` and
        updates the status message on completion.  If a mapping is
        already in progress, the request is ignored.
        """
        if self._mapping_running:
            self._status_msg = "Mapping pipeline already in progress."
            return

        self._mapping_running = True
        self._status_msg = "Running mapping pipeline..."
        logger.info("Mapping pipeline run requested")

        self._mapping_thread = threading.Thread(
            target=self._mapping_worker,
            daemon=True,
            name="mapping-worker",
        )
        self._mapping_thread.start()

    def _mapping_worker(self) -> None:
        """Background thread target for the mapping pipeline.

        Calls :meth:`_do_mapping` and updates the panel state
        with the result.  Exceptions are caught and reported.
        """
        try:
            result_msg = self._do_mapping()
            self._status_msg = result_msg
            logger.info("Mapping pipeline completed: %s", result_msg)
        except Exception as exc:
            self._status_msg = f"Mapping pipeline failed: {exc}"
            logger.exception("Mapping pipeline failed")
        finally:
            self._mapping_running = False

    def _do_mapping(self) -> str:
        """Execute the structured-light mapping pipeline.

        This is the method that will be replaced with the real
        pipeline call once hardware integration is implemented.
        Currently it simulates progress and returns a placeholder
        result.

        When the real pipeline is ready, replace the body with::

            from virtual_reality.pipeline.calibration_pipeline import (
                run_calibration_pipeline,
            )
            result = run_calibration_pipeline(self._config)
            return "Mapping complete"

        Returns:
            A human-readable result summary string.
        """
        logger.info("Mapping pipeline started (placeholder)")

        self._status_msg = "Projecting sine patterns..."
        time.sleep(0.01)

        self._status_msg = "Decoding phase..."
        time.sleep(0.01)

        self._status_msg = "Building warp maps..."
        time.sleep(0.01)

        return (
            "Mapping pipeline complete (placeholder). "
            "Replace _do_mapping() with real pipeline."
        )
