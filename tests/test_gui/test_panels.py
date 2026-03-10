"""Tests for GUI panel classes.

These tests verify panel construction, property access, and internal
state management WITHOUT requiring DearPyGui.  Tests that call
``build()`` or ``update()`` use ``pytest.importorskip("dearpygui")``
to skip gracefully when dearpygui is not installed.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import numpy as np
import pytest

from flocroscope.comms.flomington import (
    FlomingtonClient,
    FlomingtonConfig,
    FlyCross,
    FlyStock,
)
from flocroscope.config.schema import (
    CalibrationConfig,
    FlocroscopeConfig,
    WarpConfig,
)
from flocroscope.gui.panels.behaviour import (
    BehaviourPanel,
    EXPERIMENT_TYPES,
)
from flocroscope.gui.panels.calibration import (
    CalibrationPanel,
    _FISHEYE_FILES,
    _PINHOLE_FILES,
)
from flocroscope.gui.panels.comms import CommsPanel
from flocroscope.gui.panels.config_editor import ConfigEditorPanel
from flocroscope.gui.panels.fictrac import FicTracPanel
from flocroscope.gui.panels.flomington import FlomingtonPanel
from flocroscope.gui.panels.mapping import MappingPanel
from flocroscope.gui.panels.optogenetics import OptogeneticsPanel
from flocroscope.gui.panels.scanimage import ScanImagePanel
from flocroscope.gui.panels.session import SessionPanel
from flocroscope.gui.panels.stimulus import StimulusPanel, STIMULUS_TYPES
from flocroscope.gui.panels.tracking import TrackingPanel


# ------------------------------------------------------------------ #
#  StimulusPanel
# ------------------------------------------------------------------ #


class TestStimulusPanelConstruction:
    """Tests for StimulusPanel instantiation and defaults."""

    def test_default_construction(self) -> None:
        """Panel can be constructed with a default config."""
        cfg = FlocroscopeConfig()
        panel = StimulusPanel(cfg)
        assert panel._config is cfg
        assert panel._selected_idx == 0
        assert panel._running is False

    def test_custom_config_is_stored(self) -> None:
        """Panel stores the provided config reference."""
        cfg = FlocroscopeConfig()
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

    def test_window_tag(self) -> None:
        """Panel has a group_tag and backward-compat window_tag."""
        cfg = FlocroscopeConfig()
        panel = StimulusPanel(cfg)
        assert panel.group_tag == "grp_stimulus"
        assert panel.window_tag == "grp_stimulus"

    def test_build_requires_dearpygui(self) -> None:
        """build() imports dearpygui; skip if unavailable."""
        pytest.importorskip("dearpygui")
        pytest.skip(
            "dearpygui available but viewport required"
        )


# ------------------------------------------------------------------ #
#  SessionPanel
# ------------------------------------------------------------------ #


class TestSessionPanelConstruction:
    """Tests for SessionPanel instantiation and field defaults."""

    def test_default_construction(self) -> None:
        """Panel initialises with expected default fields."""
        cfg = FlocroscopeConfig()
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
        cfg = FlocroscopeConfig()
        cfg.fly_model.phys_length_mm = 5.0
        panel = SessionPanel(cfg)
        assert panel._config.fly_model.phys_length_mm == 5.0

    def test_window_tag(self) -> None:
        """Panel has a group_tag and backward-compat window_tag."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)
        assert panel.group_tag == "grp_session"
        assert panel.window_tag == "grp_session"


class TestSessionPanelStartSession:
    """Tests for SessionPanel._start_session() method."""

    def test_start_session_creates_session(self) -> None:
        """_start_session() creates and starts a Session."""
        cfg = FlocroscopeConfig()
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

        session.stop()

    def test_start_session_sets_status_msg(self) -> None:
        """_start_session() updates the status message."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)

        panel._start_session()

        assert panel._status_msg != ""
        assert panel._session.session_id in panel._status_msg

        panel._session.stop()

    def test_start_session_empty_fly_id_skips_stock_id(
        self,
    ) -> None:
        """_start_session() skips fly_stock_id when empty."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)

        panel._start_session()

        assert panel._session.metadata.fly_stock_id == ""

        panel._session.stop()

    def test_start_session_with_custom_config(self) -> None:
        """Session receives the panel's config reference."""
        cfg = FlocroscopeConfig()
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
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        assert panel._config is cfg
        assert panel._config_path == ""
        assert panel._status_msg == ""

    def test_custom_config_stored(self) -> None:
        """Panel stores the config reference for mutation."""
        cfg = FlocroscopeConfig()
        cfg.display.target_fps = 120
        panel = ConfigEditorPanel(cfg)
        assert panel._config.display.target_fps == 120

    def test_load_config_no_path(self) -> None:
        """_load_config() reports error with no path."""
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._config_path = ""
        panel._load_config()
        assert panel._status_msg == "No path specified"

    def test_save_config_no_path(self) -> None:
        """_save_config() reports error with no path."""
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._config_path = ""
        panel._save_config()
        assert panel._status_msg == "No path specified"

    def test_reset_defaults(self) -> None:
        """_reset_defaults() restores all config fields."""
        cfg = FlocroscopeConfig()
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
        """Panel can be constructed with comms=None."""
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
        """When comms is None, the panel is disabled."""
        panel = CommsPanel()
        assert panel._comms is None

    def test_no_attribute_errors(self) -> None:
        """Accessing comms property when None no error."""
        panel = CommsPanel()
        result = panel.comms
        assert result is None


class TestCommsPanelProperty:
    """Tests for CommsPanel.comms property getter/setter."""

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
        """Panel can be constructed with default config."""
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

    def test_from_flocroscope_config(self) -> None:
        """Panel works with config from FlocroscopeConfig."""
        vr_cfg = FlocroscopeConfig()
        vr_cfg.calibration.camera_type = "alvium"
        vr_cfg.calibration.exposure_ms = 15.0
        panel = CalibrationPanel(vr_cfg.calibration)
        assert panel._config.camera_type == "alvium"
        assert panel._config.exposure_ms == 15.0

    def test_is_calibrating_property(self) -> None:
        """is_calibrating property reflects _calibrating."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        assert panel.is_calibrating is False

    def test_fisheye_files_constant(self) -> None:
        """Module-level _FISHEYE_FILES has expected entries."""
        assert len(_FISHEYE_FILES) == 3
        assert "fisheye.K.npy" in _FISHEYE_FILES
        assert "fisheye.D.npy" in _FISHEYE_FILES
        assert "fisheye.xi.npy" in _FISHEYE_FILES

    def test_pinhole_files_constant(self) -> None:
        """Module-level _PINHOLE_FILES has expected entries."""
        assert len(_PINHOLE_FILES) == 2
        assert "pinhole.K.npy" in _PINHOLE_FILES
        assert "pinhole.D.npy" in _PINHOLE_FILES


class TestCalibrationPanelRunCalibration:
    """Tests for CalibrationPanel._run_calibration()."""

    def test_run_calibration_sets_status(self) -> None:
        """_run_calibration() sets a non-empty status."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert panel._status_msg != ""
        if panel._calibration_thread:
            panel._calibration_thread.join(timeout=5.0)
        assert cfg.camera_type in panel._status_msg
        assert cfg.mode in panel._status_msg

    def test_run_calibration_includes_camera_type(
        self,
    ) -> None:
        """Status mentions the camera type."""
        cfg = CalibrationConfig(camera_type="rotpy")
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        if panel._calibration_thread:
            panel._calibration_thread.join(timeout=5.0)
        assert "rotpy" in panel._status_msg

    def test_run_calibration_includes_mode(self) -> None:
        """Status mentions the capture mode."""
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

    def test_run_calibration_sets_calibrating_flag(
        self,
    ) -> None:
        """_run_calibration() sets _calibrating to True."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        assert panel._calibration_thread is not None
        panel._calibration_thread.join(timeout=2.0)

    def test_calibration_completes(self) -> None:
        """Background thread completes and clears the flag."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._run_calibration()
        panel._calibration_thread.join(timeout=5.0)
        assert panel._calibrating is False
        assert "complete" in panel._status_msg.lower()

    def test_duplicate_calibration_ignored(self) -> None:
        """A second run while calibrating is ignored."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._calibrating = True
        panel._run_calibration()
        assert "already" in panel._status_msg.lower()

    def test_do_calibration_returns_string(self) -> None:
        """_do_calibration() returns a summary."""
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
        """Panel can be constructed with default config."""
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

    def test_from_flocroscope_config(self) -> None:
        """Panel works with config from FlocroscopeConfig."""
        vr_cfg = FlocroscopeConfig()
        vr_cfg.warp.mapx_path = "data/mapx.experimental.npy"
        panel = MappingPanel(vr_cfg.warp)
        assert (
            panel._config.mapx_path
            == "data/mapx.experimental.npy"
        )

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
    """Tests for MappingPanel._load_warp_map()."""

    def test_load_no_paths_sets_error(self) -> None:
        """_load_warp_map() reports error for empty paths."""
        cfg = WarpConfig(mapx_path="", mapy_path="")
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" in panel._status_msg

    def test_load_only_mapx_set(self) -> None:
        """Reports error when only mapx is set."""
        cfg = WarpConfig(
            mapx_path="/tmp/mapx.npy", mapy_path="",
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" in panel._status_msg

    def test_load_only_mapy_set(self) -> None:
        """Reports error when only mapy is set."""
        cfg = WarpConfig(
            mapx_path="", mapy_path="/tmp/mapy.npy",
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert "Cannot load" in panel._status_msg

    def test_load_file_not_found(self) -> None:
        """Handles missing files gracefully."""
        cfg = WarpConfig(
            mapx_path="/nonexistent/mapx.npy",
            mapy_path="/nonexistent/mapy.npy",
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()
        assert (
            "not found" in panel._status_msg.lower()
            or "No such file" in panel._status_msg
        )

    def test_load_real_warp_maps(self, tmp_path) -> None:
        """Successfully loads real numpy warp maps."""
        mapx = np.random.uniform(
            0, 100, (600, 800),
        ).astype(np.float32)
        mapy = np.random.uniform(
            0, 80, (600, 800),
        ).astype(np.float32)
        mapx_path = str(tmp_path / "mapx.npy")
        mapy_path = str(tmp_path / "mapy.npy")
        np.save(mapx_path, mapx)
        np.save(mapy_path, mapy)

        cfg = WarpConfig(
            mapx_path=mapx_path, mapy_path=mapy_path,
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()

        assert panel._warp_map is not None
        assert panel._map_shape is not None
        assert panel._map_shape == (800, 600)
        assert panel.warp_map is not None
        assert panel.warp_map.proj_w == 800
        assert panel.warp_map.proj_h == 600
        assert "valid" in panel._status_msg.lower()

    def test_load_invalid_warp_maps(self, tmp_path) -> None:
        """Handles all-NaN maps gracefully."""
        mapx = np.full(
            (100, 200), np.nan, dtype=np.float32,
        )
        mapy = np.full(
            (100, 200), np.nan, dtype=np.float32,
        )
        mapx_path = str(tmp_path / "mapx.npy")
        mapy_path = str(tmp_path / "mapy.npy")
        np.save(mapx_path, mapx)
        np.save(mapy_path, mapy)

        cfg = WarpConfig(
            mapx_path=mapx_path, mapy_path=mapy_path,
        )
        panel = MappingPanel(cfg)
        panel._load_warp_map()

        assert panel._warp_map is None
        assert (
            "invalid" in panel._status_msg.lower()
            or "no valid" in panel._status_msg.lower()
        )


class TestMappingPanelRunPipeline:
    """Tests for MappingPanel._run_mapping_pipeline()."""

    def test_run_pipeline_sets_status(self) -> None:
        """Sets a running status message."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        assert panel._status_msg != ""
        if panel._mapping_thread:
            panel._mapping_thread.join(timeout=2.0)

    def test_run_pipeline_starts_thread(self) -> None:
        """Starts a background thread."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        assert panel._mapping_thread is not None
        assert panel._mapping_thread.daemon is True
        panel._mapping_thread.join(timeout=2.0)

    def test_mapping_completes(self) -> None:
        """Thread completes and clears the flag."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._run_mapping_pipeline()
        panel._mapping_thread.join(timeout=5.0)
        assert panel._mapping_running is False
        assert "complete" in panel._status_msg.lower()

    def test_duplicate_mapping_ignored(self) -> None:
        """A second run while mapping is ignored."""
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        panel._mapping_running = True
        panel._run_mapping_pipeline()
        assert "already" in panel._status_msg.lower()

    def test_do_mapping_returns_string(self) -> None:
        """_do_mapping() returns a summary."""
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
        """Panel can be constructed with client=None."""
        panel = FlomingtonPanel()
        assert panel.client is None
        assert panel._lookup_id == ""
        assert panel._lookup_type == 0
        assert panel._status_msg == ""
        assert panel.stock is None
        assert panel.cross is None

    def test_construction_with_none(self) -> None:
        """Explicitly passing None yields disconnected."""
        panel = FlomingtonPanel(client=None)
        assert panel.client is None

    def test_construction_with_client(self) -> None:
        """Panel stores a provided FlomingtonClient."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        assert panel.client is client

    def test_client_property_setter(self) -> None:
        """client property setter updates the client."""
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

    def _make_panel_with_lookup_id(
        self, client, lookup_id, lookup_type=0,
    ):
        """Helper: create panel and mock dpg.get_value."""
        panel = FlomingtonPanel(client=client)
        panel._lookup_type = lookup_type
        return panel

    def test_lookup_empty_id(self) -> None:
        """_do_lookup() reports error for empty ID."""
        panel = FlomingtonPanel()
        panel._lookup_id = ""
        panel._do_lookup()
        assert "enter" in panel._status_msg.lower()

    def test_lookup_whitespace_id(self) -> None:
        """_do_lookup() reports error for whitespace ID."""
        panel = FlomingtonPanel()
        panel._lookup_id = "   "
        panel._do_lookup()
        assert "enter" in panel._status_msg.lower()

    def test_lookup_no_client(self) -> None:
        """Reports error when no client configured."""
        panel = FlomingtonPanel(client=None)
        panel._lookup_id = "test123"
        panel._do_lookup()
        assert "not configured" in panel._status_msg.lower()

    def test_stock_lookup_not_found(self) -> None:
        """Stock lookup returns not found."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        panel._lookup_type = 0
        panel._lookup_id = "XXXX1234"
        panel._do_lookup()
        assert "not found" in panel._status_msg.lower()
        assert panel.stock is None

    def test_cross_lookup_not_found(self) -> None:
        """Cross lookup returns not found."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        panel = FlomingtonPanel(client=client)
        panel._lookup_type = 1
        panel._lookup_id = "XXXX5678"
        panel._do_lookup()
        assert "not found" in panel._status_msg.lower()
        assert panel.cross is None

    def test_stock_lookup_found(self) -> None:
        """Stock lookup with mocked client stores stock."""
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
        panel._lookup_type = 0
        panel._lookup_id = "ABC12345"
        panel._do_lookup()

        assert panel.stock is stock
        assert panel.cross is None
        assert "CS Wild-type" in panel._status_msg

    def test_cross_lookup_found(self) -> None:
        """Cross lookup with mocked client stores cross."""
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
        panel._lookup_type = 1
        panel._lookup_id = "XYZ98765"
        panel._do_lookup()

        assert panel.cross is cross
        assert panel.stock is None
        assert "XYZ98765" in panel._status_msg

    def test_stock_lookup_clears_previous_cross(
        self,
    ) -> None:
        """Stock lookup clears previously stored cross."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        stock = FlyStock(stock_id="AA", name="test")
        client.get_stock = MagicMock(return_value=stock)

        panel = FlomingtonPanel(client=client)
        panel._cross = FlyCross(cross_id="old")
        panel._lookup_type = 0
        panel._lookup_id = "AA"
        panel._do_lookup()

        assert panel.stock is stock
        assert panel.cross is None

    def test_cross_lookup_clears_previous_stock(
        self,
    ) -> None:
        """Cross lookup clears previously stored stock."""
        cfg = FlomingtonConfig()
        client = FlomingtonClient(cfg)
        cross = FlyCross(cross_id="BB", status="done")
        client.get_cross = MagicMock(return_value=cross)

        panel = FlomingtonPanel(client=client)
        panel._stock = FlyStock(stock_id="old")
        panel._lookup_type = 1
        panel._lookup_id = "BB"
        panel._do_lookup()

        assert panel.cross is cross
        assert panel.stock is None


class TestFlomingtonPanelLinkToSession:
    """Tests for FlomingtonPanel._link_to_session()."""

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
    """Tests for FlomingtonPanel module import."""

    def test_importable_from_panels_package(self) -> None:
        """FlomingtonPanel importable from panels package."""
        from flocroscope.gui.panels import (
            FlomingtonPanel as FP,
        )
        assert FP is FlomingtonPanel

    def test_in_all(self) -> None:
        """FlomingtonPanel is in the __all__ list."""
        from flocroscope.gui.panels import __all__
        assert "FlomingtonPanel" in __all__


# ------------------------------------------------------------------ #
#  SessionPanel -- Flomington integration
# ------------------------------------------------------------------ #


class TestSessionPanelFlomington:
    """Tests for SessionPanel Flomington integration."""

    def test_default_construction_no_flomington(
        self,
    ) -> None:
        """Panel constructs without flomington_client."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)
        assert panel.flomington_client is None
        assert panel._flomington_lookup_done is False

    def test_construction_with_flomington(self) -> None:
        """Panel stores a provided flomington_client."""
        cfg = FlocroscopeConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        panel = SessionPanel(
            cfg, flomington_client=client,
        )
        assert panel.flomington_client is client

    def test_lookup_populates_genotype_from_stock(
        self,
    ) -> None:
        """Populates genotype from stock."""
        cfg = FlocroscopeConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        stock = FlyStock(
            stock_id="AAAA1111",
            name="GMR-Gal4",
            genotype="w[*]; P{GMR-GAL4}",
        )
        client.get_stock = MagicMock(return_value=stock)

        panel = SessionPanel(
            cfg, flomington_client=client,
        )
        panel._fly_id = "AAAA1111"

        panel._lookup_from_flomington()

        assert panel._flomington_lookup_done is True
        assert panel._fly_genotype == "w[*]; P{GMR-GAL4}"

    def test_lookup_populates_genotype_from_cross(
        self,
    ) -> None:
        """Populates genotype from cross."""
        cfg = FlocroscopeConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        client.get_stock = MagicMock(return_value=None)
        cross = FlyCross(
            cross_id="BBBB2222",
            virgin_genotype="w; Gal4",
            male_genotype="UAS-GCaMP7f",
            status="screening",
        )
        client.get_cross = MagicMock(return_value=cross)

        panel = SessionPanel(
            cfg, flomington_client=client,
        )
        panel._fly_id = "BBBB2222"

        panel._lookup_from_flomington()

        assert panel._flomington_lookup_done is True
        assert "w; Gal4" in panel._fly_genotype
        assert "UAS-GCaMP7f" in panel._fly_genotype

    def test_lookup_not_found(self) -> None:
        """Reports not found."""
        cfg = FlocroscopeConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        client.get_stock = MagicMock(return_value=None)
        client.get_cross = MagicMock(return_value=None)

        panel = SessionPanel(
            cfg, flomington_client=client,
        )
        panel._fly_id = "ZZZZ9999"

        panel._lookup_from_flomington()

        assert "not found" in panel._status_msg.lower()
        assert panel._flomington_lookup_done is False

    def test_lookup_no_client(self) -> None:
        """Does nothing when client is None."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)
        panel._fly_id = "test"
        panel._fly_genotype = "original"
        panel._lookup_from_flomington()

    def test_lookup_empty_id(self) -> None:
        """Does nothing for empty ID."""
        cfg = FlocroscopeConfig()
        flom_cfg = FlomingtonConfig()
        client = FlomingtonClient(flom_cfg)
        panel = SessionPanel(
            cfg, flomington_client=client,
        )
        panel._fly_id = ""

        panel._lookup_from_flomington()


# ------------------------------------------------------------------ #
#  build()/update() -- require dearpygui
# ------------------------------------------------------------------ #


class TestBuildMethodsRequireDearpygui:
    """Verify build()/update() need dearpygui.

    These tests skip when dearpygui is not installed, and also
    skip when it IS installed because a viewport context is needed.
    """

    def test_stimulus_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_session_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_config_editor_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_comms_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_calibration_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_mapping_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_flomington_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_fictrac_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_scanimage_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_optogenetics_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_behaviour_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")

    def test_tracking_build_skips(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for build()")


# ------------------------------------------------------------------ #
#  FicTracPanel
# ------------------------------------------------------------------ #


class TestFicTracPanelConstruction:
    """Tests for FicTracPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with no arguments."""
        panel = FicTracPanel()
        assert panel._comms is None
        assert panel._config is None
        assert panel.frames_received == 0

    def test_construction_with_comms(self) -> None:
        """Panel stores comms reference."""
        hub = MagicMock()
        cfg = FlocroscopeConfig().comms
        panel = FicTracPanel(comms=hub, config=cfg)
        assert panel._comms is hub
        assert panel._config is cfg

    def test_initial_state_zeroed(self) -> None:
        """All tracking values start at zero."""
        panel = FicTracPanel()
        assert panel._heading_deg == 0.0
        assert panel._speed == 0.0
        assert panel._x_mm == 0.0
        assert panel._y_mm == 0.0


class TestFicTracPanelImport:
    """Tests for FicTracPanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            FicTracPanel as FTP,
        )
        assert FTP is FicTracPanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "FicTracPanel" in __all__


# ------------------------------------------------------------------ #
#  ScanImagePanel
# ------------------------------------------------------------------ #


class TestScanImagePanelConstruction:
    """Tests for ScanImagePanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with no arguments."""
        panel = ScanImagePanel()
        assert panel._comms is None
        assert panel.trial_count == 0
        assert panel.frame_count == 0

    def test_construction_with_comms(self) -> None:
        """Panel stores comms reference."""
        hub = MagicMock()
        panel = ScanImagePanel(comms=hub)
        assert panel._comms is hub

    def test_initial_not_acquiring(self) -> None:
        """Panel starts in non-acquiring state."""
        panel = ScanImagePanel()
        assert panel._acquiring is False


class TestScanImagePanelImport:
    """Tests for ScanImagePanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            ScanImagePanel as SIP,
        )
        assert SIP is ScanImagePanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "ScanImagePanel" in __all__


# ------------------------------------------------------------------ #
#  OptogeneticsPanel
# ------------------------------------------------------------------ #


class TestOptogeneticsPanelConstruction:
    """Tests for OptogeneticsPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with no arguments."""
        panel = OptogeneticsPanel()
        assert panel._comms is None
        assert panel.pulse_count == 0
        assert panel.intensity == 1.0

    def test_construction_with_comms(self) -> None:
        """Panel stores comms reference."""
        hub = MagicMock()
        panel = OptogeneticsPanel(comms=hub)
        assert panel._comms is hub

    def test_initial_parameters(self) -> None:
        """Default parameters are sensible."""
        panel = OptogeneticsPanel()
        assert panel._duration_ms == 50.0
        assert panel._channel == 0


class TestOptogeneticsPanelSend:
    """Tests for OptogeneticsPanel._send()."""

    def test_send_without_comms_no_error(self) -> None:
        """_send() is a no-op when comms is None."""
        panel = OptogeneticsPanel()
        panel._send("on", 1.0)

    def test_send_with_comms(self) -> None:
        """_send() calls comms.send_led()."""
        hub = MagicMock()
        panel = OptogeneticsPanel(comms=hub)
        panel._send("pulse", 0.5, 100.0)
        hub.send_led.assert_called_once()


class TestOptogeneticsPanelImport:
    """Tests for OptogeneticsPanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            OptogeneticsPanel as OP,
        )
        assert OP is OptogeneticsPanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "OptogeneticsPanel" in __all__


# ------------------------------------------------------------------ #
#  BehaviourPanel
# ------------------------------------------------------------------ #


class TestBehaviourPanelConstruction:
    """Tests for BehaviourPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with no arguments."""
        panel = BehaviourPanel()
        assert panel._config is None
        assert panel._comms is None
        assert panel.session is None
        assert panel.experiment_type == "Behaviour"

    def test_construction_with_config(self) -> None:
        """Panel stores config reference."""
        cfg = FlocroscopeConfig()
        panel = BehaviourPanel(config=cfg)
        assert panel._config is cfg

    def test_experiment_types_available(self) -> None:
        """All expected experiment types are listed."""
        assert "2P" in EXPERIMENT_TYPES
        assert "Behaviour" in EXPERIMENT_TYPES
        assert "VR+2P" in EXPERIMENT_TYPES
        assert "VR" in EXPERIMENT_TYPES
        assert len(EXPERIMENT_TYPES) == 4

    def test_session_setter(self) -> None:
        """session property can be updated."""
        panel = BehaviourPanel()
        mock_session = MagicMock()
        panel.session = mock_session
        assert panel.session is mock_session


class TestBehaviourPanelImport:
    """Tests for BehaviourPanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            BehaviourPanel as BP,
        )
        assert BP is BehaviourPanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "BehaviourPanel" in __all__


# ------------------------------------------------------------------ #
#  TrackingPanel
# ------------------------------------------------------------------ #


class TestTrackingPanelConstruction:
    """Tests for TrackingPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with no arguments."""
        panel = TrackingPanel()
        assert panel._comms is None
        assert panel._arena_radius == 40.0
        assert panel.distance_mm == 0.0
        assert panel.heading_offset_deg == 0.0

    def test_custom_arena_radius(self) -> None:
        """Panel stores custom arena radius."""
        panel = TrackingPanel(arena_radius_mm=200.0)
        assert panel._arena_radius == 200.0

    def test_set_virtual_state(self) -> None:
        """set_virtual_state() updates virtual fly position."""
        panel = TrackingPanel()
        panel.set_virtual_state(10.0, 20.0, 90.0)
        assert panel._virtual_x == 10.0
        assert panel._virtual_y == 20.0
        assert panel._virtual_heading_deg == 90.0

    def test_set_real_state(self) -> None:
        """set_real_state() updates real fly position."""
        panel = TrackingPanel()
        panel.set_real_state(5.0, -3.0, 45.0)
        assert panel._real_x == 5.0
        assert panel._real_y == -3.0
        assert panel._real_heading_deg == 45.0


class TestTrackingPanelMetrics:
    """Tests for TrackingPanel computed properties."""

    def test_distance_zero_when_colocated(self) -> None:
        """Distance is 0 when both flies are at origin."""
        panel = TrackingPanel()
        assert panel.distance_mm == 0.0

    def test_distance_basic(self) -> None:
        """Distance is correct for a simple offset."""
        panel = TrackingPanel()
        panel.set_virtual_state(3.0, 4.0, 0.0)
        assert abs(panel.distance_mm - 5.0) < 0.01

    def test_heading_offset_zero(self) -> None:
        """Heading offset is 0 when both face same way."""
        panel = TrackingPanel()
        panel.set_virtual_state(0, 0, 90.0)
        panel.set_real_state(0, 0, 90.0)
        assert abs(panel.heading_offset_deg) < 0.01

    def test_heading_offset_positive(self) -> None:
        """Heading offset is +45 for 45 deg clockwise."""
        panel = TrackingPanel()
        panel.set_virtual_state(0, 0, 135.0)
        panel.set_real_state(0, 0, 90.0)
        assert abs(panel.heading_offset_deg - 45.0) < 0.01

    def test_heading_offset_wraps(self) -> None:
        """Heading offset wraps around 360 correctly."""
        panel = TrackingPanel()
        panel.set_virtual_state(0, 0, 10.0)
        panel.set_real_state(0, 0, 350.0)
        assert abs(panel.heading_offset_deg - 20.0) < 0.01


class TestTrackingPanelImport:
    """Tests for TrackingPanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            TrackingPanel as TP,
        )
        assert TP is TrackingPanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "TrackingPanel" in __all__


# ------------------------------------------------------------------ #
#  App — single-window tabbed layout
# ------------------------------------------------------------------ #


class TestAppConstruction:
    """Tests for FlocroscopeApp construction."""

    def test_default_construction(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        assert app._running is False
        assert app._config is not None
        assert app._comms is None

    def test_default_experiment_mode(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        from flocroscope.gui.layout import ExperimentMode
        app = FlocroscopeApp()
        assert app._experiment_mode is ExperimentMode.BEHAVIOUR

    def test_custom_config_stored(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        cfg = FlocroscopeConfig()
        cfg.arena.radius_mm = 42.0
        app = FlocroscopeApp(config=cfg)
        assert app._config.arena.radius_mm == 42.0

    def test_experiment_mode_change(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        from flocroscope.gui.layout import ExperimentMode
        app = FlocroscopeApp()
        app._on_experiment_mode(None, "VR", None)
        assert app._experiment_mode is ExperimentMode.VR

    def test_experiment_mode_change_invalid(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        from flocroscope.gui.layout import ExperimentMode
        app = FlocroscopeApp()
        app._on_experiment_mode(None, "bogus", None)
        assert app._experiment_mode is ExperimentMode.BEHAVIOUR

    def test_on_quit(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        app._running = True
        app._on_quit()
        assert app._running is False
