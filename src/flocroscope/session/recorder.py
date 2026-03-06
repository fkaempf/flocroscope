"""Per-frame data recorder for experiment sessions.

Writes timestamped fly position, heading, and FicTrac data to a
CSV file during experiments.  The recorder is designed to be called
once per frame from the stimulus update loop.

Example::

    recorder = FrameRecorder(output_dir / "frames.csv")
    recorder.start()
    # in render loop:
    recorder.record(time.time(), fly_x=1.0, fly_y=2.0, heading=90.0)
    # on exit:
    recorder.stop()
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default columns written to the CSV
DEFAULT_COLUMNS = [
    "timestamp",
    "frame",
    "fly_x",
    "fly_y",
    "fly_heading_deg",
    "fly_speed",
    "cam_x",
    "cam_y",
    "cam_heading_deg",
    "fictrac_heading_rad",
    "fictrac_x_rad",
    "fictrac_y_rad",
    "fictrac_speed",
]


class FrameRecorder:
    """Records per-frame data to a CSV file.

    Buffers writes and flushes periodically to avoid I/O overhead
    every frame.

    Args:
        path: Output CSV file path.
        columns: Column names for the CSV header.  Defaults to
            :data:`DEFAULT_COLUMNS`.
        flush_interval: Seconds between forced file flushes.
    """

    def __init__(
        self,
        path: str | Path,
        columns: list[str] | None = None,
        flush_interval: float = 1.0,
    ) -> None:
        self._path = Path(path)
        self._columns = columns or list(DEFAULT_COLUMNS)
        self._flush_interval = flush_interval
        self._file = None
        self._writer: csv.DictWriter | None = None
        self._frame_count = 0
        self._last_flush = 0.0
        self._started = False

    @property
    def frame_count(self) -> int:
        """Number of frames recorded."""
        return self._frame_count

    @property
    def path(self) -> Path:
        """Output CSV file path."""
        return self._path

    def start(self) -> None:
        """Open the CSV file and write the header."""
        if self._started:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "w", newline="")
        self._writer = csv.DictWriter(
            self._file,
            fieldnames=self._columns,
            extrasaction="ignore",
        )
        self._writer.writeheader()
        self._frame_count = 0
        self._last_flush = time.time()
        self._started = True
        logger.info("FrameRecorder started: %s", self._path)

    def stop(self) -> None:
        """Flush and close the CSV file."""
        if not self._started:
            return

        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
        self._writer = None
        self._started = False
        logger.info(
            "FrameRecorder stopped: %d frames written to %s",
            self._frame_count, self._path,
        )

    def record(self, **data: Any) -> None:
        """Record one frame of data.

        Missing columns are written as empty strings.  Extra keys
        not in the column list are silently ignored.

        Args:
            **data: Column name → value pairs.
        """
        if not self._started or self._writer is None:
            return

        self._frame_count += 1
        row = {"frame": self._frame_count}
        if "timestamp" not in data:
            row["timestamp"] = time.time()
        row.update(data)

        self._writer.writerow(row)

        # Periodic flush
        now = time.time()
        if now - self._last_flush >= self._flush_interval:
            self._file.flush()
            self._last_flush = now

    def record_dict(self, data: dict[str, Any]) -> None:
        """Record one frame from a dict (alternative to kwargs).

        Args:
            data: Column name → value pairs.
        """
        self.record(**data)
