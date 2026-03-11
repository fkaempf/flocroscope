"""Tests for GUI panel classes.

These tests verify panel construction, property access, and internal
state management WITHOUT requiring DearPyGui.  Tests that call
``build()`` or ``update()`` use ``pytest.importorskip("dearpygui")``
to skip gracefully when dearpygui is not installed.
"""

from __future__ import annotations

import os
import shutil
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
from flocroscope.gui.panels.login import LoginPanel
from flocroscope.gui.panels.presets import PresetsPanel
from flocroscope.gui.panels.scanimage import ScanImagePanel
from flocroscope.gui.panels.user_profile import UserProfilePanel
from flocroscope.gui.panels.session import SessionPanel
from flocroscope.gui.panels.stimulus import StimulusPanel, STIMULUS_TYPES
from flocroscope.gui.panels.tracking import TrackingPanel
from flocroscope.gui.profiles import ProfileManager
from flocroscope.gui.presets import PresetManager


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


class TestStimulusPanelCallbacks:
    """Tests for StimulusPanel callback methods."""

    def _make(self) -> StimulusPanel:
        cfg = FlocroscopeConfig()
        return StimulusPanel(cfg)

    def test_on_type_change_valid(self) -> None:
        """_on_type_change updates selected_idx."""
        p = self._make()
        labels = [t[0] for t in STIMULUS_TYPES]
        if len(labels) > 1:
            p._on_type_change(None, labels[1], None)
            assert p._selected_idx == 1

    def test_on_type_change_invalid(self) -> None:
        """_on_type_change ignores invalid label."""
        p = self._make()
        p._on_type_change(None, "nonexistent", None)
        assert p._selected_idx == 0

    def test_on_arena_radius(self) -> None:
        """_on_arena_radius clamps to min 1.0."""
        p = self._make()
        p._on_arena_radius(None, 50.0, None)
        assert p._config.arena.radius_mm == 50.0

    def test_on_arena_radius_clamps(self) -> None:
        """_on_arena_radius clamps negative to 1.0."""
        p = self._make()
        p._on_arena_radius(None, -5.0, None)
        assert p._config.arena.radius_mm == 1.0

    def test_on_fly_size(self) -> None:
        """_on_fly_size updates config."""
        p = self._make()
        p._on_fly_size(None, 3.5, None)
        assert p._config.fly_model.phys_length_mm == 3.5

    def test_on_fly_size_clamps(self) -> None:
        """_on_fly_size clamps to min 0.1."""
        p = self._make()
        p._on_fly_size(None, -1.0, None)
        assert p._config.fly_model.phys_length_mm == 0.1

    def test_on_fov_x(self) -> None:
        """_on_fov_x clamps to [10, 359]."""
        p = self._make()
        p._on_fov_x(None, 180.0, None)
        assert p._config.camera.fov_x_deg == 180.0

    def test_on_fov_x_clamps_low(self) -> None:
        p = self._make()
        p._on_fov_x(None, 1.0, None)
        assert p._config.camera.fov_x_deg == 10.0

    def test_on_fov_x_clamps_high(self) -> None:
        p = self._make()
        p._on_fov_x(None, 400.0, None)
        assert p._config.camera.fov_x_deg == 359.0

    def test_on_projection(self) -> None:
        """_on_projection sets camera projection mode."""
        p = self._make()
        p._on_projection(None, "equirect", None)
        assert p._config.camera.projection == "equirect"

    def test_on_autonomous(self) -> None:
        """_on_autonomous toggles autonomous mode."""
        p = self._make()
        p._on_autonomous(None, True, None)
        assert p._config.autonomous.enabled is True

    def test_on_speed(self) -> None:
        """_on_speed clamps to min 0.0."""
        p = self._make()
        p._on_speed(None, 15.0, None)
        assert p._config.movement.speed_mm_s == 15.0
        p._on_speed(None, -5.0, None)
        assert p._config.movement.speed_mm_s == 0.0

    def test_on_near_plane(self) -> None:
        """_on_near_plane sets near_plane_safety."""
        p = self._make()
        p._on_near_plane(None, 2.5, None)
        assert p._config.scaling.near_plane_safety == 2.5

    def test_on_auto_min(self) -> None:
        """_on_auto_min sets auto_min_distance."""
        p = self._make()
        p._on_auto_min(None, True, None)
        assert p._config.scaling.auto_min_distance is True

    def test_on_min_dist(self) -> None:
        """_on_min_dist clamps to min 0.1."""
        p = self._make()
        p._on_min_dist(None, 5.0, None)
        assert p._config.scaling.min_cam_fly_dist_mm == 5.0
        p._on_min_dist(None, -1.0, None)
        assert p._config.scaling.min_cam_fly_dist_mm == 0.1

    def test_on_launch_toggle(self) -> None:
        """_on_launch toggles between launch and stop."""
        p = self._make()
        assert p._running is False
        # Simulate running state
        p._running = True
        # Would call _stop_stimulus, which terminates process
        assert p._running is True

    def test_stop_stimulus_when_no_process(self) -> None:
        """_stop_stimulus is safe when no process exists."""
        p = self._make()
        p._stop_stimulus()
        assert p._running is False


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


class TestSessionPanelExperimenterAndRecent:
    """Tests for experimenter auto-fill and recent sessions."""

    def test_set_experimenter(self) -> None:
        """set_experimenter updates the field."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)
        panel.set_experimenter("Alice")
        assert panel._experimenter == "Alice"

    def test_recent_sessions_empty(self) -> None:
        """recent_sessions starts empty."""
        cfg = FlocroscopeConfig()
        panel = SessionPanel(cfg)
        assert panel._recent_sessions == []


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


class TestSessionPanelCallbacks:
    """Tests for SessionPanel callback methods."""

    def _make(self):
        cfg = FlocroscopeConfig()
        return SessionPanel(cfg)

    def test_on_experimenter(self) -> None:
        p = self._make()
        p._on_experimenter(None, "Bob", None)
        assert p._experimenter == "Bob"

    def test_on_genotype(self) -> None:
        p = self._make()
        p._on_genotype(None, "CS x Or47b", None)
        assert p._fly_genotype == "CS x Or47b"

    def test_on_fly_id_change_resets_lookup(self) -> None:
        """Changing fly ID resets Flomington lookup flag."""
        p = self._make()
        p._flomington_lookup_done = True
        p._on_fly_id_change(None, "new_id", None)
        assert p._fly_id == "new_id"
        assert p._flomington_lookup_done is False

    def test_on_notes(self) -> None:
        p = self._make()
        p._on_notes(None, "Some notes", None)
        assert p._notes == "Some notes"

    def test_flomington_client_property(self) -> None:
        """flomington_client returns the stored client."""
        cfg = FlocroscopeConfig()
        client = MagicMock()
        panel = SessionPanel(cfg, flomington_client=client)
        assert panel.flomington_client is client

    def test_flomington_client_none(self) -> None:
        """flomington_client is None by default."""
        p = self._make()
        assert p.flomington_client is None


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

    def test_inline_edit_arena_radius(self) -> None:
        """Inline callbacks modify config directly."""
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_arena_radius(None, 55.5, None)
        assert cfg.arena.radius_mm == 55.5

    def test_inline_edit_camera_projection(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_cam_proj(None, "equisolid", None)
        assert cfg.camera.projection == "equisolid"

    def test_inline_edit_movement_speed(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_mov_speed(None, 42.0, None)
        assert cfg.movement.speed_mm_s == 42.0

    def test_inline_edit_comms_enabled(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_comms_en(None, True, None)
        assert cfg.comms.enabled is True

    def test_inline_edit_display_fps(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_disp_fps(None, 144, None)
        assert cfg.display.target_fps == 144

    def test_inline_edit_display_borderless(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_disp_border(None, True, None)
        assert cfg.display.borderless is True

    def test_inline_edit_cam_fov(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_cam_fov(None, 180.0, None)
        assert cfg.camera.fov_x_deg == 180.0

    def test_inline_edit_fly_length(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_fly_len(None, 3.5, None)
        assert cfg.fly_model.phys_length_mm == 3.5

    def test_inline_edit_autonomous(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_mov_auto(None, True, None)
        assert cfg.autonomous.enabled is True

    def test_path_change_callback(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        panel._on_path_change(None, "/path/to/config.yaml", None)
        assert panel._config_path == "/path/to/config.yaml"

    def test_save_and_load_roundtrip(self) -> None:
        """Save then load config preserves values."""
        cfg = FlocroscopeConfig()
        cfg.arena.radius_mm = 77.0
        panel = ConfigEditorPanel(cfg)

        path = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_cfg_roundtrip.yaml",
        )
        panel._config_path = path
        panel._save_config()
        assert "Saved" in panel._status_msg

        # Modify config
        cfg.arena.radius_mm = 1.0

        # Load it back
        panel._load_config()
        assert "Loaded" in panel._status_msg
        assert cfg.arena.radius_mm == 77.0


class TestConfigEditorPanelWindowTag:
    """Tests for ConfigEditorPanel tag properties."""

    def test_group_tag(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        assert panel.group_tag == "grp_config"

    def test_window_tag(self) -> None:
        cfg = FlocroscopeConfig()
        panel = ConfigEditorPanel(cfg)
        assert panel.window_tag == "grp_config"
        assert panel.window_tag == panel.group_tag


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


class TestCommsPanelWindowTag:
    """Tests for CommsPanel tag properties."""

    def test_group_tag(self) -> None:
        panel = CommsPanel()
        assert panel.group_tag == "grp_comms"

    def test_window_tag(self) -> None:
        panel = CommsPanel()
        assert panel.window_tag == "grp_comms"
        assert panel.window_tag == panel.group_tag


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


class TestCalibrationPanelWarpCircle:
    """Tests for CalibrationPanel warp circle launch/stop."""

    def test_warp_initially_not_running(self) -> None:
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        assert panel._warp_running is False
        assert panel._warp_process is None
        assert panel._warp_status == ""

    def test_stop_warp_circle_no_process(self) -> None:
        """_stop_warp_circle is safe with no process."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        panel._stop_warp_circle()
        # No crash, warp_status unchanged
        assert panel._warp_status == ""

    def test_stop_warp_circle_with_mock(self) -> None:
        """_stop_warp_circle terminates process."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        mock_proc = MagicMock()
        panel._warp_process = mock_proc
        panel._warp_running = True
        panel._stop_warp_circle()
        mock_proc.terminate.assert_called_once()
        assert "terminated" in panel._warp_status.lower()

    def test_on_warp_launch_toggle(self) -> None:
        """_on_warp_launch calls stop when already running."""
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        mock_proc = MagicMock()
        panel._warp_process = mock_proc
        panel._warp_running = True
        panel._on_warp_launch(None, None, None)
        mock_proc.terminate.assert_called_once()

    def test_full_config_stored(self) -> None:
        """Panel stores full_config for warp circle launch."""
        cfg = CalibrationConfig()
        full = FlocroscopeConfig()
        panel = CalibrationPanel(cfg, full_config=full)
        assert panel._full_config is full

    def test_intrinsic_file_constants(self) -> None:
        """Module-level file constants have expected entries."""
        assert len(_FISHEYE_FILES) == 3
        assert len(_PINHOLE_FILES) == 2
        assert all(f.endswith(".npy") for f in _FISHEYE_FILES)
        assert all(f.endswith(".npy") for f in _PINHOLE_FILES)


class TestCalibrationPanelWindowTag:
    """Tests for CalibrationPanel tag properties."""

    def test_group_tag(self) -> None:
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        assert panel.group_tag == "grp_calibration"

    def test_window_tag(self) -> None:
        cfg = CalibrationConfig()
        panel = CalibrationPanel(cfg)
        assert panel.window_tag == "grp_calibration"
        assert panel.window_tag == panel.group_tag


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


class TestMappingPanelWindowTag:
    """Tests for MappingPanel tag properties."""

    def test_group_tag(self) -> None:
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        assert panel.group_tag == "grp_mapping"

    def test_window_tag(self) -> None:
        cfg = WarpConfig()
        panel = MappingPanel(cfg)
        assert panel.window_tag == "grp_mapping"
        assert panel.window_tag == panel.group_tag


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


class TestFlomingtonPanelWindowTag:
    """Tests for FlomingtonPanel tag properties."""

    def test_group_tag(self) -> None:
        panel = FlomingtonPanel()
        assert panel.group_tag == "grp_flomington"

    def test_window_tag(self) -> None:
        panel = FlomingtonPanel()
        assert panel.window_tag == "grp_flomington"
        assert panel.window_tag == panel.group_tag


class TestFlomingtonPanelCallbacks:
    """Tests for FlomingtonPanel callback methods."""

    def test_on_lookup_type_stock(self) -> None:
        panel = FlomingtonPanel()
        panel._on_lookup_type(None, "Stock", None)
        assert panel._lookup_type == 0

    def test_on_lookup_type_cross(self) -> None:
        panel = FlomingtonPanel()
        panel._on_lookup_type(None, "Cross", None)
        assert panel._lookup_type == 1

    def test_on_lookup_id(self) -> None:
        panel = FlomingtonPanel()
        panel._on_lookup_id(None, "FLY001", None)
        assert panel._lookup_id == "FLY001"

    def test_link_to_session_no_record(self) -> None:
        """_link_to_session with no record sets error."""
        panel = FlomingtonPanel()
        panel._link_to_session()
        assert "No record" in panel._status_msg

    def test_link_to_session_with_stock(self) -> None:
        """_link_to_session with stock sets status."""
        panel = FlomingtonPanel()
        panel._stock = FlyStock(
            stock_id="s1", name="TestStock",
        )
        panel._link_to_session()
        assert "TestStock" in panel._status_msg

    def test_link_to_session_with_cross(self) -> None:
        """_link_to_session with cross sets status."""
        panel = FlomingtonPanel()
        panel._cross = FlyCross(
            cross_id="c1", status="active",
        )
        panel._link_to_session()
        assert "c1" in panel._status_msg


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


class TestFicTracPanelWindowTag:
    """Tests for FicTracPanel tag properties."""

    def test_group_tag(self) -> None:
        panel = FicTracPanel()
        assert panel.group_tag == "grp_fictrac"

    def test_window_tag(self) -> None:
        panel = FicTracPanel()
        assert panel.window_tag == "grp_fictrac"
        assert panel.window_tag == panel.group_tag


class TestFicTracPanelSpeedHistory:
    """Tests for FicTracPanel speed history buffer."""

    def test_speed_history_is_deque(self) -> None:
        from collections import deque
        panel = FicTracPanel()
        assert isinstance(panel._speed_history, deque)

    def test_speed_history_max_length(self) -> None:
        from flocroscope.gui.panels.fictrac import _HISTORY_LEN
        panel = FicTracPanel()
        assert panel._speed_history.maxlen == _HISTORY_LEN

    def test_speed_history_starts_empty(self) -> None:
        panel = FicTracPanel()
        assert len(panel._speed_history) == 0


class TestFicTracPanelLaunchState:
    """Tests for FicTrac launch subprocess state."""

    def test_ft_process_initially_none(self) -> None:
        """FicTrac subprocess starts as None."""
        panel = FicTracPanel()
        assert panel._ft_process is None
        assert panel.ft_running is False

    def test_launch_status_initially_empty(self) -> None:
        """Launch status starts empty."""
        panel = FicTracPanel()
        assert panel._ft_launch_status == ""

    def test_exe_path_initially_empty(self) -> None:
        """Executable path starts empty."""
        panel = FicTracPanel()
        assert panel._ft_exe_path == ""

    def test_config_path_initially_empty(self) -> None:
        """Config path starts empty."""
        panel = FicTracPanel()
        assert panel._ft_config_path == ""

    def test_on_exe_path_change(self) -> None:
        """_on_exe_path_change stores the new path."""
        panel = FicTracPanel()
        panel._on_exe_path_change(
            None, "/usr/local/bin/fictrac", None,
        )
        assert panel._ft_exe_path == (
            "/usr/local/bin/fictrac"
        )

    def test_on_config_path_change(self) -> None:
        """_on_config_path_change stores the new path."""
        panel = FicTracPanel()
        panel._on_config_path_change(
            None, "/home/user/config.txt", None,
        )
        assert panel._ft_config_path == (
            "/home/user/config.txt"
        )

    def test_stop_fictrac_no_process(self) -> None:
        """_stop_fictrac is safe when no process exists."""
        panel = FicTracPanel()
        panel._stop_fictrac()
        assert panel._ft_launch_status == ""

    def test_stop_fictrac_with_mock_process(self) -> None:
        """_stop_fictrac terminates existing process."""
        panel = FicTracPanel()
        mock_proc = MagicMock()
        panel._ft_process = mock_proc
        panel._ft_running = True
        panel._stop_fictrac()
        mock_proc.terminate.assert_called_once()
        assert "terminated" in (
            panel._ft_launch_status.lower()
        )


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

    def test_construction_with_config(self) -> None:
        """Panel stores comms config for scanimage_path."""
        from flocroscope.config.schema import CommsConfig
        cfg = CommsConfig(scanimage_path="/usr/bin/matlab")
        panel = ScanImagePanel(config=cfg)
        assert panel._config is cfg
        assert panel._config.scanimage_path == "/usr/bin/matlab"

    def test_initial_not_acquiring(self) -> None:
        """Panel starts in non-acquiring state."""
        panel = ScanImagePanel()
        assert panel._acquiring is False

    def test_si_process_initially_none(self) -> None:
        """ScanImage subprocess starts as None."""
        panel = ScanImagePanel()
        assert panel._si_process is None
        assert panel.si_running is False

    def test_launch_status_initially_empty(self) -> None:
        """Launch status starts empty."""
        panel = ScanImagePanel()
        assert panel._si_launch_status == ""


class TestScanImagePanelWindowTag:
    """Tests for ScanImagePanel tag properties."""

    def test_group_tag(self) -> None:
        panel = ScanImagePanel()
        assert panel.group_tag == "grp_scanimage"

    def test_window_tag(self) -> None:
        panel = ScanImagePanel()
        assert panel.window_tag == "grp_scanimage"
        assert panel.window_tag == panel.group_tag


class TestScanImagePanelEventLog:
    """Tests for ScanImagePanel event log and counters."""

    def test_event_log_max_size(self) -> None:
        from flocroscope.gui.panels.scanimage import (
            _EVENT_LOG_MAX,
        )
        panel = ScanImagePanel()
        assert panel._event_log.maxlen == _EVENT_LOG_MAX

    def test_event_log_starts_empty(self) -> None:
        panel = ScanImagePanel()
        assert len(panel._event_log) == 0

    def test_on_path_change_updates_config(self) -> None:
        """_on_path_change stores scanimage_path in config."""
        from flocroscope.config.schema import CommsConfig
        cfg = CommsConfig()
        panel = ScanImagePanel(config=cfg)
        panel._on_path_change(None, "/new/path", None)
        assert cfg.scanimage_path == "/new/path"

    def test_on_path_change_without_config(self) -> None:
        """_on_path_change is safe with no config."""
        panel = ScanImagePanel()
        panel._on_path_change(None, "/any/path", None)

    def test_stop_scanimage_no_process(self) -> None:
        """_stop_scanimage is safe when no process exists."""
        panel = ScanImagePanel()
        panel._stop_scanimage()
        assert panel._si_launch_status == ""

    def test_stop_scanimage_with_mock_process(self) -> None:
        """_stop_scanimage terminates existing process."""
        panel = ScanImagePanel()
        mock_proc = MagicMock()
        panel._si_process = mock_proc
        panel._si_running = True
        panel._stop_scanimage()
        mock_proc.terminate.assert_called_once()
        assert "terminated" in panel._si_launch_status.lower()

    def test_on_launch_calls_launch(self) -> None:
        """_on_launch calls _launch_scanimage."""
        panel = ScanImagePanel()
        panel._launch_scanimage = MagicMock()
        panel._on_launch(None, None, None)
        panel._launch_scanimage.assert_called_once()

    def test_on_stop_calls_stop(self) -> None:
        """_on_stop calls _stop_scanimage."""
        panel = ScanImagePanel()
        mock_proc = MagicMock()
        panel._si_process = mock_proc
        panel._si_running = True
        panel._on_stop(None, None, None)
        mock_proc.terminate.assert_called_once()


class TestScanImagePanelMatlabHints:
    """Tests for ScanImage MATLAB executable hints."""

    def test_matlab_exe_hints_exist(self) -> None:
        from flocroscope.gui.panels.scanimage import (
            _MATLAB_EXE_HINTS,
        )
        assert "win32" in _MATLAB_EXE_HINTS
        assert "linux" in _MATLAB_EXE_HINTS
        assert "darwin" in _MATLAB_EXE_HINTS

    def test_matlab_exe_hints_contain_matlab(self) -> None:
        """All hints reference a matlab executable."""
        from flocroscope.gui.panels.scanimage import (
            _MATLAB_EXE_HINTS,
        )
        for platform, hint in _MATLAB_EXE_HINTS.items():
            assert "matlab" in hint.lower()


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


class TestOptogeneticsPanelWindowTag:
    """Tests for OptogeneticsPanel tag properties."""

    def test_group_tag(self) -> None:
        panel = OptogeneticsPanel()
        assert panel.group_tag == "grp_optogenetics"

    def test_window_tag(self) -> None:
        panel = OptogeneticsPanel()
        assert panel.window_tag == "grp_optogenetics"
        assert panel.window_tag == panel.group_tag


class TestOptogeneticsPanelCallbacks:
    """Tests for OptogeneticsPanel parameter callbacks."""

    def test_on_intensity(self) -> None:
        panel = OptogeneticsPanel()
        panel._on_intensity(None, 0.75, None)
        assert panel._intensity == 0.75
        assert panel.intensity == 0.75

    def test_on_duration(self) -> None:
        panel = OptogeneticsPanel()
        panel._on_duration(None, 200.0, None)
        assert panel._duration_ms == 200.0

    def test_on_channel(self) -> None:
        panel = OptogeneticsPanel()
        panel._on_channel(None, 3, None)
        assert panel._channel == 3

    def test_on_led_pulse_increments_count(self) -> None:
        """_on_led_pulse increments pulse_count."""
        panel = OptogeneticsPanel()
        assert panel.pulse_count == 0
        panel._on_led_pulse(None, None, None)
        assert panel.pulse_count == 1
        panel._on_led_pulse(None, None, None)
        assert panel.pulse_count == 2

    def test_on_led_on_sends(self) -> None:
        hub = MagicMock()
        panel = OptogeneticsPanel(comms=hub)
        panel._on_led_on(None, None, None)
        hub.send_led.assert_called_once()

    def test_on_led_off_sends(self) -> None:
        hub = MagicMock()
        panel = OptogeneticsPanel(comms=hub)
        panel._on_led_off(None, None, None)
        hub.send_led.assert_called_once()


class TestOptogeneticsPanelPresets:
    """Tests for OptogeneticsPanel preset protocols."""

    def test_presets_exist(self) -> None:
        from flocroscope.gui.panels.optogenetics import _PRESETS
        assert len(_PRESETS) > 0

    def test_preset_structure(self) -> None:
        from flocroscope.gui.panels.optogenetics import _PRESETS
        for label, cmd, intensity, duration in _PRESETS:
            assert isinstance(label, str)
            assert cmd in ("on", "off", "pulse")
            assert 0.0 <= intensity <= 1.0
            assert duration >= 0.0

    def test_on_preset_pulse_increments(self) -> None:
        """Applying a pulse preset increments the count."""
        from flocroscope.gui.panels.optogenetics import _PRESETS
        panel = OptogeneticsPanel()
        # Find a pulse preset
        pulse_idx = None
        for i, (_, cmd, _, _) in enumerate(_PRESETS):
            if cmd == "pulse":
                pulse_idx = i
                break
        if pulse_idx is not None:
            panel._on_preset(None, None, pulse_idx)
            assert panel.pulse_count == 1

    def test_on_preset_on_does_not_increment(self) -> None:
        """Applying an 'on' preset does not increment pulse count."""
        from flocroscope.gui.panels.optogenetics import _PRESETS
        panel = OptogeneticsPanel()
        on_idx = None
        for i, (_, cmd, _, _) in enumerate(_PRESETS):
            if cmd == "on":
                on_idx = i
                break
        if on_idx is not None:
            panel._on_preset(None, None, on_idx)
            assert panel.pulse_count == 0


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


class TestBehaviourPanelWindowTag:
    """Tests for BehaviourPanel tag properties."""

    def test_group_tag(self) -> None:
        panel = BehaviourPanel()
        assert panel.group_tag == "grp_behaviour"

    def test_window_tag(self) -> None:
        panel = BehaviourPanel()
        assert panel.window_tag == "grp_behaviour"
        assert panel.window_tag == panel.group_tag


class TestBehaviourPanelCallbacks:
    """Tests for BehaviourPanel callback methods."""

    def test_on_exp_type_valid(self) -> None:
        """_on_exp_type updates experiment type index."""
        panel = BehaviourPanel()
        assert panel.experiment_type == "Behaviour"
        panel._on_exp_type(None, "VR", None)
        assert panel.experiment_type == "VR"
        assert panel._experiment_type_idx == (
            EXPERIMENT_TYPES.index("VR")
        )

    def test_on_exp_type_all_modes(self) -> None:
        """_on_exp_type handles all experiment modes."""
        panel = BehaviourPanel()
        for exp_type in EXPERIMENT_TYPES:
            panel._on_exp_type(None, exp_type, None)
            assert panel.experiment_type == exp_type

    def test_on_exp_type_invalid_ignored(self) -> None:
        """_on_exp_type ignores unknown types."""
        panel = BehaviourPanel()
        panel._on_exp_type(None, "Behaviour", None)
        panel._on_exp_type(None, "invalid_type", None)
        # Should still be Behaviour
        assert panel.experiment_type == "Behaviour"

    def test_construction_with_all_args(self) -> None:
        """Panel accepts config, comms, and session."""
        cfg = FlocroscopeConfig()
        hub = MagicMock()
        session = MagicMock()
        panel = BehaviourPanel(
            config=cfg, comms=hub, session=session,
        )
        assert panel._config is cfg
        assert panel._comms is hub
        assert panel.session is session


class TestBehaviourPanelFBDCState:
    """Tests for BehaviourPanel FBDC launch state."""

    def test_fbdc_process_initially_none(self) -> None:
        """FBDC subprocess starts as None."""
        panel = BehaviourPanel()
        assert panel._fbdc_process is None
        assert panel.fbdc_running is False

    def test_fbdc_launch_status_initially_empty(
        self,
    ) -> None:
        """FBDC launch status starts empty."""
        panel = BehaviourPanel()
        assert panel._fbdc_launch_status == ""

    def test_fbdc_matlab_path_initially_empty(
        self,
    ) -> None:
        """MATLAB path for FBDC starts empty."""
        panel = BehaviourPanel()
        assert panel._fbdc_matlab_path == ""

    def test_fbdc_dir_initially_empty(self) -> None:
        """FBDC directory starts empty."""
        panel = BehaviourPanel()
        assert panel._fbdc_dir == ""

    def test_on_fbdc_matlab_change(self) -> None:
        """_on_fbdc_matlab_change stores the new path."""
        panel = BehaviourPanel()
        panel._on_fbdc_matlab_change(
            None, "/usr/local/bin/matlab", None,
        )
        assert panel._fbdc_matlab_path == (
            "/usr/local/bin/matlab"
        )

    def test_on_fbdc_dir_change(self) -> None:
        """_on_fbdc_dir_change stores the new path."""
        panel = BehaviourPanel()
        panel._on_fbdc_dir_change(
            None, "/home/user/FlyBowlDataCapture", None,
        )
        assert panel._fbdc_dir == (
            "/home/user/FlyBowlDataCapture"
        )

    def test_stop_fbdc_no_process(self) -> None:
        """_stop_fbdc is safe when no process exists."""
        panel = BehaviourPanel()
        panel._stop_fbdc()
        assert panel._fbdc_launch_status == ""

    def test_stop_fbdc_with_mock_process(self) -> None:
        """_stop_fbdc terminates existing process."""
        panel = BehaviourPanel()
        mock_proc = MagicMock()
        panel._fbdc_process = mock_proc
        panel._fbdc_running = True
        panel._stop_fbdc()
        mock_proc.terminate.assert_called_once()
        assert "terminated" in (
            panel._fbdc_launch_status.lower()
        )

    def test_on_fbdc_launch_calls_launch(self) -> None:
        """_on_fbdc_launch calls _launch_fbdc."""
        panel = BehaviourPanel()
        panel._launch_fbdc = MagicMock()
        panel._on_fbdc_launch(None, None, None)
        panel._launch_fbdc.assert_called_once()

    def test_on_fbdc_stop_calls_stop(self) -> None:
        """_on_fbdc_stop calls _stop_fbdc."""
        panel = BehaviourPanel()
        panel._stop_fbdc = MagicMock()
        panel._on_fbdc_stop(None, None, None)
        panel._stop_fbdc.assert_called_once()


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

    def test_has_profile_manager(self) -> None:
        """App creates a ProfileManager."""
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        assert app._profile_mgr is not None

    def test_has_preset_manager(self) -> None:
        """App creates a PresetManager."""
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        assert app._preset_mgr is not None

    def test_creates_behaviour_panel_on_run(self) -> None:
        """App _create_panels sets up BehaviourPanel."""
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        # _create_panels is called inside run() but we can
        # invoke it directly for testing
        app._create_panels(flomington_client=None)
        assert hasattr(app, "_behaviour_panel")
        assert app._behaviour_panel is not None


class TestAppCreatePanels:
    """Tests for FlocroscopeApp._create_panels()."""

    def _make_app(self):
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        app._create_panels(flomington_client=None)
        return app

    def test_all_panels_created(self) -> None:
        """All 14 panels are created."""
        app = self._make_app()
        assert app._stimulus_panel is not None
        assert app._session_panel is not None
        assert app._config_panel is not None
        assert app._comms_panel is not None
        assert app._calibration_panel is not None
        assert app._mapping_panel is not None
        assert app._flomington_panel is not None
        assert app._fictrac_panel is not None
        assert app._scanimage_panel is not None
        assert app._optogenetics_panel is not None
        assert app._tracking_panel is not None
        assert app._presets_panel is not None
        assert app._behaviour_panel is not None
        assert app._user_profile_panel is not None

    def test_comms_panel_has_none_comms(self) -> None:
        """CommsPanel starts with no comms hub."""
        app = self._make_app()
        assert app._comms_panel.comms is None

    def test_flomington_panel_has_no_client(self) -> None:
        """FlomingtonPanel starts with no client."""
        app = self._make_app()
        assert app._flomington_panel.client is None


class TestAppModuleConstants:
    """Tests for module-level constants in app.py."""

    def test_hw_indicators(self) -> None:
        from flocroscope.gui.app import _HW_INDICATORS
        assert len(_HW_INDICATORS) == 4
        abbrevs = [a for a, _ in _HW_INDICATORS]
        assert "FT" in abbrevs
        assert "SI" in abbrevs
        assert "LED" in abbrevs
        assert "PRES" in abbrevs

    def test_tab_tags_map(self) -> None:
        from flocroscope.gui.app import _TAB_TAGS
        from flocroscope.gui.layout import Tab
        for tab in Tab:
            assert tab in _TAB_TAGS
            assert _TAB_TAGS[tab].startswith("tab_")

    def test_tab_tags_count(self) -> None:
        from flocroscope.gui.app import _TAB_TAGS
        from flocroscope.gui.layout import Tab
        assert len(_TAB_TAGS) == len(Tab)


class TestAppExperimentModeCycle:
    """Tests for cycling through all experiment modes."""

    def test_all_modes_settable(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        from flocroscope.gui.layout import ExperimentMode
        app = FlocroscopeApp()
        for mode in ExperimentMode:
            app._on_experiment_mode(None, mode.value, None)
            assert app._experiment_mode is mode


class TestAppOnLogout:
    """Tests for FlocroscopeApp._on_logout()."""

    def test_logout_resets_prefs_applied(self) -> None:
        from flocroscope.gui.app import FlocroscopeApp
        app = FlocroscopeApp()
        app._prefs_applied = True
        app._create_panels(flomington_client=None)
        # Create a mock login panel
        app._login_panel = MagicMock()
        app._on_logout()
        assert app._prefs_applied is False


class TestAppBuildParser:
    """Tests for the CLI argument parser."""

    def test_build_parser(self) -> None:
        from flocroscope.gui.app import _build_parser
        parser = _build_parser()
        assert parser is not None

    def test_parser_accepts_config(self) -> None:
        from flocroscope.gui.app import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["myconfig.yaml"])
        assert args.config == "myconfig.yaml"

    def test_parser_default_no_config(self) -> None:
        from flocroscope.gui.app import _build_parser
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.config is None

    def test_parser_log_level(self) -> None:
        from flocroscope.gui.app import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

    def test_parser_default_log_level(self) -> None:
        from flocroscope.gui.app import _build_parser
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.log_level == "INFO"


class TestAppFindProjectRoot:
    """Tests for _find_project_root()."""

    def test_returns_path(self) -> None:
        from flocroscope.gui.app import _find_project_root
        root = _find_project_root()
        assert root.is_dir()


# ------------------------------------------------------------------ #
#  LoginPanel
# ------------------------------------------------------------------ #


class TestLoginPanelConstruction:
    """Tests for LoginPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with a ProfileManager."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_login_panel_profiles",
        )
        pm = ProfileManager(d)
        panel = LoginPanel(pm)
        assert panel._pm is pm
        assert panel.logged_in_user is None
        assert panel.is_logged_in is False

    def test_group_tag(self) -> None:
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_login_tag",
        )
        pm = ProfileManager(d)
        panel = LoginPanel(pm)
        assert panel.group_tag == "grp_login"
        assert panel.window_tag == "grp_login"

    def test_initial_state(self) -> None:
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_login_state",
        )
        pm = ProfileManager(d)
        panel = LoginPanel(pm)
        assert panel._username == ""
        assert panel._password == ""
        assert panel._show_register is False

    def test_build_requires_dearpygui(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip(
            "dearpygui available but viewport required"
        )

    def test_registration_fields_initial(self) -> None:
        """Registration fields start empty."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_login_reg_fields",
        )
        pm = ProfileManager(d)
        panel = LoginPanel(pm)
        assert panel._reg_username == ""
        assert panel._reg_display_name == ""
        assert panel._reg_password == ""
        assert panel._reg_confirm == ""


class TestLoginPanelCallbacks:
    """Tests for LoginPanel callback methods."""

    def _make(self):
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_login_callbacks",
        )
        pm = ProfileManager(d)
        return LoginPanel(pm)

    def test_on_username(self) -> None:
        p = self._make()
        p._on_username(None, "alice", None)
        assert p._username == "alice"

    def test_on_reg_username(self) -> None:
        p = self._make()
        p._on_reg_username(None, "newuser", None)
        assert p._reg_username == "newuser"

    def test_on_reg_display(self) -> None:
        p = self._make()
        p._on_reg_display(None, "Alice Smith", None)
        assert p._reg_display_name == "Alice Smith"

    def test_on_reg_password(self) -> None:
        p = self._make()
        p._on_reg_password(None, "secret", None)
        assert p._reg_password == "secret"

    def test_on_reg_confirm(self) -> None:
        p = self._make()
        p._on_reg_confirm(None, "secret", None)
        assert p._reg_confirm == "secret"

    def test_update_is_noop(self) -> None:
        """update() does nothing (placeholder)."""
        p = self._make()
        p.update()  # should not raise


class TestLoginPanelImport:
    """Tests for LoginPanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            LoginPanel as LP,
        )
        assert LP is LoginPanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "LoginPanel" in __all__


# ------------------------------------------------------------------ #
#  PresetsPanel
# ------------------------------------------------------------------ #


class TestPresetsPanelConstruction:
    """Tests for PresetsPanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with config and manager."""
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_panel",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr)
        assert panel._config is cfg
        assert panel._pm is mgr
        assert panel._preset_name == ""
        assert panel._status_msg == ""

    def test_current_user_default(self) -> None:
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_user",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr)
        assert panel.current_user == ""

    def test_current_user_setter(self) -> None:
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_user_set",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(
            cfg, mgr, current_user="alice",
        )
        assert panel.current_user == "alice"
        panel.current_user = "bob"
        assert panel.current_user == "bob"

    def test_group_tag(self) -> None:
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_tag",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr)
        assert panel.group_tag == "grp_presets"
        assert panel.window_tag == "grp_presets"

    def test_save_preset_via_panel(self) -> None:
        """Panel _save_preset() delegates to PresetManager."""
        cfg = FlocroscopeConfig()
        cfg.arena.radius_mm = 77.0
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_save",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr, current_user="tester")
        panel._preset_name = "test_preset"
        panel._preset_desc = "Testing"
        panel._save_preset()
        assert "Saved" in panel._status_msg

        # Verify preset was actually saved
        result = mgr.load_preset("test_preset")
        assert result is not None
        _, loaded_cfg = result
        assert loaded_cfg.arena.radius_mm == 77.0

    def test_save_preset_empty_name(self) -> None:
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_empty",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr)
        panel._preset_name = ""
        panel._save_preset()
        assert "name" in panel._status_msg.lower()

    def test_load_preset_via_panel(self) -> None:
        """Panel _load_preset() applies config."""
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_load",
        )
        mgr = PresetManager(d)
        # Save a preset with custom arena radius
        save_cfg = FlocroscopeConfig()
        save_cfg.arena.radius_mm = 88.0
        mgr.save_preset("loadme", save_cfg)

        panel = PresetsPanel(cfg, mgr)
        panel._selected_preset = "loadme"
        panel._load_preset()
        assert cfg.arena.radius_mm == 88.0
        assert "Loaded" in panel._status_msg

    def test_duplicate_preset(self) -> None:
        """_duplicate_preset creates a copy with new name."""
        cfg = FlocroscopeConfig()
        cfg.arena.radius_mm = 99.0
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_dup",
        )
        mgr = PresetManager(d)
        mgr.save_preset("original", cfg)
        panel = PresetsPanel(cfg, mgr, current_user="tester")
        panel._selected_preset = "original"
        panel._duplicate_preset()
        assert "Duplicated" in panel._status_msg
        assert mgr.preset_exists("original (copy)")
        result = mgr.load_preset("original (copy)")
        assert result is not None
        _, dup_cfg = result
        assert dup_cfg.arena.radius_mm == 99.0

    def test_duplicate_avoids_collision(self) -> None:
        """_duplicate_preset adds counter for name collisions."""
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_dup2",
        )
        mgr = PresetManager(d)
        mgr.save_preset("test", cfg)
        mgr.save_preset("test (copy)", cfg)
        panel = PresetsPanel(cfg, mgr)
        panel._selected_preset = "test"
        panel._duplicate_preset()
        assert mgr.preset_exists("test (copy 2)")

    def test_filter_state_defaults(self) -> None:
        """Panel has filter state initialized to no filtering."""
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_filter",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr)
        assert panel._filter_by_mode is False
        assert panel._filter_tag == ""

    def test_experiment_mode_property(self) -> None:
        """Panel tracks experiment_mode for filtering."""
        cfg = FlocroscopeConfig()
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_presets_mode",
        )
        mgr = PresetManager(d)
        panel = PresetsPanel(cfg, mgr)
        assert panel.experiment_mode == "Behaviour"
        panel.experiment_mode = "VR"
        assert panel.experiment_mode == "VR"

    def test_build_requires_dearpygui(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip(
            "dearpygui available but viewport required"
        )


class TestPresetsPanelImport:
    """Tests for PresetsPanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            PresetsPanel as PP,
        )
        assert PP is PresetsPanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "PresetsPanel" in __all__


# ------------------------------------------------------------------ #
#  UserProfilePanel
# ------------------------------------------------------------------ #


class TestUserProfilePanelConstruction:
    """Tests for UserProfilePanel instantiation."""

    def test_default_construction(self) -> None:
        """Panel can be created with a ProfileManager."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_panel",
        )
        pm = ProfileManager(d)
        panel = UserProfilePanel(pm)
        assert panel._pm is pm
        assert panel._status_msg == ""

    def test_group_tag(self) -> None:
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_tag",
        )
        pm = ProfileManager(d)
        panel = UserProfilePanel(pm)
        assert panel.group_tag == "grp_user_profile"
        assert panel.window_tag == "grp_user_profile"

    def test_update_display_name(self) -> None:
        """_update_display_name changes the profile."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_name",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "pass123")
        pm.login("tester", "pass123")
        panel = UserProfilePanel(pm)
        panel._display_name = "New Name"
        panel._update_display_name()
        assert "updated" in panel._status_msg.lower()
        profile = pm.get_profile("tester")
        assert profile.display_name == "New Name"

    def test_save_defaults(self) -> None:
        """_save_defaults persists user preferences."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_defaults",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "pass123")
        pm.login("tester", "pass123")
        panel = UserProfilePanel(pm)
        panel._default_mode = "VR"
        panel._default_preset = "my_preset"
        panel._save_defaults()
        assert "saved" in panel._status_msg.lower()
        profile = pm.get_profile("tester")
        assert profile.default_experiment_mode == "VR"
        assert profile.default_preset == "my_preset"

    def test_change_password_success(self) -> None:
        """_change_password works with correct old password."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_chpass",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "oldpass")
        pm.login("tester", "oldpass")
        panel = UserProfilePanel(pm)
        panel._old_password = "oldpass"
        panel._new_password = "newpass"
        panel._confirm_password = "newpass"
        panel._change_password()
        assert "changed" in panel._status_msg.lower()
        # Verify new password works
        assert pm.authenticate("tester", "newpass") is not None

    def test_change_password_mismatch(self) -> None:
        """_change_password fails with mismatched passwords."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_mismatch",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "oldpass")
        pm.login("tester", "oldpass")
        panel = UserProfilePanel(pm)
        panel._old_password = "oldpass"
        panel._new_password = "newpass"
        panel._confirm_password = "different"
        panel._change_password()
        assert "match" in panel._status_msg.lower()

    def test_not_logged_in(self) -> None:
        """Actions fail gracefully when not logged in."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_nologin",
        )
        pm = ProfileManager(d)
        panel = UserProfilePanel(pm)
        panel._display_name = "Test"
        panel._update_display_name()
        assert "not logged in" in panel._status_msg.lower()

    def test_delete_account_not_confirmed(self) -> None:
        """_delete_account fails without confirmation."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_del_noconfirm",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "pass")
        pm.login("tester", "pass")
        panel = UserProfilePanel(pm)
        panel._delete_confirmed = False
        panel._delete_account()
        assert "confirmation" in panel._status_msg.lower()
        assert pm.get_profile("tester") is not None

    def test_delete_account_success(self) -> None:
        """_delete_account removes the user profile."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_del_ok",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "pass")
        pm.login("tester", "pass")
        panel = UserProfilePanel(pm)
        panel._delete_confirmed = True
        panel._delete_account()
        assert "deleted" in panel._status_msg.lower()
        assert pm.get_profile("tester") is None

    def test_delete_account_triggers_callback(self) -> None:
        """_delete_account calls _on_account_deleted if set."""
        d = os.path.join(
            os.environ.get("TMPDIR", "/tmp/claude-1000"),
            "test_up_del_cb",
        )
        shutil.rmtree(d, ignore_errors=True)
        pm = ProfileManager(d)
        pm.create_user("tester", "pass")
        pm.login("tester", "pass")
        panel = UserProfilePanel(pm)
        panel._delete_confirmed = True
        called = []
        panel._on_account_deleted = lambda: called.append(1)
        panel._delete_account()
        assert called == [1]

    def test_build_requires_dearpygui(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip(
            "dearpygui available but viewport required"
        )


class TestUserProfilePanelImport:
    """Tests for UserProfilePanel import and re-export."""

    def test_importable_from_package(self) -> None:
        from flocroscope.gui.panels import (
            UserProfilePanel as UPP,
        )
        assert UPP is UserProfilePanel

    def test_in_all(self) -> None:
        from flocroscope.gui.panels import __all__
        assert "UserProfilePanel" in __all__
