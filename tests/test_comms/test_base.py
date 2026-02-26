"""Tests for comms base types."""

from __future__ import annotations

import pytest

from virtual_reality.comms.base import (
    FicTracFrame,
    LedCommand,
    PresenterCommand,
    PresenterStatus,
    TrialEvent,
)


class TestFicTracFrame:
    """Tests for FicTracFrame dataclass."""

    def test_defaults(self) -> None:
        """Default frame has zero values."""
        f = FicTracFrame()
        assert f.frame_count == 0
        assert f.heading_rad == 0.0
        assert f.x_rad == 0.0
        assert f.y_rad == 0.0
        assert f.speed == 0.0
        assert f.raw == ""

    def test_delta_rot_default(self) -> None:
        """Delta rotation defaults to zero tuple."""
        f = FicTracFrame()
        assert f.delta_rot_lab == (0.0, 0.0, 0.0)

    def test_custom_values(self) -> None:
        """Custom values are stored correctly."""
        f = FicTracFrame(
            frame_count=10, heading_rad=1.5,
            x_rad=2.0, y_rad=-1.0,
        )
        assert f.frame_count == 10
        assert f.heading_rad == 1.5


class TestTrialEvent:
    """Tests for TrialEvent dataclass."""

    def test_defaults(self) -> None:
        """Default event has empty type and metadata."""
        ev = TrialEvent()
        assert ev.event_type == ""
        assert ev.timestamp == 0.0
        assert ev.metadata == {}

    def test_metadata_independent(self) -> None:
        """Each event gets its own metadata dict."""
        ev1 = TrialEvent()
        ev2 = TrialEvent()
        ev1.metadata["key"] = "value"
        assert "key" not in ev2.metadata


class TestPresenterStatus:
    """Tests for PresenterStatus dataclass."""

    def test_defaults(self) -> None:
        """Default status is unknown."""
        s = PresenterStatus()
        assert s.state == "unknown"
        assert s.position_mm == 0.0
        assert s.error == ""


class TestPresenterCommand:
    """Tests for PresenterCommand dataclass."""

    def test_defaults(self) -> None:
        """Default command is retract."""
        cmd = PresenterCommand()
        assert cmd.command == "retract"
        assert cmd.position_mm == 0.0

    def test_position_command(self) -> None:
        """Position command with target."""
        cmd = PresenterCommand(command="position", position_mm=15.0)
        assert cmd.position_mm == 15.0
