"""Optogenetics LED controller.

Publishes LED commands over a ZMQ PUB socket.  The receiving end
(typically an Arduino or ESP32 running a ZMQ SUB subscriber) applies
the command to the physical LED.

Commands are serialized as JSON.  Example subscriber (Arduino side)
receives messages like::

    {"command": "pulse", "intensity": 0.8, "duration_ms": 50, "channel": 0}

Requires ``pyzmq``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flocroscope.comms.base import Endpoint, LedCommand

logger = logging.getLogger(__name__)


class LedController(Endpoint):
    """ZMQ PUB endpoint for optogenetics LED control.

    This is a *sender* endpoint — it publishes commands rather
    than receiving data.  :meth:`poll` always returns ``None``.

    Args:
        port: ZMQ PUB port to bind on.
        host: Bind address.
    """

    def __init__(
        self,
        port: int = 5001,
        host: str = "*",
    ) -> None:
        self._host = host
        self._port = port
        self._ctx = None
        self._socket = None
        self._connected = False

    def start(self) -> None:
        """Bind the ZMQ PUB socket."""
        import zmq

        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.PUB)
        self._socket.bind(f"tcp://{self._host}:{self._port}")
        self._connected = True
        logger.info("LedController PUB bound on tcp://*:%d", self._port)

    def stop(self) -> None:
        """Close the socket and context."""
        if self._socket is not None:
            self._socket.close(linger=100)
            self._socket = None
        if self._ctx is not None:
            self._ctx.term()
            self._ctx = None
        self._connected = False
        logger.info("LedController stopped")

    def poll(self) -> None:
        """No-op — this endpoint only sends."""
        return None

    @property
    def connected(self) -> bool:
        """Whether the PUB socket is bound."""
        return self._connected

    def send_command(self, cmd: LedCommand) -> None:
        """Publish an LED command.

        Args:
            cmd: The command to send.
        """
        if self._socket is None:
            logger.warning("LedController: not started, dropping command")
            return

        payload = json.dumps({
            "command": cmd.command,
            "intensity": cmd.intensity,
            "duration_ms": cmd.duration_ms,
            "channel": cmd.channel,
        })
        self._socket.send_string(payload)
        logger.debug("LED cmd: %s", payload)

    def on(self, intensity: float = 1.0, channel: int = 0) -> None:
        """Turn LED on at the given intensity."""
        self.send_command(LedCommand(
            command="on", intensity=intensity, channel=channel,
        ))

    def off(self, channel: int = 0) -> None:
        """Turn LED off."""
        self.send_command(LedCommand(
            command="off", intensity=0.0, channel=channel,
        ))

    def pulse(
        self,
        intensity: float = 1.0,
        duration_ms: float = 50.0,
        channel: int = 0,
    ) -> None:
        """Send a single pulse."""
        self.send_command(LedCommand(
            command="pulse",
            intensity=intensity,
            duration_ms=duration_ms,
            channel=channel,
        ))
