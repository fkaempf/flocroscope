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
    from flocroscope.config.schema import WarpConfig
    from flocroscope.mapping.warp import WarpMap

logger = logging.getLogger(__name__)


class MappingPanel:
    """Panel for projector-camera warp map management.

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
        self.group_tag = "grp_mapping"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    @property
    def warp_map(self) -> WarpMap | None:
        """The currently loaded WarpMap, or None."""
        return self._warp_map

    @property
    def is_mapping(self) -> bool:
        """Whether the mapping pipeline is currently running."""
        return self._mapping_running

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(parent=parent, tag=self.group_tag):
            dpg.add_text("Warp Map Paths:")
            dpg.add_separator()
            dpg.add_text("", tag="map_mapx")
            dpg.add_text("", tag="map_mapy")
            dpg.add_spacer(height=4)

            dpg.add_text("", tag="map_dims_label")
            dpg.add_text("", tag="map_dims_size")
            dpg.add_text("", tag="map_dims_cam")
            dpg.add_text(
                "No warp map loaded", tag="map_no_map",
                color=(153, 153, 153),
            )

            dpg.add_spacer(height=4)

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Load Warp Map",
                    callback=self._on_load,
                )
                dpg.add_text(
                    "", tag="map_progress",
                    color=(230, 179, 51),
                )
                dpg.add_button(
                    label="Run Mapping Pipeline",
                    tag="map_run_btn",
                    callback=self._on_run,
                )

            dpg.add_separator()
            dpg.add_text("Status:")
            dpg.add_text("", tag="map_status", wrap=400)

    def update(self) -> None:
        """Push live data each frame."""
        import dearpygui.dearpygui as dpg

        dpg.set_value(
            "map_mapx",
            f"  mapx: "
            f"{self._config.mapx_path or '(not set)'}",
        )
        dpg.set_value(
            "map_mapy",
            f"  mapy: "
            f"{self._config.mapy_path or '(not set)'}",
        )

        if self._map_shape is not None:
            dpg.set_value(
                "map_dims_label", "Loaded Map Dimensions:",
            )
            dpg.set_value(
                "map_dims_size",
                f"  Size: {self._map_shape[0]} x "
                f"{self._map_shape[1]} (w x h)",
            )
            if self._warp_map is not None:
                dpg.set_value(
                    "map_dims_cam",
                    f"  Camera: {self._warp_map.cam_w} x "
                    f"{self._warp_map.cam_h} (inferred)",
                )
            dpg.hide_item("map_no_map")
            dpg.show_item("map_dims_label")
            dpg.show_item("map_dims_size")
            dpg.show_item("map_dims_cam")
        else:
            dpg.show_item("map_no_map")
            dpg.hide_item("map_dims_label")
            dpg.hide_item("map_dims_size")
            dpg.hide_item("map_dims_cam")

        if self._mapping_running:
            dpg.set_value(
                "map_progress", "Mapping in progress...",
            )
            dpg.configure_item(
                "map_run_btn", enabled=False,
            )
        else:
            dpg.set_value("map_progress", "")
            dpg.configure_item(
                "map_run_btn", enabled=True,
            )

        dpg.set_value("map_status", self._status_msg)

    # -- callbacks --

    def _on_load(self, sender, app_data, user_data):
        self._load_warp_map()

    def _on_run(self, sender, app_data, user_data):
        self._run_mapping_pipeline()

    def _load_warp_map(self) -> None:
        """Load warp map files."""
        mapx = self._config.mapx_path
        mapy = self._config.mapy_path

        if not mapx or not mapy:
            self._status_msg = (
                "Cannot load: mapx and/or mapy path "
                "not configured."
            )
            return

        try:
            from flocroscope.mapping.warp import load_warp_map

            warp = load_warp_map(mapx, mapy)
            self._warp_map = warp
            self._map_shape = (warp.proj_w, warp.proj_h)

            valid_pct = (
                warp.valid_mask.sum()
                / warp.valid_mask.size * 100
            )
            self._status_msg = (
                f"Loaded warp map: {warp.proj_w}x"
                f"{warp.proj_h} (projector), "
                f"{warp.cam_w}x{warp.cam_h} (camera), "
                f"{valid_pct:.1f}% valid pixels"
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
            logger.error(
                "Warp map file not found: %s", exc,
            )
        except RuntimeError as exc:
            self._status_msg = f"Invalid warp map: {exc}"
            logger.error("Invalid warp map: %s", exc)
        except Exception as exc:
            self._status_msg = (
                f"Failed to load warp map: {exc}"
            )
            logger.exception(
                "Unexpected error loading warp map",
            )

    def _run_mapping_pipeline(self) -> None:
        """Launch the mapping pipeline in a thread."""
        if self._mapping_running:
            self._status_msg = (
                "Mapping pipeline already in progress."
            )
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
        """Background thread target."""
        try:
            result_msg = self._do_mapping()
            self._status_msg = result_msg
            logger.info(
                "Mapping pipeline completed: %s", result_msg,
            )
        except Exception as exc:
            self._status_msg = (
                f"Mapping pipeline failed: {exc}"
            )
            logger.exception("Mapping pipeline failed")
        finally:
            self._mapping_running = False

    def _do_mapping(self) -> str:
        """Execute the mapping pipeline (placeholder)."""
        logger.info(
            "Mapping pipeline started (placeholder)",
        )
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
