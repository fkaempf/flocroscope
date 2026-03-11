"""Tests for the experiment presets system.

Pure Python tests -- no DearPyGui required.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from flocroscope.config.schema import FlocroscopeConfig
from flocroscope.gui.presets import (
    ExperimentPreset,
    PresetManager,
)


@pytest.fixture
def tmp_presets_dir():
    """Create a temporary directory for preset storage."""
    d = os.path.join(
        os.environ.get("TMPDIR", "/tmp/claude-1000"),
        "test_presets",
    )
    os.makedirs(d, exist_ok=True)
    yield d
    # Cleanup
    for f in Path(d).glob("*.yaml"):
        f.unlink()
    try:
        Path(d).rmdir()
    except OSError:
        pass


@pytest.fixture
def mgr(tmp_presets_dir):
    """Create a PresetManager with temp storage."""
    return PresetManager(tmp_presets_dir)


# ------------------------------------------------------------------ #
#  ExperimentPreset dataclass
# ------------------------------------------------------------------ #


class TestExperimentPreset:
    """Tests for the ExperimentPreset dataclass."""

    def test_default_construction(self) -> None:
        p = ExperimentPreset()
        assert p.name == ""
        assert p.description == ""
        assert p.author == ""
        assert p.experiment_mode == "Behaviour"
        assert p.tags == []

    def test_custom_fields(self) -> None:
        p = ExperimentPreset(
            name="Test Preset",
            author="alice",
            tags=["opto", "2p"],
        )
        assert p.name == "Test Preset"
        assert p.author == "alice"
        assert p.tags == ["opto", "2p"]


# ------------------------------------------------------------------ #
#  PresetManager - Save
# ------------------------------------------------------------------ #


class TestPresetManagerSave:
    """Tests for saving presets."""

    def test_save_creates_file(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("my_preset", config)
        assert mgr.preset_exists("my_preset")

    def test_save_returns_metadata(self, mgr) -> None:
        config = FlocroscopeConfig()
        preset = mgr.save_preset(
            "test",
            config,
            description="A test preset",
            author="alice",
        )
        assert preset.name == "test"
        assert preset.description == "A test preset"
        assert preset.author == "alice"
        assert preset.created_at != ""
        assert preset.updated_at != ""

    def test_save_empty_name_raises(self, mgr) -> None:
        config = FlocroscopeConfig()
        with pytest.raises(ValueError, match="cannot be empty"):
            mgr.save_preset("", config)

    def test_save_overwrites_existing(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset(
            "test", config, description="v1",
        )
        mgr.save_preset(
            "test", config, description="v2",
        )
        meta = mgr.load_preset_metadata("test")
        assert meta.description == "v2"

    def test_save_preserves_created_at(self, mgr) -> None:
        config = FlocroscopeConfig()
        p1 = mgr.save_preset("test", config)
        created = p1.created_at
        p2 = mgr.save_preset(
            "test", config, description="updated",
        )
        assert p2.created_at == created

    def test_save_with_tags(self, mgr) -> None:
        config = FlocroscopeConfig()
        preset = mgr.save_preset(
            "tagged", config, tags=["opto", "vr"],
        )
        assert preset.tags == ["opto", "vr"]


# ------------------------------------------------------------------ #
#  PresetManager - Load
# ------------------------------------------------------------------ #


class TestPresetManagerLoad:
    """Tests for loading presets."""

    def test_load_returns_config(self, mgr) -> None:
        config = FlocroscopeConfig()
        config.arena.radius_mm = 55.5
        mgr.save_preset("test", config)
        result = mgr.load_preset("test")
        assert result is not None
        preset, loaded_config = result
        assert preset.name == "test"
        assert loaded_config.arena.radius_mm == 55.5

    def test_load_nonexistent_returns_none(self, mgr) -> None:
        assert mgr.load_preset("nope") is None

    def test_load_preserves_nested_config(self, mgr) -> None:
        config = FlocroscopeConfig()
        config.camera.projection = "equidistant"
        config.comms.enabled = True
        config.movement.speed_mm_s = 42.0
        mgr.save_preset("full", config)
        _, loaded = mgr.load_preset("full")
        assert loaded.camera.projection == "equidistant"
        assert loaded.comms.enabled is True
        assert loaded.movement.speed_mm_s == 42.0

    def test_load_metadata_only(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset(
            "meta", config,
            author="bob", description="quick",
        )
        meta = mgr.load_preset_metadata("meta")
        assert meta is not None
        assert meta.author == "bob"

    def test_load_metadata_nonexistent(self, mgr) -> None:
        assert mgr.load_preset_metadata("nope") is None


# ------------------------------------------------------------------ #
#  PresetManager - List
# ------------------------------------------------------------------ #


class TestPresetManagerList:
    """Tests for listing presets."""

    def test_list_empty(self, mgr) -> None:
        assert mgr.list_presets() == []

    def test_list_after_save(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("alpha", config)
        mgr.save_preset("beta", config)
        presets = mgr.list_presets()
        names = [p.name for p in presets]
        assert "alpha" in names
        assert "beta" in names

    def test_list_sorted_by_name(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("zebra", config)
        mgr.save_preset("alpha", config)
        presets = mgr.list_presets()
        names = [p.name for p in presets]
        assert names == sorted(names)


# ------------------------------------------------------------------ #
#  PresetManager - Delete
# ------------------------------------------------------------------ #


class TestPresetManagerDelete:
    """Tests for deleting presets."""

    def test_delete_existing(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("doomed", config)
        assert mgr.delete_preset("doomed") is True
        assert not mgr.preset_exists("doomed")

    def test_delete_nonexistent(self, mgr) -> None:
        assert mgr.delete_preset("nope") is False


# ------------------------------------------------------------------ #
#  PresetManager - Slug generation
# ------------------------------------------------------------------ #


class TestPresetSlug:
    """Tests for filename slug generation."""

    def test_spaces_replaced(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("My Preset", config)
        path = mgr._preset_path("My Preset")
        assert "my_preset" in path.name

    def test_case_normalized(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("BIG", config)
        assert mgr.preset_exists("BIG")


# ------------------------------------------------------------------ #
#  PresetManager - Filtering
# ------------------------------------------------------------------ #


class TestPresetFiltering:
    """Tests for list_presets_filtered method."""

    def test_filter_by_mode(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset(
            "vr1", config, experiment_mode="VR",
        )
        mgr.save_preset(
            "beh1", config, experiment_mode="Behaviour",
        )
        mgr.save_preset(
            "vr2", config, experiment_mode="VR",
        )
        result = mgr.list_presets_filtered(
            experiment_mode="VR",
        )
        names = [p.name for p in result]
        assert "vr1" in names
        assert "vr2" in names
        assert "beh1" not in names

    def test_filter_by_tag(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset(
            "tagged", config, tags=["opto", "vr"],
        )
        mgr.save_preset(
            "untagged", config, tags=[],
        )
        result = mgr.list_presets_filtered(tag="opto")
        names = [p.name for p in result]
        assert "tagged" in names
        assert "untagged" not in names

    def test_filter_empty_returns_all(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset("a", config)
        mgr.save_preset("b", config)
        result = mgr.list_presets_filtered()
        assert len(result) == 2

    def test_filter_combined(self, mgr) -> None:
        config = FlocroscopeConfig()
        mgr.save_preset(
            "match", config,
            experiment_mode="VR", tags=["opto"],
        )
        mgr.save_preset(
            "wrong_mode", config,
            experiment_mode="Behaviour", tags=["opto"],
        )
        mgr.save_preset(
            "wrong_tag", config,
            experiment_mode="VR", tags=["tracking"],
        )
        result = mgr.list_presets_filtered(
            experiment_mode="VR", tag="opto",
        )
        names = [p.name for p in result]
        assert names == ["match"]

    def test_filter_includes_empty_mode_presets(
        self, mgr,
    ) -> None:
        """Presets with empty mode match any mode filter."""
        config = FlocroscopeConfig()
        mgr.save_preset(
            "generic", config, experiment_mode="",
        )
        mgr.save_preset(
            "specific", config, experiment_mode="VR",
        )
        result = mgr.list_presets_filtered(
            experiment_mode="VR",
        )
        names = [p.name for p in result]
        assert "generic" in names
        assert "specific" in names
