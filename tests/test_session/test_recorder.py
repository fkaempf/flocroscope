"""Tests for the per-frame data recorder."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from flocroscope.session.recorder import (
    DEFAULT_COLUMNS,
    FrameRecorder,
)


class TestFrameRecorder:
    """Tests for FrameRecorder."""

    def test_start_creates_file(self, tmp_path: Path) -> None:
        """Starting the recorder creates the CSV file."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path)
        rec.start()
        rec.stop()
        assert path.exists()

    def test_header_written(self, tmp_path: Path) -> None:
        """CSV file starts with a header row."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path)
        rec.start()
        rec.stop()

        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == DEFAULT_COLUMNS

    def test_custom_columns(self, tmp_path: Path) -> None:
        """Custom column names are used."""
        path = tmp_path / "test.csv"
        cols = ["timestamp", "x", "y"]
        rec = FrameRecorder(path, columns=cols)
        rec.start()
        rec.stop()

        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == cols

    def test_record_one_frame(self, tmp_path: Path) -> None:
        """Recording one frame writes one data row."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path, columns=["frame", "fly_x", "fly_y"])
        rec.start()
        rec.record(fly_x=1.0, fly_y=2.0)
        rec.stop()

        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2  # header + 1 row

    def test_record_multiple_frames(self, tmp_path: Path) -> None:
        """Multiple frames accumulate in the CSV."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path, columns=["frame", "fly_x"])
        rec.start()
        for i in range(10):
            rec.record(fly_x=float(i))
        rec.stop()

        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 11  # header + 10 rows

    def test_frame_count(self, tmp_path: Path) -> None:
        """frame_count tracks number of recorded frames."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path, columns=["frame"])
        rec.start()
        assert rec.frame_count == 0
        rec.record()
        rec.record()
        assert rec.frame_count == 2
        rec.stop()

    def test_frame_number_auto_increments(
        self, tmp_path: Path,
    ) -> None:
        """Frame number column auto-increments."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(
            path, columns=["frame", "fly_x"],
        )
        rec.start()
        rec.record(fly_x=0.0)
        rec.record(fly_x=1.0)
        rec.stop()

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["frame"] == "1"
        assert rows[1]["frame"] == "2"

    def test_extra_keys_ignored(self, tmp_path: Path) -> None:
        """Keys not in column list are silently dropped."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path, columns=["frame", "fly_x"])
        rec.start()
        rec.record(fly_x=1.0, unknown_field=99)
        rec.stop()

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert "unknown_field" not in rows[0]

    def test_missing_columns_empty(self, tmp_path: Path) -> None:
        """Missing columns are written as empty strings."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(
            path, columns=["frame", "fly_x", "fly_y"],
        )
        rec.start()
        rec.record(fly_x=1.0)  # no fly_y
        rec.stop()

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["fly_y"] == ""

    def test_record_before_start_noop(
        self, tmp_path: Path,
    ) -> None:
        """Recording before start is silently ignored."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path)
        rec.record(fly_x=1.0)  # should not raise
        assert rec.frame_count == 0

    def test_stop_without_start_noop(
        self, tmp_path: Path,
    ) -> None:
        """Stopping before starting is a no-op."""
        rec = FrameRecorder(tmp_path / "test.csv")
        rec.stop()  # should not raise

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Parent directories are created if needed."""
        path = tmp_path / "a" / "b" / "test.csv"
        rec = FrameRecorder(path)
        rec.start()
        rec.stop()
        assert path.exists()

    def test_record_dict(self, tmp_path: Path) -> None:
        """record_dict works as alternative to kwargs."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(
            path, columns=["frame", "fly_x", "fly_y"],
        )
        rec.start()
        rec.record_dict({"fly_x": 3.0, "fly_y": 4.0})
        rec.stop()

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["fly_x"] == "3.0"

    def test_path_property(self, tmp_path: Path) -> None:
        """path property returns the file path."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path)
        assert rec.path == path

    def test_double_start_ignored(self, tmp_path: Path) -> None:
        """Starting twice is a no-op."""
        path = tmp_path / "test.csv"
        rec = FrameRecorder(path, columns=["frame"])
        rec.start()
        rec.record()
        rec.start()  # should not reset
        assert rec.frame_count == 1
        rec.stop()
