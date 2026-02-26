"""Round-trip tests for CommsConfig, SessionConfig, and full config save/load.

Verifies that YAML serialization via ``save_config`` / ``load_config`` is
lossless for all config sections, with special attention to the newer
``CommsConfig`` and ``SessionConfig`` dataclasses.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
import yaml

from virtual_reality.config.loader import load_config, save_config
from virtual_reality.config.schema import (
    ArenaConfig,
    AutonomousConfig,
    CalibrationConfig,
    CameraConfig,
    CommsConfig,
    DisplayConfig,
    FlyModelConfig,
    LightingConfig,
    MinimapConfig,
    MovementConfig,
    ScalingConfig,
    SessionConfig,
    VirtualRealityConfig,
    WarpConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_section_names() -> list[str]:
    """Return the field names for every section of VirtualRealityConfig."""
    return [f.name for f in dataclasses.fields(VirtualRealityConfig)]


def _configs_equal(a: VirtualRealityConfig, b: VirtualRealityConfig) -> bool:
    """Deep-compare two VirtualRealityConfig instances field by field.

    We compare each sub-dataclass individually so the assertion error
    is easier to diagnose.
    """
    for f in dataclasses.fields(a):
        val_a = getattr(a, f.name)
        val_b = getattr(b, f.name)
        if val_a != val_b:
            return False
    return True


# ---------------------------------------------------------------------------
# 1. CommsConfig round-trip
# ---------------------------------------------------------------------------


class TestCommsConfigRoundtrip:
    """Verify CommsConfig survives a YAML save/load cycle."""

    def test_custom_comms_roundtrip(self, tmp_path: Path) -> None:
        original = VirtualRealityConfig()
        original.comms.enabled = True
        original.comms.fictrac_host = "192.168.1.42"
        original.comms.fictrac_port = 3000
        original.comms.fictrac_ball_radius_mm = 5.5
        original.comms.scanimage_port = 6000
        original.comms.led_port = 7000
        original.comms.presenter_host = "10.0.0.1"
        original.comms.presenter_port = 8000
        original.comms.log_messages = True

        path = tmp_path / "comms.yaml"
        save_config(original, path)
        loaded = load_config(path)

        assert loaded.comms.enabled is True
        assert loaded.comms.fictrac_host == "192.168.1.42"
        assert loaded.comms.fictrac_port == 3000
        assert loaded.comms.fictrac_ball_radius_mm == 5.5
        assert loaded.comms.scanimage_port == 6000
        assert loaded.comms.led_port == 7000
        assert loaded.comms.presenter_host == "10.0.0.1"
        assert loaded.comms.presenter_port == 8000
        assert loaded.comms.log_messages is True

    def test_comms_disabled_ports_zero(self, tmp_path: Path) -> None:
        """Ports set to 0 (disabled) should round-trip as 0."""
        original = VirtualRealityConfig()
        original.comms.enabled = False
        original.comms.fictrac_port = 0
        original.comms.scanimage_port = 0
        original.comms.led_port = 0
        original.comms.presenter_port = 0

        path = tmp_path / "comms_off.yaml"
        save_config(original, path)
        loaded = load_config(path)

        assert loaded.comms.enabled is False
        assert loaded.comms.fictrac_port == 0
        assert loaded.comms.scanimage_port == 0
        assert loaded.comms.led_port == 0
        assert loaded.comms.presenter_port == 0


# ---------------------------------------------------------------------------
# 2. SessionConfig round-trip
# ---------------------------------------------------------------------------


class TestSessionConfigRoundtrip:
    """Verify SessionConfig survives a YAML save/load cycle."""

    def test_custom_session_roundtrip(self, tmp_path: Path) -> None:
        original = VirtualRealityConfig()
        original.session.output_dir = "/tmp/experiment_42"
        original.session.auto_save = False
        original.session.log_fictrac = False
        original.session.log_stimulus = False
        original.session.log_interval_ms = 33.33

        path = tmp_path / "session.yaml"
        save_config(original, path)
        loaded = load_config(path)

        assert loaded.session.output_dir == "/tmp/experiment_42"
        assert loaded.session.auto_save is False
        assert loaded.session.log_fictrac is False
        assert loaded.session.log_stimulus is False
        assert loaded.session.log_interval_ms == pytest.approx(33.33)

    def test_session_defaults_roundtrip(self, tmp_path: Path) -> None:
        """Default SessionConfig values should survive the round-trip."""
        original = VirtualRealityConfig()

        path = tmp_path / "session_defaults.yaml"
        save_config(original, path)
        loaded = load_config(path)

        assert loaded.session.output_dir == "data/sessions"
        assert loaded.session.auto_save is True
        assert loaded.session.log_fictrac is True
        assert loaded.session.log_stimulus is True
        assert loaded.session.log_interval_ms == pytest.approx(16.67)


# ---------------------------------------------------------------------------
# 3. Full lossless round-trip for all 13 sections
# ---------------------------------------------------------------------------


class TestFullConfigRoundtrip:
    """save_config + load_config should be lossless for every section."""

    def test_default_config_roundtrip(self, tmp_path: Path) -> None:
        """A default VirtualRealityConfig round-trips without data loss."""
        original = VirtualRealityConfig()
        path = tmp_path / "full_default.yaml"
        save_config(original, path)
        loaded = load_config(path)
        assert _configs_equal(original, loaded)

    def test_fully_customised_config_roundtrip(self, tmp_path: Path) -> None:
        """A heavily customised config round-trips without data loss."""
        cfg = VirtualRealityConfig()

        # Arena
        cfg.arena.radius_mm = 80.0
        # Fly model
        cfg.fly_model.model_path = "/custom/fly.glb"
        cfg.fly_model.phys_length_mm = 4.5
        cfg.fly_model.base_scale = 2.0
        cfg.fly_model.yaw_offset_deg = 90.0
        # Camera
        cfg.camera.x_mm = 10.0
        cfg.camera.y_mm = -80.0
        cfg.camera.height_mm = 2.0
        cfg.camera.projection = "perspective"
        cfg.camera.fov_x_deg = 90.0
        cfg.camera.fov_y_deg = 45.0
        cfg.camera.allow_ultrawide = False
        cfg.camera.flip_model_for_ultrawide = False
        # Movement
        cfg.movement.speed_mm_s = 30.0
        cfg.movement.start_x = 5.0
        cfg.movement.start_y = -10.0
        cfg.movement.start_heading_deg = 45.0
        # Autonomous
        cfg.autonomous.enabled = False
        cfg.autonomous.mean_run_dur = 2.0
        cfg.autonomous.mean_pause_dur = 1.5
        # Lighting
        cfg.lighting.ambient = 0.3
        cfg.lighting.intensities = (1.0, 2.0, 3.0, 4.0)
        cfg.lighting.elevation_deg = 45.0
        cfg.lighting.max_gain = 8.0
        # Minimap
        cfg.minimap.enabled = False
        cfg.minimap.width = 200
        cfg.minimap.height = 200
        cfg.minimap.trail_color = (0, 255, 128)
        cfg.minimap.trail_thick = 4
        # Warp
        cfg.warp.mapx_path = "/data/mapx.npy"
        cfg.warp.mapy_path = "/data/mapy.npy"
        # Display
        cfg.display.bg_color = (0, 0, 0)
        cfg.display.target_fps = 144
        cfg.display.borderless = False
        cfg.display.monitor = "left"
        # Scaling
        cfg.scaling.screen_distance_mm = 120.0
        cfg.scaling.apparent_distance_mm = 50.0
        cfg.scaling.dist_scale_smooth_hz = 4.0
        cfg.scaling.min_cam_fly_dist_mm = 3.0
        # Calibration
        cfg.calibration.camera_type = "rotpy"
        cfg.calibration.proj_w = 1920
        cfg.calibration.proj_h = 1080
        cfg.calibration.mode = "gray"
        cfg.calibration.periods_x = 64
        cfg.calibration.periods_y = 48
        cfg.calibration.nphase = 8
        cfg.calibration.avg_per = 3
        cfg.calibration.exposure_ms = 20.0
        cfg.calibration.gain_db = 5.0
        # Comms
        cfg.comms.enabled = True
        cfg.comms.fictrac_host = "192.168.0.100"
        cfg.comms.fictrac_port = 4000
        cfg.comms.fictrac_ball_radius_mm = 6.0
        cfg.comms.scanimage_port = 7000
        cfg.comms.led_port = 8000
        cfg.comms.presenter_host = "10.10.0.1"
        cfg.comms.presenter_port = 9000
        cfg.comms.log_messages = True
        # Session
        cfg.session.output_dir = "/results/session_1"
        cfg.session.auto_save = False
        cfg.session.log_fictrac = False
        cfg.session.log_stimulus = False
        cfg.session.log_interval_ms = 50.0

        path = tmp_path / "full_custom.yaml"
        save_config(cfg, path)
        loaded = load_config(path)

        # Compare every section individually for clear failure messages.
        for f in dataclasses.fields(cfg):
            assert getattr(loaded, f.name) == getattr(cfg, f.name), (
                f"Mismatch in section '{f.name}'"
            )

    def test_all_section_names_present_in_yaml(self, tmp_path: Path) -> None:
        """The YAML file should contain a key for every config section."""
        cfg = VirtualRealityConfig()
        path = tmp_path / "sections.yaml"
        save_config(cfg, path)

        data = yaml.safe_load(path.read_text())
        expected_sections = _all_section_names()
        for name in expected_sections:
            assert name in data, f"Section '{name}' missing from YAML output"

    def test_section_count_is_13(self) -> None:
        """Guard against new sections being added without updating tests.

        VirtualRealityConfig currently has 13 sub-config sections.
        If you add a new section, update this count and add round-trip
        coverage above.
        """
        assert len(dataclasses.fields(VirtualRealityConfig)) == 13


# ---------------------------------------------------------------------------
# 4. Partial YAML with only comms section
# ---------------------------------------------------------------------------


class TestPartialCommsYAML:
    """Loading a YAML that only specifies ``comms`` should fill defaults."""

    def test_only_comms_section(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "comms_only.yaml"
        yaml_path.write_text(yaml.dump({
            "comms": {
                "enabled": True,
                "fictrac_port": 9999,
                "presenter_host": "10.0.0.5",
            },
        }))
        cfg = load_config(yaml_path)

        # Comms values from the file.
        assert cfg.comms.enabled is True
        assert cfg.comms.fictrac_port == 9999
        assert cfg.comms.presenter_host == "10.0.0.5"
        # Comms fields not in the file fall back to defaults.
        assert cfg.comms.fictrac_host == "localhost"
        assert cfg.comms.scanimage_port == 5000
        assert cfg.comms.led_port == 5001
        assert cfg.comms.presenter_port == 5002
        assert cfg.comms.log_messages is False

        # All other sections should be at their defaults.
        default = VirtualRealityConfig()
        for f in dataclasses.fields(default):
            if f.name == "comms":
                continue
            assert getattr(cfg, f.name) == getattr(default, f.name), (
                f"Section '{f.name}' differs from default"
            )


# ---------------------------------------------------------------------------
# 5. Partial YAML with only session section
# ---------------------------------------------------------------------------


class TestPartialSessionYAML:
    """Loading a YAML that only specifies ``session`` should fill defaults."""

    def test_only_session_section(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "session_only.yaml"
        yaml_path.write_text(yaml.dump({
            "session": {
                "output_dir": "/data/experiment_99",
                "auto_save": False,
                "log_interval_ms": 100.0,
            },
        }))
        cfg = load_config(yaml_path)

        # Session values from the file.
        assert cfg.session.output_dir == "/data/experiment_99"
        assert cfg.session.auto_save is False
        assert cfg.session.log_interval_ms == pytest.approx(100.0)
        # Session fields not in the file fall back to defaults.
        assert cfg.session.log_fictrac is True
        assert cfg.session.log_stimulus is True

        # All other sections should be at their defaults.
        default = VirtualRealityConfig()
        for f in dataclasses.fields(default):
            if f.name == "session":
                continue
            assert getattr(cfg, f.name) == getattr(default, f.name), (
                f"Section '{f.name}' differs from default"
            )


# ---------------------------------------------------------------------------
# 6. Tuple fields survive round-trip
# ---------------------------------------------------------------------------


class TestTupleFieldsRoundtrip:
    """Tuple fields are serialized as YAML lists and must convert back."""

    def test_bg_color_roundtrip(self, tmp_path: Path) -> None:
        cfg = VirtualRealityConfig()
        cfg.display.bg_color = (10, 20, 30)

        path = tmp_path / "tuple_bg.yaml"
        save_config(cfg, path)
        loaded = load_config(path)

        assert loaded.display.bg_color == (10, 20, 30)
        assert isinstance(loaded.display.bg_color, tuple)

    def test_trail_color_roundtrip(self, tmp_path: Path) -> None:
        cfg = VirtualRealityConfig()
        cfg.minimap.trail_color = (0, 128, 255)

        path = tmp_path / "tuple_trail.yaml"
        save_config(cfg, path)
        loaded = load_config(path)

        assert loaded.minimap.trail_color == (0, 128, 255)
        assert isinstance(loaded.minimap.trail_color, tuple)

    def test_lighting_intensities_roundtrip(self, tmp_path: Path) -> None:
        cfg = VirtualRealityConfig()
        cfg.lighting.intensities = (0.5, 1.5, 2.5, 3.5)

        path = tmp_path / "tuple_light.yaml"
        save_config(cfg, path)
        loaded = load_config(path)

        assert loaded.lighting.intensities == (0.5, 1.5, 2.5, 3.5)
        assert isinstance(loaded.lighting.intensities, tuple)

    def test_single_element_tuple_roundtrip(self, tmp_path: Path) -> None:
        """A single-element tuple should still come back as a tuple."""
        cfg = VirtualRealityConfig()
        cfg.lighting.intensities = (7.0,)

        path = tmp_path / "tuple_single.yaml"
        save_config(cfg, path)
        loaded = load_config(path)

        assert loaded.lighting.intensities == (7.0,)
        assert isinstance(loaded.lighting.intensities, tuple)

    def test_empty_tuple_roundtrip(self, tmp_path: Path) -> None:
        """An empty tuple should round-trip as an empty tuple."""
        cfg = VirtualRealityConfig()
        cfg.lighting.intensities = ()

        path = tmp_path / "tuple_empty.yaml"
        save_config(cfg, path)
        loaded = load_config(path)

        assert loaded.lighting.intensities == ()
        assert isinstance(loaded.lighting.intensities, tuple)

    def test_yaml_stores_tuples_as_lists(self, tmp_path: Path) -> None:
        """Verify the on-disk YAML uses plain lists for tuple fields."""
        cfg = VirtualRealityConfig()
        cfg.display.bg_color = (10, 20, 30)
        cfg.lighting.intensities = (1.0, 2.0, 3.0, 4.0)

        path = tmp_path / "tuple_raw.yaml"
        save_config(cfg, path)

        data = yaml.safe_load(path.read_text())
        assert isinstance(data["display"]["bg_color"], list)
        assert data["display"]["bg_color"] == [10, 20, 30]
        assert isinstance(data["lighting"]["intensities"], list)
        assert data["lighting"]["intensities"] == [1.0, 2.0, 3.0, 4.0]
