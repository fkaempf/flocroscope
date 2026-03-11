"""Experiment presets system for saving and loading configurations.

Allows users to create named experiment presets that store a full
``FlocroscopeConfig`` snapshot.  Presets are saved as YAML files
in a dedicated directory and can be loaded, listed, and deleted.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from flocroscope.config.schema import FlocroscopeConfig

logger = logging.getLogger(__name__)

_DEFAULT_PRESETS_DIR = "data/presets"


@dataclass
class ExperimentPreset:
    """Metadata wrapper around a saved configuration.

    Attributes:
        name: Short human-readable preset name.
        description: Longer description of the experiment setup.
        author: Username of the preset creator.
        created_at: ISO 8601 timestamp of creation.
        updated_at: ISO 8601 timestamp of last update.
        experiment_mode: The experiment mode this preset is for.
        tags: Free-form tags for organisation.
    """

    name: str = ""
    description: str = ""
    author: str = ""
    created_at: str = ""
    updated_at: str = ""
    experiment_mode: str = "Behaviour"
    tags: list[str] = field(default_factory=list)


class PresetManager:
    """Manages experiment preset files on disk.

    Each preset is a YAML file containing the ``ExperimentPreset``
    metadata and a full serialized ``FlocroscopeConfig``.

    Args:
        presets_dir: Directory to store preset YAML files.
    """

    def __init__(
        self,
        presets_dir: str | Path = _DEFAULT_PRESETS_DIR,
    ) -> None:
        self._dir = Path(presets_dir)

    @property
    def presets_dir(self) -> Path:
        """The directory where presets are stored."""
        return self._dir

    def save_preset(
        self,
        name: str,
        config: FlocroscopeConfig,
        description: str = "",
        author: str = "",
        experiment_mode: str = "Behaviour",
        tags: list[str] | None = None,
    ) -> ExperimentPreset:
        """Save the current configuration as a named preset.

        If a preset with the same name already exists, it is
        overwritten and *updated_at* is refreshed.

        Args:
            name: Short preset name (used as filename slug).
            config: Configuration to snapshot.
            description: Human-readable description.
            author: Username of the creator.
            experiment_mode: The experiment mode string.
            tags: Optional list of tags.

        Returns:
            The saved preset metadata.

        Raises:
            ValueError: If *name* is empty.
        """
        name = name.strip()
        if not name:
            raise ValueError("Preset name cannot be empty")

        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Try to preserve created_at from existing preset
        existing = self.load_preset_metadata(name)
        created_at = (
            existing.created_at if existing else now
        )

        preset = ExperimentPreset(
            name=name,
            description=description,
            author=author,
            created_at=created_at,
            updated_at=now,
            experiment_mode=experiment_mode,
            tags=tags or [],
        )

        self._write(preset, config)
        logger.info("Saved preset: %s", name)
        return preset

    def load_preset(
        self, name: str,
    ) -> tuple[ExperimentPreset, FlocroscopeConfig] | None:
        """Load a preset's metadata and configuration.

        Returns ``None`` if the preset does not exist.
        """
        path = self._preset_path(name)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return None

            meta_data = data.get("preset", {})
            config_data = data.get("config", {})

            preset = ExperimentPreset(
                name=meta_data.get("name", name),
                description=meta_data.get("description", ""),
                author=meta_data.get("author", ""),
                created_at=meta_data.get("created_at", ""),
                updated_at=meta_data.get("updated_at", ""),
                experiment_mode=meta_data.get(
                    "experiment_mode", "Behaviour",
                ),
                tags=meta_data.get("tags", []),
            )

            from flocroscope.config.loader import (
                _apply_dict_to_dataclass,
            )
            from flocroscope.config.schema import (
                FlocroscopeConfig,
            )

            config = FlocroscopeConfig()
            if config_data:
                _apply_dict_to_dataclass(config, config_data)

            return preset, config
        except Exception as exc:
            logger.warning(
                "Failed to load preset '%s': %s", name, exc,
            )
            return None

    def load_preset_metadata(
        self, name: str,
    ) -> ExperimentPreset | None:
        """Load only the metadata for a preset (faster than full load)."""
        path = self._preset_path(name)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            meta_data = data.get("preset", {})
            return ExperimentPreset(
                name=meta_data.get("name", name),
                description=meta_data.get("description", ""),
                author=meta_data.get("author", ""),
                created_at=meta_data.get("created_at", ""),
                updated_at=meta_data.get("updated_at", ""),
                experiment_mode=meta_data.get(
                    "experiment_mode", "Behaviour",
                ),
                tags=meta_data.get("tags", []),
            )
        except Exception:
            return None

    def list_presets(self) -> list[ExperimentPreset]:
        """Return metadata for all saved presets, sorted by name."""
        if not self._dir.exists():
            return []
        presets = []
        for path in sorted(self._dir.glob("*.yaml")):
            meta = self.load_preset_metadata(path.stem)
            if meta is not None:
                presets.append(meta)
        return presets

    def list_presets_filtered(
        self,
        experiment_mode: str = "",
        tag: str = "",
    ) -> list[ExperimentPreset]:
        """Return presets filtered by experiment mode and/or tag.

        Args:
            experiment_mode: If non-empty, only presets matching
                this mode (or with empty mode) are included.
            tag: If non-empty, only presets containing this tag
                (case-insensitive substring match).
        """
        presets = self.list_presets()
        if experiment_mode:
            presets = [
                p for p in presets
                if not p.experiment_mode
                or p.experiment_mode == experiment_mode
            ]
        if tag:
            tag_lower = tag.strip().lower()
            presets = [
                p for p in presets
                if any(
                    tag_lower in t.lower() for t in p.tags
                )
            ]
        return presets

    def delete_preset(self, name: str) -> bool:
        """Delete a preset file.

        Returns ``True`` if the file existed and was removed.
        """
        path = self._preset_path(name)
        if path.exists():
            path.unlink()
            logger.info("Deleted preset: %s", name)
            return True
        return False

    def preset_exists(self, name: str) -> bool:
        """Check whether a preset with the given name exists."""
        return self._preset_path(name).exists()

    # -- Internal ----------------------------------------------------- #

    def _preset_path(self, name: str) -> Path:
        slug = (
            name.strip()
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
        )
        return self._dir / f"{slug}.yaml"

    def _write(
        self,
        preset: ExperimentPreset,
        config: FlocroscopeConfig,
    ) -> None:
        from flocroscope.config.loader import _dataclass_to_dict

        self._dir.mkdir(parents=True, exist_ok=True)
        data = {
            "preset": {
                "name": preset.name,
                "description": preset.description,
                "author": preset.author,
                "created_at": preset.created_at,
                "updated_at": preset.updated_at,
                "experiment_mode": preset.experiment_mode,
                "tags": preset.tags,
            },
            "config": _dataclass_to_dict(config),
        }
        path = self._preset_path(preset.name)
        with open(path, "w") as f:
            yaml.dump(
                data, f,
                default_flow_style=False,
                sort_keys=False,
            )
