"""ScanImage 2-photon microscopy synchronization.

Runs a TCP server that accepts connections from ScanImage (MATLAB).
Messages are newline-delimited JSON.  Example MATLAB client::

    t = tcpclient("localhost", 5000);
    writeline(t, '{"type":"trial_start","trial_id":1}');

The server is fully optional — if ScanImage is not connected the
stimulus runs normally.
"""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from typing import Any

from virtual_reality.comms.base import Endpoint, TrialEvent

logger = logging.getLogger(__name__)


class ScanImageSync(Endpoint):
    """TCP server for ScanImage synchronization.

    Listens for incoming TCP connections and parses newline-delimited
    JSON messages into :class:`TrialEvent` objects.

    Expected JSON format::

        {"type": "trial_start", "trial_id": 1, "params": {...}}
        {"type": "trial_stop"}
        {"type": "frame_clock", "frame": 42}

    Args:
        port: TCP port to listen on.
        host: Bind address (default ``"0.0.0.0"`` to accept any).
    """

    def __init__(
        self,
        port: int = 5000,
        host: str = "0.0.0.0",
    ) -> None:
        self._host = host
        self._port = port
        self._queue: queue.Queue[TrialEvent] = queue.Queue(maxsize=1000)
        self._running = False
        self._thread: threading.Thread | None = None
        self._connected = False

    def start(self) -> None:
        """Start the TCP server thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="scanimage-sync",
        )
        self._thread.start()
        logger.info(
            "ScanImageSync listening on %s:%d", self._host, self._port,
        )

    def stop(self) -> None:
        """Stop the server thread."""
        self._running = False
        # Connect to self to unblock accept()
        try:
            with socket.socket() as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", self._port))
        except OSError:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._connected = False
        logger.info("ScanImageSync stopped")

    def poll(self) -> list[TrialEvent]:
        """Drain and return all queued events.

        Returns an empty list if no events are pending.
        """
        events: list[TrialEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    @property
    def connected(self) -> bool:
        """Whether a ScanImage client is connected."""
        return self._connected

    def _run(self) -> None:
        """Background thread: accept connections and read messages."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.settimeout(1.0)
        srv.bind((self._host, self._port))
        srv.listen(1)

        try:
            while self._running:
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue
                if not self._running:
                    conn.close()
                    break

                logger.info("ScanImage connected from %s", addr)
                self._connected = True
                self._handle_client(conn)
                self._connected = False
                logger.info("ScanImage disconnected")
        finally:
            srv.close()

    def _handle_client(self, conn: socket.socket) -> None:
        """Read newline-delimited JSON from one client."""
        conn.settimeout(1.0)
        buf = ""
        try:
            while self._running:
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break

                buf += data.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    event = self._parse_message(line)
                    if event is not None:
                        try:
                            self._queue.put_nowait(event)
                        except queue.Full:
                            logger.warning("ScanImage event queue full")
        except OSError:
            pass
        finally:
            conn.close()

    def _parse_message(self, line: str) -> TrialEvent | None:
        """Parse a JSON line into a TrialEvent."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from ScanImage: %s", line[:80])
            return None

        if not isinstance(data, dict):
            return None

        event_type = data.pop("type", "unknown")
        return TrialEvent(
            event_type=str(event_type),
            timestamp=time.time(),
            metadata=data,
        )
