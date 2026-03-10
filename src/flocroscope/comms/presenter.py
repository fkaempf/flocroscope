"""Fly presenter positioning controller.

Sends commands to an external fly-presenter mechanism over a ZMQ
REQ/REP socket.  The presenter controller (e.g. a microcontroller
running a ZMQ REP server) executes the command and replies with a
status message.

Commands are serialized as JSON.  Replies are expected as::

    {"state": "idle", "position_mm": 12.5, "error": ""}

The :meth:`send_command` call is threaded so it does not block the
render loop.

Requires ``pyzmq``.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from flocroscope.comms.base import (
    Endpoint,
    PresenterCommand,
    PresenterStatus,
)

logger = logging.getLogger(__name__)


class FlyPresenter(Endpoint):
    """ZMQ REQ endpoint for fly presenter positioning.

    Args:
        host: Presenter controller host.
        port: Presenter controller port.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5002,
    ) -> None:
        self._host = host
        self._port = port
        self._ctx = None
        self._socket = None
        self._connected = False
        self._lock = threading.Lock()
        self._latest_status: PresenterStatus | None = None

    def start(self) -> None:
        """Connect the ZMQ REQ socket."""
        import zmq

        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.setsockopt(zmq.RCVTIMEO, 2000)
        self._socket.setsockopt(zmq.SNDTIMEO, 2000)
        self._socket.connect(
            f"tcp://{self._host}:{self._port}",
        )
        self._connected = True
        logger.info(
            "FlyPresenter connected to tcp://%s:%d",
            self._host, self._port,
        )

    def stop(self) -> None:
        """Close the socket and context."""
        if self._socket is not None:
            self._socket.close(linger=100)
            self._socket = None
        if self._ctx is not None:
            self._ctx.term()
            self._ctx = None
        self._connected = False
        logger.info("FlyPresenter stopped")

    def poll(self) -> PresenterStatus | None:
        """Return the latest status from the presenter.

        Returns:
            The most recent :class:`PresenterStatus`, or ``None``.
        """
        with self._lock:
            status = self._latest_status
            self._latest_status = None
            return status

    @property
    def connected(self) -> bool:
        """Whether the REQ socket is connected."""
        return self._connected

    def send_command(self, cmd: PresenterCommand) -> None:
        """Send a command to the presenter (threaded).

        The actual send/recv happens in a background thread so the
        render loop is not blocked by the REQ/REP round-trip.

        Args:
            cmd: The command to send.
        """
        t = threading.Thread(
            target=self._do_send, args=(cmd,),
            daemon=True, name="presenter-send",
        )
        t.start()

    def _do_send(self, cmd: PresenterCommand) -> None:
        """Send command and store reply."""
        if self._socket is None:
            return
        payload = json.dumps({
            "command": cmd.command,
            "position_mm": cmd.position_mm,
        })
        try:
            self._socket.send_string(payload)
            reply = self._socket.recv_string()
            data = json.loads(reply)
            status = PresenterStatus(
                state=data.get("state", "unknown"),
                position_mm=data.get("position_mm", 0.0),
                error=data.get("error", ""),
            )
            with self._lock:
                self._latest_status = status
        except Exception as exc:
            logger.warning("Presenter command failed: %s", exc)
            self._connected = False

    def present(self) -> None:
        """Move the presenter into the arena."""
        self.send_command(PresenterCommand(command="present"))

    def retract(self) -> None:
        """Retract the presenter."""
        self.send_command(PresenterCommand(command="retract"))

    def move_to(self, position_mm: float) -> None:
        """Move to a specific position."""
        self.send_command(PresenterCommand(
            command="position", position_mm=position_mm,
        ))
