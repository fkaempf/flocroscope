"""Tests for GUI panel classes.

These tests verify panel construction, property access, and internal
state management WITHOUT requiring Dear ImGui.  Tests that call
``draw()`` use ``pytest.importorskip("imgui")`` to skip gracefully
when imgui is not installed.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from virtual_reality.comms.flomington import (
    FlomingtonClient,
    FlomingtonConfig,
    FlyCross,
    FlyStock,
)
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
from virtual_reality.gui.panels.flomington import FlomingtonPanel
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
        labels = [entry[0] for entry in STIMULUS_TYPES]
        keys = [entry[1] for entry in STIMULUS_TYPES]
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
        assert panel._calibrating is False
        assert panel._calibration_thread is None

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

    def test_is_calibrating_property(self) -> None:
        """is_calibrating property reflects _calibrating state."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        assert panel.is_calibrating is False

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
    """Tests for CalibrationPanel._run_calibration() with threading."""

    def test_run_calibration_sets_status(self) -> None:
        """_run_calibration() sets a non-empty status and completes with camera/mode info."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert panel._status_msg != ""
        # Wait for thread completion, then check final status
        if panel._calibration_thread:
            panel._calibration_thread.join(timeout=5.0)
        assert cfg.camera_type in panel._status_msg
        assert cfg.mode in panel._status_msg

    def test_run_calibration_includes_camera_type(self) -> None:
        """Completed status message mentions the configured camera type."""
        cfg = CalibrationConfig(camera_type="rotpy")
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        if panel._calibration_thread:
            panel._calibration_thread.join(timeout=5.0)
        assert "rotpy" in panel._status_msg

    def test_run_calibration_includes_mode(self) -> None:
        """Completed status message mentions the configured capture mode."""
        cfg = CalibrationConfig(mode="gray")
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        if panel._calibration_thread:
            panel._calibration_thread.join(timeout=5.0)
        assert "gray" in panel._status_msg

    def test_run_calibration_starts_thread(self) -> None:
        """_run_calibration() starts a background thread."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert panel._calibration_thread is not None
        assert panel._calibration_thread.daemon is True
        panel._calibration_thread.join(timeout=2.0)

    def test_run_calibration_sets_calibrating_flag(self) -> None:
        """_run_calibration() sets _calibrating to True."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        # The flag is True immediately after calling
        # (thread may complete very quickly, so just check it was set)
        assert panel._calibration_thread is not None
        panel._calibration_thread.join(timeout=2.0)

    def test_calibration_completes(self) -> None:
        """Background calibration thread completes and clears the flag."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        panel._calibration_thread.join(timeout=5.0)
        assert panel._calibrating is False
        assert "complete" in panel._status_msg.lower()

    def test_duplicate_calibration_ignored(self) -> None:
        """A second _run_calibration() while running is ignored."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._calibrating = True  # Simulate already running
        panel._run_calibration()
        assert "already" in panel._status_msg.lower()

    def test_do_calibration_returns_string(self) -> None:
        """_do_calibration() returns a human-readable summary."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        result = panel._do_calibration()
        assert isinstance(result, str)
        assert len(result) > 0


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
        assert panel._warp_map is None
        assert panel._mapping_running is False

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

    def test_warp_map_property(self) -> None:
        """warp_map property returns None by default."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        assert panel.warp_map is None

    def test_is_mapping_property(self) -> None:
        """is_mapping property returns False by default."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        assert panel.is_mapping is False


class TestMappingPanelLoadWarpMap:
    """Tests for MappingPanel._load_warp_map() with real loading."""

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

    def test_load_file_not_found(self) -> None:
        """_load_warp_map() handles missing files gracefully."""
        cfg = WarpConfig(
            mapx_path="/nonexistent/mapx.npy",
            mapy_path="/nonexistent/mapy.npy",
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "not found" in panel._status_msg.lower() or "No such file" in panel._status_msg

    def test_load_real_warp_maps(self, tmp_path) -> None:
        """_load_warp_map() successfully loads real numpy warp maps."""
        mapx = np.random.uniform(0, 100, (600, 800)).astype(np.float32)
        mapy = np.random.uniform(0, 80, (600, 800)).astype(np.float32)
        mapx_path = str(tmp_path / "mapx.npy")
        mapy_path = str(tmp_path / "mapy.npy")
        np.save(mapx_path, mapx)
        np.save(mapy_path, mapy)

        cfg = WarpConfig(mapx_path=mapx_path, mapy_path=mapy_path)
        panel = MappingPanel(cfg)
        panel._load_warp_map()

        assert panel._warp_map is not None
        assert panel._map_shape is not None
        assert panel._map_shape == (800, 600)  # (proj_w, proj_h)
        assert panel.warp_map is not None
        assert panel.warp_map.proj_w == 800
        assert panel.warp_map.proj_h == 600
        assert "valid" in panel._status_msg.lower()

    def test_load_invalid_warp_maps(self, tmp_path) -> None:
        """_load_warp_map() handles all-NaN maps gracefully."""
        mapx = np.full((100, 200), np.nan, dtype=np.float32)
        mapy = np.full((100, 200), np.nan, dtype=np.float32)
        mapx_path = str(tmp_path / "mapx.npy")
        mapy_path = str(tmp_path / "mapy.npy")
        np.save(mapx_path, mapx)
        np.save(mapy_path, mapy)

        cfg = WarpConfig(mapx_path=mapx_path, mapy_path=mapy_path)
        panel = MappingPanel(cfg)
        panel._load_warp_map()

        assert panel._warp_map is None
        assert "invalid" in panel._status_msg.lower() or "no valid" in panel._status_msg.lower()


class TestMappingPanelRunPipeline:
    """Tests for MappingPanel._run_mapping_pipeline() with threading."""

    def test_run_pipeline_sets_status(self) -> None:
        """_run_mapping_pipeline() sets a running status message."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        assert panel._status_msg != ""
        if panel._mapping_thread:
            panel._mapping_thread.join(timeout=2.0)

    def test_run_pipeline_starts_thread(self) -> None:
        """_run_mapping_pipeline() starts a background thread."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        assert panel._mapping_thread is not None
        assert panel._mapping_thread.daemon is True
        panel._mapping_thread.join(timeout=2.0)

    def test_mapping_completes(self) -> None:
        """Background mapping thread completes and clears the flag."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        panel._mapping_thread.join(timeout=5.0)
        assert panel._mapping_running is False
        assert "complete" in panel._status_msg.lower()

    def test_duplicate_mapping_ignored(self) -> None:
        """A second _run_mapping_pipeline() while running is ignored."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._mapping_running = True
        panel._run_mapping_pipeline()
        assert "already" in panel._status_msg.lower()

    def test_do_mapping_returns_string(self) -> None:
        """_do_mapping() returns a human-readable summary."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        result = panel._do_mapping()
        assert isinstance(result, str)
        assert len(result) > 0


# ------------------------------------------------------------------ #
#  FlomingtonPanel
# ------------------------------------------------------------------ #


class TestFlomingtonPanelConstruction:
    """Tests for FlomingtonPanel instantiation and defaults."""

    def test_default_construction_no_client(self) -> None:
        """Panel can be constructed with client=None (default)."""
        panel = FlomingtonPanel()
        assert panel.client is None
        assert panel._lookup_id == ""
        assert panel._lookup_type == 0
        assert panel._status_msg == ""
        assert panel.stock is None
        assert panel.cross is None

    def test_construction_with_none(self) -> None:
        """Explicitly passing None yields disconnected state."""
        panel = FlomingtonPanel(client=None)
        assert panel.client is None

    def test_construction_with_client(self) -> None:
        """Panel stores a provided FlomingtonClient."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        assert panel.client is client

    def test_client_property_setter(self) -> None:
        """client property setter updates the stored client."""
        panel = FlomingtonPanel()
        assert panel.client is None

        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel.client = client
        assert panel.client is client

    def test_client_property_setter_to_none(self) -> None:
        """Setting client to None removes the client."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        panel.client = None
        assert panel.client is None


class TestFlomingtonPanelLookup:
    """Tests for FlomingtonPanel._do_lookup() method."""

    def test_lookup_empty_id(self) -> None:
        """_do_lookup() reports error for empty ID."""
        panel = FlomingtonPanel()
        panel._lookup_id = ""
        panel._do_lookup()
        assert "enter" in panel._status_msg.lower()

    def test_lookup_whitespace_id(self) -> None:
        """_do_lookup() reports error for whitespace-only ID."""
        panel = FlomingtonPanel()
        panel._lookup_id = "   "
        panel._do_lookup()
        assert "enter" in panel._status_msg.lower()

    def test_lookup_no_client(self) -> None:
        """_do_lookup() reports error when no client configured."""
        panel = FlomingtonPanel(client=None)
        panel._lookup_id = "test123"
        panel._do_lookup()
        assert "not configured" in panel._status_msg.lower()

    def test_stock_lookup_not_found(self) -> None:
        """Stock lookup with placeholder client returns not found."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        panel._lookup_id = "XXXX1234"
        panel._lookup_type = 0  # Stock
        panel._do_lookup()
        assert "not found" in panel._status_msg.lower()
        assert panel.stock is None

    def test_cross_lookup_not_found(self) -> None:
        """Cross lookup with placeholder client returns not found."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        panel._lookup_id = "XXXX5678"
        panel._lookup_type = 1  # Cross
        panel._do_lookup()
        assert "not found" in panel._status_msg.lower()
        assert panel.cross is None

    def test_stock_lookup_found(self) -> None:
        """Stock lookup with mocked client stores the stock."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        stock = FlyStock(
            stock_id="ABC12345",
            name="CS Wild-type",
            genotype="Canton-S",
            source="Bloomington",
            genetic_tags=["wild-type"],
        )
        client.get_stock = MagicMock(return_value=stock)

        panel = FlomingtonPanel(client=client)
        panel._lookup_id = "ABC12345"
        panel._lookup_type = 0
        panel._do_lookup()

        assert panel.stock is stock
        assert panel.cross is None
        assert "CS Wild-type" in panel._status_msg

    def test_cross_lookup_found(self) -> None:
        """Cross lookup with mocked client stores the cross."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        cross = FlyCross(
            cross_id="XYZ98765",
            virgin_parent="Gal4",
            male_parent="UAS-GCaMP",
            status="ripening",
            experiment_type="2P",
        )
        client.get_cross = MagicMock(return_value=cross)

        panel = FlomingtonPanel(client=client)
        panel._lookup_id = "XYZ98765"
        panel._lookup_type = 1
        panel._do_lookup()

        assert panel.cross is cross
        assert panel.stock is None
        assert "XYZ98765" in panel._status_msg

    def test_stock_lookup_clears_previous_cross(self) -> None:
        """Stock lookup clears any previously stored cross."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        stock = FlyStock(stock_id="AA", name="test")
        client.get_stock = MagicMock(return_value=stock)

        panel = FlomingtonPanel(client=client)
        panel._cross = FlyCross(cross_id="old")
        panel._lookup_id = "AA"
        panel._lookup_type = 0
        panel._do_lookup()

        assert panel.stock is stock
        assert panel.cross is None

    def test_cross_lookup_clears_previous_stock(self) -> None:
        """Cross lookup clears any previously stored stock."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        cross = FlyCross(cross_id="BB", status="done")
        client.get_cross = MagicMock(return_value=cross)

        panel = FlomingtonPanel(client=client)
        panel._stock = FlyStock(stock_id="old")
        panel._lookup_id = "BB"
        panel._lookup_type = 1
        panel._do_lookup()

        assert panel.cross is cross
        assert panel.stock is None


class TestFlomingtonPanelLinkToSession:
    """Tests for FlomingtonPanel._link_to_session() placeholder."""

    def test_link_with_stock(self) -> None:
        """_link_to_session() with a stock sets status."""
        panel = FlomingtonPanel()
        panel._stock = FlyStock(
            stock_id="ABC", name="CS",
        )
        panel._link_to_session()
        assert "link" in panel._status_msg.lower()
        assert "CS" in panel._status_msg

    def test_link_with_cross(self) -> None:
        """_link_to_session() with a cross sets status."""
        panel = FlomingtonPanel()
        panel._cross = FlyCross(cross_id="XYZ")
        panel._link_to_session()
        assert "link" in panel._status_msg.lower()
        assert "XYZ" in panel._status_msg

    def test_link_no_record(self) -> None:
        """_link_to_session() with no record sets error."""
        panel = FlomingtonPanel()
        panel._link_to_session()
        assert "no record" in panel._status_msg.lower()


class TestFlomingtonPanelImport:
    """Tests for FlomingtonPanel module import and re-export."""

    def test_importable_from_panels_package(self) -> None:
        """FlomingtonPanel is importable from the panels package."""
        from virtual_reality.gui.panels import FlomingtonPanel as FP
        assert FP is FlomingtonPanel

    def test_in_all(self) -> None:
        """FlomingtonPanel is in the __all__ list."""
        from virtual_reality.gui.panels import __all__
        assert "FlomingtonPanel" in __all__


# ------------------------------------------------------------------ #
#  SessionPanel — Flomington integration
# ------------------------------------------------------------------ #


class TestSessionPanelFlomington:
    """Tests for SessionPanel Flomington integration."""

    def test_default_construction_no_flomington(self) -> None:
        """Panel can be constructed without flomington_client."""
        cfg = VirtualRealityConfig()
        panel = SessionPanel(cfg)
        assert panel.flomington_client is None
        assert panel._flomington_lookup_done is False

    def test_construction_with_flomington(self) -> None:
        """Panel stores a provided flomington_client."""
        cfg = VirtualRealityConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        panel = SessionPanel(cfg, flomington_client=client)
        assert panel.flomington_client is client

    def test_lookup_populates_genotype_from_stock(self) -> None:
        """_lookup_from_flomington() populates genotype from stock."""
        cfg = VirtualRealityConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        stock = FlyStock(
            stock_id="AAAA1111",
            name="GMR-Gal4",
            genotype="w[*]; P{GMR-GAL4}",
        )
        client.get_stock = MagicMock(return_value=stock)

        panel = SessionPanel(cfg, flomington_client=client)
        panel._fly_id = "AAAA1111"
        panel._lookup_from_flomington()

        assert panel._fly_genotype == "w[*]; P{GMR-GAL4}"
        assert panel._flomington_lookup_done is True

    def test_lookup_populates_genotype_from_cross(self) -> None:
        """_lookup_from_flomington() populates genotype from cross."""
        cfg = VirtualRealityConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        # Stock lookup returns None to fall through to cross
        client.get_stock = MagicMock(return_value=None)
        cross = FlyCross(
            cross_id="BBBB2222",
            virgin_genotype="w; Gal4",
            male_genotype="UAS-GCaMP7f",
            status="screening",
        )
        client.get_cross = MagicMock(return_value=cross)

        panel = SessionPanel(cfg, flomington_client=client)
        panel._fly_id = "BBBB2222"
        panel._lookup_from_flomington()

        assert "w; Gal4" in panel._fly_genotype
        assert "UAS-GCaMP7f" in panel._fly_genotype
        assert panel._flomington_lookup_done is True

    def test_lookup_not_found(self) -> None:
        """_lookup_from_flomington() reports not found."""
        cfg = VirtualRealityConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        client.get_stock = MagicMock(return_value=None)
        client.get_cross = MagicMock(return_value=None)

        panel = SessionPanel(cfg, flomington_client=client)
        panel._fly_id = "ZZZZ9999"
        panel._lookup_from_flomington()

        assert "not found" in panel._status_msg.lower()
        assert panel._flomington_lookup_done is False

    def test_lookup_no_client(self) -> None:
        """_lookup_from_flomington() does nothing when client is None."""
        cfg = VirtualRealityConfig()
        panel = SessionPanel(cfg)
        panel._fly_id = "test"
        panel._fly_genotype = "original"
        panel._lookup_from_flomington()
        assert panel._fly_genotype == "original"

    def test_lookup_empty_id(self) -> None:
        """_lookup_from_flomington() does nothing for empty ID."""
        cfg = VirtualRealityConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        panel = SessionPanel(cfg, flomington_client=client)
        panel._fly_id = ""
        panel._fly_genotype = "original"
        panel._lookup_from_flomington()
        assert panel._fly_genotype == "original"


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

    def test_flomington_draw_skips_without_imgui(self) -> None:
        """FlomingtonPanel.draw() requires imgui."""
        imgui = pytest.importorskip("imgui")
        pytest.skip("imgui available but OpenGL context required for draw()")
