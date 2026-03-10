"""FicTrac treadmill tracking receiver.

Connects to FicTrac's socket output (configurable as TCP or UDP)
and parses the 25-column CSV data into :class:`FicTracFrame`
objects.  Runs in a background thread so the render loop is never
blocked.

FicTrac output format reference:
    https://github.com/rjdmoore/fictrac/blob/master/doc/data_header.txt
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any

from flocroscope.comms.base import Endpoint, FicTracFrame

logger = logging.getLogger(__name__)

# Column indices (0-based) in FicTrac's 25-column CSV output.
_COL_FRAME = 0
_COL_DROT_LAB_X = 5
_COL_DROT_LAB_Y = 6
_COL_DROT_LAB_Z = 7
_COL_INTEG_X = 14
_COL_INTEG_Y = 15
_COL_HEADING = 16
_COL_DIRECTION = 17
_COL_SPEED = 18
_COL_TIMESTAMP = 21
_COL_DT = 23
_NUM_COLS = 25


def parse_fictrac_line(line: str) -> FicTracFrame | None:
    """Parse a single line of FicTrac CSV output.

    Args:
        line: Comma-separated string with 25 columns.

    Returns:
        A :class:`FicTracFrame`, or ``None`` if parsing fails.
    """
    parts = line.strip().split(",")
    if len(parts) < _NUM_COLS:
        return None
    try:
        vals = [float(p) for p in parts[:_NUM_COLS]]
    except ValueError:
        return None

    return FicTracFrame(
        frame_count=int(vals[_COL_FRAME]),
        delta_rot_lab=(
            vals[_COL_DROT_LAB_X],
            vals[_COL_DROT_LAB_Y],
            vals[_COL_DROT_LAB_Z],
        ),
        heading_rad=vals[_COL_HEADING],
        x_rad=vals[_COL_INTEG_X],
        y_rad=vals[_COL_INTEG_Y],
        speed=vals[_COL_SPEED],
        direction_rad=vals[_COL_DIRECTION],
        timestamp_ms=vals[_COL_TIMESTAMP],
        dt_ms=vals[_COL_DT],
        raw=line.strip(),
    )


class FicTracReceiver(Endpoint):
    """Receive FicTrac data over a TCP socket.

    FicTrac sends one CSV line per frame.  This endpoint connects
    to FicTrac's socket output and stores the latest parsed frame
    in a thread-safe slot.

    Args:
        host: FicTrac host address.
        port: FicTrac socket port (matches ``sock_port`` in FicTrac
            config).
    """

    def __init__(self, host: str = "localhost", port: int = 2000) -> None:
        self._host = host
        self._port = port
        self._latest: FicTracFrame | None = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._connected = False

    def start(self) -> None:
        """Start the background receiver thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="fictrac-recv",
        )
        self._thread.start()
        logger.info(
            "FicTracReceiver started on %s:%d", self._host, self._port,
        )

    def stop(self) -> None:
        """Stop the receiver thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._connected = False
        logger.info("FicTracReceiver stopped")

    def poll(self) -> FicTracFrame | None:
        """Return the most recent frame, or ``None``.

        This is non-blocking and safe to call from the render thread.
        """
        with self._lock:
            frame = self._latest
            self._latest = None
            return frame

    @property
    def connected(self) -> bool:
        """Whether a connection to FicTrac is active."""
        return self._connected

    def _run(self) -> None:
        """Background thread: connect and receive data."""
        buf = ""
        while self._running:
            try:
                with socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM,
                ) as sock:
                    sock.settimeout(2.0)
                    sock.connect((self._host, self._port))
                    self._connected = True
                    logger.info(
                        "Connected to FicTrac at %s:%d",
                        self._host, self._port,
                    )

                    while self._running:
                        try:
                            data = sock.recv(4096)
                        except socket.timeout:
                            continue
                        if not data:
                            break

                        buf += data.decode("ascii", errors="replace")
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            frame = parse_fictrac_line(line)
                            if frame is not None:
                                with self._lock:
                                    self._latest = frame

            except OSError as exc:
                if self._running:
                    logger.debug(
                        "FicTrac connection failed: %s (retrying)",
                        exc,
                    )
            finally:
                self._connected = False

            # Brief wait before reconnecting
            if self._running:
                import time
                time.sleep(1.0)
