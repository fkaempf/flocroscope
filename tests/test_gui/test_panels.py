"""Tests for GUI panel classes.

These tests verify panel construction, property access, and internal
state management WITHOUT requiring Dear ImGui.  Tests that call
``draw()`` use ``pytest.importorskip("imgui")`` to skip gracefully
when imgui is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from virtual_reality.config.schema import (
    CalibrationConfig,
    VirtualRealityConfig,
    WarpConfig,
)
from virtual_reality.gui.panels.calibration import (
    CalibrationPanel,
    _FISHEYE_FILES,
    _PINHOLE_FILES,
)
from virtual_reality.gui.panels.comms import CommsPanel
from virtual_reality.gui.panels.config_editor import ConfigEditorPanel
from virtual_reality.gui.panels.mapping import MappingPanel
from virtual_reality.gui.panels.session import SessionPanel
from virtual_reality.gui.panels.stimulus import StimulusPanel, STIMULUS_TYPES


# ------------------------------------------------------------------ #
#  StimulusPanel
# ------------------------------------------------------------------ #


class TestStimulusPanelConstruction:
    """Tests for StimulusPanel instantiation and defaults."""

    def test_default_construction(self) -> None:
        """Panel can be constructed with a default config."""
        cfg = VirtualRealityConfig()
        panel = StimulusPanel(cfg)
        assert panel._config is cfg
        assert panel._selected_idx == 0
        assert panel._running is False

    def test_custom_config_is_stored(self) -> None:
        """Panel stores the provided config reference."""
        cfg = VirtualRealityConfig()
        cfg.arena.radius_mm = 99.0
        panel = StimulusPanel(cfg)
        assert panel._config.arena.radius_mm == 99.0

    def test_stimulus_types_populated(self) -> None:
        """Module-level STIMULUS_TYPES has expected entries."""
        assert len(STIMULUS_TYPES) >= 1
        labels = [label for label, _key in STIMULUS_TYPES]
        keys = [key for _label, key in STIMULUS_TYPES]
        assert "fly_3d" in keys
        assert "Fly 3D (GLB)" in labels

    def test_draw_requires_imgui(self) -> None:
        """draw() imports imgui; skip if unavailable."""
        pytest.importorskip("imgui")
        # If imgui is available, draw() would need a context.
        # We only verify the import gate here.


# ------------------------------------------------------------------ #
#  SessionPanel
# ------------------------------------------------------------------ #


class TestSessionPanelConstruction:
    """Tests for SessionPanel instantiation and field defaults."""

    def test_default_construction(self) -> None:
        """Panel initialises with expected default fields."""
        cfg = VirtualRealityConfig()
        panel = SessionPanel(cfg)
        assert panel._config is cfg
        assert panel._session is None
        assert panel._experimenter == ""
        assert panel._fly_genotype == ""
        assert panel._fly_id == ""
        assert panel._notes == ""
        assert panel._status_msg == ""

    def test_custom_config_stored(self) -> None:
        """Panel stores the mutable config reference."""
        cfg = VirtualRealityConfig()
        cfg.fly_model.phys_length_mm = 5.0
        panel = SessionPanel(cfg)
        assert panel._config.fly_model.phys_length_mm == 5.0


class TestSessionPanelStartSession:
    """Tests for SessionPanel._start_session() method."""

    def test_start_session_creates_session(self) -> None:
        """_start_session() creates and starts a Session instance."""
        cfg = VirtualRealityConfig()
        panel = SessionPanel(cfg)
        panel._experimenter = "Alice"
        panel._fly_genotype = "CS"
        panel._fly_id = "fly42"
        panel._notes = "test run"

        panel._start_session()

        session = panel._session
        assert session is not None
        assert session.is_running
        assert session.metadata.experimenter == "Alice"
        assert session.metadata.fly_genotype == "CS"
        assert session.metadata.fly_stock_id == "fly42"
        assert session.metadata.notes == "test run"
        assert session.metadata.stimulus_type == "gui"
        assert len(session.session_id) == 12

        # Clean up
        session.stop()

    def test_start_session_sets_status_msg(self) -> None:
        """_start_session() updates the status message."""
        cfg = VirtualRealityConfig()
        panel = SessionPanel(cfg)
        panel._start_session()

        assert panel._status_msg != ""
        assert panel._session.session_id in panel._status_msg

        panel._session.stop()

    def test_start_session_empty_fly_id_skips_stock_id(self) -> None:
        """_start_session() does not set fly_stock_id when fly_id is empty."""
        cfg = VirtualRealityConfig()
        panel = SessionPanel(cfg)
        panel._fly_id = ""

        panel._start_session()

        # When fly_id is empty, the code skips the assignment,
        # so fly_stock_id stays at its default (empty string).
        assert panel._session.metadata.fly_stock_id == ""

        panel._session.stop()

    def test_start_session_with_custom_config(self) -> None:
        """Session receives the panel's config reference."""
        cfg = VirtualRealityConfig()
        cfg.arena.radius_mm = 123.0
        panel = SessionPanel(cfg)

        panel._start_session()

        snapshot = panel._session.metadata.config_snapshot
        assert snapshot["arena_radius_mm"] == 123.0

        panel._session.stop()


# ------------------------------------------------------------------ #
#  ConfigEditorPanel
# ------------------------------------------------------------------ #


class TestConfigEditorPanelConstruction:
    """Tests for ConfigEditorPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel initialises with empty path and status."""
        cfg = VirtualRealityConfig()
        panel = ConfigEditorPanel(cfg)
        assert panel._config is cfg
        assert panel._config_path == ""
        assert panel._status_msg == ""

    def test_custom_config_stored(self) -> None:
        """Panel stores the config reference for later mutation."""
        cfg = VirtualRealityConfig()
        cfg.display.target_fps = 120
        panel = ConfigEditorPanel(cfg)
        assert panel._config.display.target_fps == 120

    def test_load_config_no_path(self) -> None:
        """_load_config() reports an error when no path is set."""
        cfg = VirtualRealityConfig()
        panel = ConfigEditorPanel(cfg)
        panel._config_path = ""
        panel._load_config()
        assert panel._status_msg == "No path specified"

    def test_save_config_no_path(self) -> None:
        """_save_config() reports an error when no path is set."""
        cfg = VirtualRealityConfig()
        panel = ConfigEditorPanel(cfg)
        panel._config_path = ""
        panel._save_config()
        assert panel._status_msg == "No path specified"

    def test_reset_defaults(self) -> None:
        """_reset_defaults() restores all config fields to defaults."""
        cfg = VirtualRealityConfig()
        cfg.arena.radius_mm = 999.0
        cfg.camera.fov_x_deg = 10.0
        cfg.display.target_fps = 1
        panel = ConfigEditorPanel(cfg)

        panel._reset_defaults()

        assert cfg.arena.radius_mm == 40.0
        assert cfg.camera.fov_x_deg == 200.0
        assert cfg.display.target_fps == 60
        assert panel._status_msg == "Reset to defaults"


# ------------------------------------------------------------------ #
#  CommsPanel
# ------------------------------------------------------------------ #


class TestCommsPanelConstruction:
    """Tests for CommsPanel instantiation."""

    def test_default_construction_no_comms(self) -> None:
        """Panel can be constructed with comms=None (default)."""
        panel = CommsPanel()
        assert panel.comms is None

    def test_construction_with_none(self) -> None:
        """Explicitly passing None yields disabled state."""
        panel = CommsPanel(comms=None)
        assert panel.comms is None
        assert panel._comms is None

    def test_construction_with_mock_hub(self) -> None:
        """Panel stores a provided CommsHub instance."""
        hub = MagicMock()
        panel = CommsPanel(comms=hub)
        assert panel.comms is hub


class TestCommsPanelDisabledState:
    """Tests for CommsPanel with comms=None (disabled)."""

    def test_comms_is_none(self) -> None:
        """When comms is None, the panel is in disabled state."""
        panel = CommsPanel()
        assert panel._comms is None

    def test_no_attribute_errors(self) -> None:
        """Accessing the comms property when None does not raise."""
        panel = CommsPanel()
        result = panel.comms
        assert result is None


class TestCommsPanelProperty:
    """Tests for CommsPanel.comms property getter and setter."""

    def test_getter_returns_stored_hub(self) -> None:
        """comms property returns the stored CommsHub."""
        hub = MagicMock()
        panel = CommsPanel(comms=hub)
        assert panel.comms is hub

    def test_setter_updates_hub(self) -> None:
        """Setting comms replaces the stored hub."""
        panel = CommsPanel()
        assert panel.comms is None

        hub = MagicMock()
        panel.comms = hub
        assert panel.comms is hub

    def test_setter_to_none(self) -> None:
        """Setting comms to None disables the panel."""
        hub = MagicMock()
        panel = CommsPanel(comms=hub)
        assert panel.comms is hub

        panel.comms = None
        assert panel.comms is None

    def test_setter_replaces_hub(self) -> None:
        """Setting comms replaces one hub with another."""
        hub1 = MagicMock(name="hub1")
        hub2 = MagicMock(name="hub2")

        panel = CommsPanel(comms=hub1)
        assert panel.comms is hub1

        panel.comms = hub2
        assert panel.comms is hub2
        assert panel.comms is not hub1


# ------------------------------------------------------------------ #
#  CalibrationPanel
# ------------------------------------------------------------------ #


class TestCalibrationPanelConstruction:
    """Tests for CalibrationPanel instantiation and defaults."""

    def test_default_construction(self) -> None:
        """Panel can be constructed with a default CalibrationConfig."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        assert panel._config is cfg
        assert panel._status_msg == ""
        assert panel._last_rms is None

    def test_custom_config_is_stored(self) -> None:
        """Panel stores the provided config reference."""
        cfg = CalibrationConfig(
            camera_type="rotpy",
            proj_w=1920,
            proj_h=1080,
            mode="gray",
            exposure_ms=25.0,
        )
        panel = CalibrationPanel(cfg)
        assert panel._config.camera_type == "rotpy"
        assert panel._config.proj_w == 1920
        assert panel._config.proj_h == 1080
        assert panel._config.mode == "gray"
        assert panel._config.exposure_ms == 25.0

    def test_from_virtual_reality_config(self) -> None:
        """Panel works with config extracted from VirtualRealityConfig."""
        vr_cfg = VirtualRealityConfig()
        vr_cfg.calibration.camera_type = "alvium"
        vr_cfg.calibration.exposure_ms = 15.0
        panel = CalibrationPanel(vr_cfg.calibration)
        assert panel._config.camera_type == "alvium"
        assert panel._config.exposure_ms == 15.0

    def test_fisheye_files_constant(self) -> None:
        """Module-level _FISHEYE_FILES has the expected entries."""
        assert len(_FISHEYE_FILES) == 3
        assert "fisheye.K.npy" in _FISHEYE_FILES
        assert "fisheye.D.npy" in _FISHEYE_FILES
        assert "fisheye.xi.npy" in _FISHEYE_FILES

    def test_pinhole_files_constant(self) -> None:
        """Module-level _PINHOLE_FILES has the expected entries."""
        assert len(_PINHOLE_FILES) == 2
        assert "pinhole.K.npy" in _PINHOLE_FILES
        assert "pinhole.D.npy" in _PINHOLE_FILES


class TestCalibrationPanelRunCalibration:
    """Tests for CalibrationPanel._run_calibration() placeholder."""

    def test_run_calibration_sets_status(self) -> None:
        """_run_calibration() sets a non-empty status message."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert panel._status_msg != ""
        assert cfg.camera_type in panel._status_msg
        assert cfg.mode in panel._status_msg

    def test_run_calibration_includes_camera_type(self) -> None:
        """Status message mentions the configured camera type."""
        cfg = CalibrationConfig(camera_type="rotpy")
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert "rotpy" in panel._status_msg

    def test_run_calibration_includes_mode(self) -> None:
        """Status message mentions the configured capture mode."""
        cfg = CalibrationConfig(mode="gray")
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert "gray" in panel._status_msg


# ------------------------------------------------------------------ #
#  MappingPanel
# ------------------------------------------------------------------ #


class TestMappingPanelConstruction:
    """Tests for MappingPanel instantiation and defaults."""

    def test_default_construction(self) -> None:
        """Panel can be constructed with a default WarpConfig."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        assert panel._config is cfg
        assert panel._status_msg == ""
        assert panel._map_shape is None

    def test_custom_config_is_stored(self) -> None:
        """Panel stores the provided config reference."""
        cfg = WarpConfig(
            mapx_path="/tmp/mapx.npy",
            mapy_path="/tmp/mapy.npy",
        )
        panel = MappingPanel(cfg)
        assert panel._config.mapx_path == "/tmp/mapx.npy"
        assert panel._config.mapy_path == "/tmp/mapy.npy"

    def test_from_virtual_reality_config(self) -> None:
        """Panel works with config extracted from VirtualRealityConfig."""
        vr_cfg = VirtualRealityConfig()
        vr_cfg.warp.mapx_path = "data/mapx.experimental.npy"
        panel = MappingPanel(vr_cfg.warp)
        assert panel._config.mapx_path == "data/mapx.experimental.npy"


class TestMappingPanelLoadWarpMap:
    """Tests for MappingPanel._load_warp_map() placeholder."""

    def test_load_no_paths_sets_error(self) -> None:
        """_load_warp_map() reports an error when paths are empty."""
        cfg = WarpConfig(mapx_path="", mapy_path="")
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" in panel._status_msg

    def test_load_only_mapx_set(self) -> None:
        """_load_warp_map() reports error when only mapx is set."""
        cfg = WarpConfig(mapx_path="/tmp/mapx.npy", mapy_path="")
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" in panel._status_msg

    def test_load_only_mapy_set(self) -> None:
        """_load_warp_map() reports error when only mapy is set."""
        cfg = WarpConfig(mapx_path="", mapy_path="/tmp/mapy.npy")
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" in panel._status_msg

    def test_load_both_paths_set(self) -> None:
        """_load_warp_map() sets a non-error status when paths are set."""
        cfg = WarpConfig(
            mapx_path="/tmp/mapx.npy",
            mapy_path="/tmp/mapy.npy",
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" not in panel._status_msg
        assert panel._status_msg != ""
        assert "/tmp/mapx.npy" in panel._status_msg
        assert "/tmp/mapy.npy" in panel._status_msg


class TestMappingPanelRunPipeline:
    """Tests for MappingPanel._run_mapping_pipeline() placeholder."""

    def test_run_pipeline_sets_status(self) -> None:
        """_run_mapping_pipeline() sets a non-empty status message."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        assert panel._status_msg != ""
        assert "pipeline" in panel._status_msg.lower()


# ------------------------------------------------------------------ #
#  draw() methods -- require imgui
# ------------------------------------------------------------------ #


class TestDrawMethodsRequireImgui:
    """Verify that draw() methods cannot run without imgui.

    These tests use ``pytest.importorskip("imgui")`` to skip when
    Dear ImGui is not installed.  When imgui IS available, we still
    skip because a full OpenGL context is needed for rendering.
    """

    def test_stimulus_draw_skips_without_imgui(self) -> None:
        """StimulusPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        # imgui is available but draw() needs an active context,
        # so we verify the import succeeds and bail.
        pytest.skip("imgui available but OpenGL context required for draw()")

    def test_session_draw_skips_without_imgui(self) -> None:
        """SessionPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        pytest.skip("imgui available but OpenGL context required for draw()")

    def test_config_editor_draw_skips_without_imgui(self) -> None:
        """ConfigEditorPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        pytest.skip("imgui available but OpenGL context required for draw()")

    def test_comms_draw_skips_without_imgui(self) -> None:
        """CommsPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        pytest.skip("imgui available but OpenGL context required for draw()")

    def test_calibration_draw_skips_without_imgui(self) -> None:
        """CalibrationPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        pytest.skip("imgui available but OpenGL context required for draw()")

    def test_mapping_draw_skips_without_imgui(self) -> None:
        """MappingPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        pytest.skip("imgui available but OpenGL context required for draw()")
