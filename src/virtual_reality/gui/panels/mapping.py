"""Projector-camera mapping panel.

Displays warp map paths and dimensions, and provides placeholder
buttons for loading warp maps and running the structured-light
mapping pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.config.schema import WarpConfig

logger = logging.getLogger(__name__)


class MappingPanel:
    """Panel for projector-camera warp map management.

    Shows the configured warp map file paths, their dimensions
    when loaded, and provides placeholder buttons for loading maps
    and running the mapping pipeline.

    Args:
        config: Warp configuration (mutable).
    """

    def __init__(self, config: WarpConfig) -> None:
        self._config = config
        self._status_msg = ""
        self._map_shape: tuple[int, int] | None = None

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
                f"Size: {self._map_shape[1]} x {self._map_shape[0]}"
                " (w x h)",
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

        if imgui.button("Run Mapping Pipeline"):
            self._run_mapping_pipeline()

        # --- Status area ---
        imgui.separator()
        imgui.text("Status:")

        if self._status_msg:
            imgui.text_wrapped(self._status_msg)

        imgui.end()

    def _load_warp_map(self) -> None:
        """Placeholder for loading warp map files.

        In a full implementation this would call
        :func:`~virtual_reality.mapping.warp.load_warp_map` and
        store the resulting dimensions.  For now it validates that
        paths are configured and sets a status message.
        """
        mapx = self._config.mapx_path
        mapy = self._config.mapy_path

        if not mapx or not mapy:
            self._status_msg = (
                "Cannot load: mapx and/or mapy path not configured."
            )
            return

        self._status_msg = (
            f"Load requested for:\n"
            f"  mapx: {mapx}\n"
            f"  mapy: {mapy}\n"
            "Use CLI or configure paths in YAML."
        )
        logger.info(
            "Warp map load requested: mapx=%s, mapy=%s",
            mapx, mapy,
        )

    def _run_mapping_pipeline(self) -> None:
        """Placeholder for running the structured-light mapping pipeline.

        In a full implementation this would launch the sine/gray
        pattern projection and phase decoding pipeline.  For now
        it sets a status message indicating the action.
        """
        self._status_msg = (
            "Mapping pipeline requested. "
            "Connect projector + camera hardware and run from CLI."
        )
        logger.info("Mapping pipeline run requested")
