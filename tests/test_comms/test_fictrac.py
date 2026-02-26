"""Tests for FicTrac receiver and line parsing."""

from __future__ import annotations

import math

import pytest

from virtual_reality.comms.base import FicTracFrame
from virtual_reality.comms.fictrac import (
    _COL_DIRECTION,
    _COL_DROT_LAB_X,
    _COL_DROT_LAB_Y,
    _COL_DROT_LAB_Z,
    _COL_DT,
    _COL_FRAME,
    _COL_HEADING,
    _COL_INTEG_X,
    _COL_INTEG_Y,
    _COL_SPEED,
    _COL_TIMESTAMP,
    _NUM_COLS,
    parse_fictrac_line,
)


def _make_fictrac_line(**overrides: float) -> str:
    """Build a synthetic 25-column FicTrac CSV line.

    Args:
        **overrides: Column index → value overrides.
    """
    cols = [0.0] * _NUM_COLS
    cols[_COL_FRAME] = 1.0
    for idx, val in overrides.items():
        cols[int(idx)] = val
    return ",".join(f"{v}" for v in cols)


class TestParseFicTracLine:
    """Tests for :func:`parse_fictrac_line`."""

    def test_valid_25_columns(self) -> None:
        """Correctly parses a full 25-column line."""
        cols = [float(i) for i in range(_NUM_COLS)]
        line = ",".join(str(v) for v in cols)
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert frame.frame_count == 0
        assert frame.x_rad == float(_COL_INTEG_X)
        assert frame.y_rad == float(_COL_INTEG_Y)
        assert frame.heading_rad == float(_COL_HEADING)
        assert frame.speed == float(_COL_SPEED)

    def test_frame_count(self) -> None:
        """Frame counter is parsed as integer."""
        line = _make_fictrac_line(**{str(_COL_FRAME): 42.0})
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert frame.frame_count == 42

    def test_heading_preserved(self) -> None:
        """Heading value passes through in radians."""
        heading = 1.5707
        line = _make_fictrac_line(**{str(_COL_HEADING): heading})
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert abs(frame.heading_rad - heading) < 1e-4

    def test_delta_rotation_lab(self) -> None:
        """Delta rotation vector is extracted from cols 6-8."""
        line = _make_fictrac_line(**{
            str(_COL_DROT_LAB_X): 0.1,
            str(_COL_DROT_LAB_Y): 0.2,
            str(_COL_DROT_LAB_Z): 0.3,
        })
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert abs(frame.delta_rot_lab[0] - 0.1) < 1e-6
        assert abs(frame.delta_rot_lab[1] - 0.2) < 1e-6
        assert abs(frame.delta_rot_lab[2] - 0.3) < 1e-6

    def test_integrated_position(self) -> None:
        """Integrated x/y are parsed from cols 15-16."""
        line = _make_fictrac_line(**{
            str(_COL_INTEG_X): 3.14,
            str(_COL_INTEG_Y): -1.57,
        })
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert abs(frame.x_rad - 3.14) < 1e-6
        assert abs(frame.y_rad - (-1.57)) < 1e-6

    def test_timestamp_and_dt(self) -> None:
        """Timestamp and dt are parsed from cols 22/24."""
        line = _make_fictrac_line(**{
            str(_COL_TIMESTAMP): 1234.5,
            str(_COL_DT): 6.7,
        })
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert abs(frame.timestamp_ms - 1234.5) < 1e-6
        assert abs(frame.dt_ms - 6.7) < 1e-6

    def test_raw_line_stored(self) -> None:
        """The raw CSV line is stored on the frame."""
        line = _make_fictrac_line()
        frame = parse_fictrac_line(line)
        assert frame is not None
        assert frame.raw == line.strip()

    def test_too_few_columns_returns_none(self) -> None:
        """Lines with fewer than 25 columns are rejected."""
        line = ",".join(str(i) for i in range(10))
        assert parse_fictrac_line(line) is None

    def test_non_numeric_returns_none(self) -> None:
        """Lines with non-numeric values are rejected."""
        cols = ["hello"] * _NUM_COLS
        line = ",".join(cols)
        assert parse_fictrac_line(line) is None

    def test_empty_string_returns_none(self) -> None:
        """An empty string returns None."""
        assert parse_fictrac_line("") is None

    def test_trailing_newline(self) -> None:
        """Lines with trailing newline are handled."""
        line = _make_fictrac_line() + "\n"
        frame = parse_fictrac_line(line)
        assert frame is not None

    def test_extra_columns_tolerated(self) -> None:
        """Lines with more than 25 columns still parse."""
        cols = [float(i) for i in range(30)]
        line = ",".join(str(v) for v in cols)
        frame = parse_fictrac_line(line)
        assert frame is not None


class TestFicTracReceiver:
    """Tests for :class:`FicTracReceiver` lifecycle."""

    def test_instantiation(self) -> None:
        """Receiver creates without starting."""
        from virtual_reality.comms.fictrac import FicTracReceiver
        recv = FicTracReceiver(host="localhost", port=0)
        assert not recv.connected
        assert recv.poll() is None

    def test_stop_without_start(self) -> None:
        """Stopping before starting is a no-op."""
        from virtual_reality.comms.fictrac import FicTracReceiver
        recv = FicTracReceiver(host="localhost", port=0)
        recv.stop()
        assert not recv.connected
