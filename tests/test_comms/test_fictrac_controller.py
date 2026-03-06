"""Tests for the FicTrac movement controller."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from flocroscope.comms.base import FicTracFrame
from flocroscope.comms.fictrac_controller import FicTracController


def _make_hub(frame: FicTracFrame | None = None) -> MagicMock:
    """Create a mock CommsHub that returns the given frame."""
    hub = MagicMock()
    hub.poll_fictrac.return_value = frame
    hub.fictrac = MagicMock()
    hub.fictrac.connected = frame is not None
    return hub


class TestFicTracController:
    """Tests for the FicTracController."""

    def test_initial_state(self) -> None:
        """Controller starts at origin with zero heading."""
        hub = _make_hub()
        ctrl = FicTracController(hub)
        assert ctrl.x == 0.0
        assert ctrl.y == 0.0
        assert ctrl.heading_deg == 0.0
        assert ctrl.speed == 0.0

    def test_no_frame_no_update(self) -> None:
        """Position unchanged when no FicTrac data available."""
        hub = _make_hub(frame=None)
        ctrl = FicTracController(hub)
        ctrl.update(0.01)
        assert ctrl.x == 0.0
        assert ctrl.y == 0.0

    def test_position_from_frame(self) -> None:
        """Position is computed from integrated radians * ball_radius."""
        frame = FicTracFrame(
            x_rad=1.0, y_rad=2.0,
            heading_rad=math.pi / 2,
            speed=0.5,
        )
        hub = _make_hub(frame)
        ctrl = FicTracController(
            hub, ball_radius_mm=4.5, arena_radius=40.0,
        )
        ctrl.update(0.01)
        assert abs(ctrl.x - 4.5) < 1e-6
        assert abs(ctrl.y - 9.0) < 1e-6

    def test_heading_from_frame(self) -> None:
        """Heading is converted from radians to degrees."""
        frame = FicTracFrame(heading_rad=math.pi)
        hub = _make_hub(frame)
        ctrl = FicTracController(hub)
        ctrl.update(0.01)
        assert abs(ctrl.heading_deg - 180.0) < 1e-4

    def test_heading_wraps_360(self) -> None:
        """Heading wraps around at 360 degrees."""
        frame = FicTracFrame(heading_rad=2 * math.pi + 0.1)
        hub = _make_hub(frame)
        ctrl = FicTracController(hub)
        ctrl.update(0.01)
        expected = math.degrees(0.1) % 360.0
        assert abs(ctrl.heading_deg - expected) < 0.1

    def test_heading_rad_property(self) -> None:
        """heading_rad property matches heading_deg."""
        frame = FicTracFrame(heading_rad=1.0)
        hub = _make_hub(frame)
        ctrl = FicTracController(hub)
        ctrl.update(0.01)
        assert abs(ctrl.heading_rad - math.radians(ctrl.heading_deg)) < 1e-6

    def test_gain_applied(self) -> None:
        """Gain multiplier scales position."""
        frame = FicTracFrame(x_rad=1.0, y_rad=1.0)
        hub = _make_hub(frame)
        ctrl = FicTracController(
            hub, ball_radius_mm=4.5, gain=2.0,
        )
        ctrl.update(0.01)
        assert abs(ctrl.x - 9.0) < 1e-6

    def test_clamped_to_arena(self) -> None:
        """Position is clamped to arena radius."""
        frame = FicTracFrame(x_rad=100.0, y_rad=0.0)
        hub = _make_hub(frame)
        ctrl = FicTracController(
            hub, ball_radius_mm=4.5, arena_radius=40.0,
        )
        ctrl.update(0.01)
        dist = math.sqrt(ctrl.x ** 2 + ctrl.y ** 2)
        assert dist <= 40.0 + 1e-6

    def test_frames_received_increments(self) -> None:
        """Frame counter increments with each update."""
        frame = FicTracFrame(x_rad=0.0, y_rad=0.0)
        hub = _make_hub(frame)
        ctrl = FicTracController(hub)
        assert ctrl.frames_received == 0
        ctrl.update(0.01)
        assert ctrl.frames_received == 1
        ctrl.update(0.01)
        assert ctrl.frames_received == 2

    def test_connected_property(self) -> None:
        """connected property delegates to hub."""
        hub = _make_hub(FicTracFrame())
        ctrl = FicTracController(hub)
        assert ctrl.connected is True

        hub.fictrac.connected = False
        assert ctrl.connected is False

    def test_speed_from_frame(self) -> None:
        """Speed is passed through from the frame."""
        frame = FicTracFrame(speed=1.23)
        hub = _make_hub(frame)
        ctrl = FicTracController(hub)
        ctrl.update(0.01)
        assert abs(ctrl.speed - 1.23) < 1e-6
