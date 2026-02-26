"""Tests for the LED controller endpoint."""

from __future__ import annotations

import json

import pytest

from virtual_reality.comms.base import LedCommand


class TestLedCommand:
    """Tests for LedCommand dataclass."""

    def test_defaults(self) -> None:
        """Default LedCommand is off with zero intensity."""
        cmd = LedCommand()
        assert cmd.command == "off"
        assert cmd.intensity == 0.0
        assert cmd.duration_ms == 0.0
        assert cmd.channel == 0

    def test_on_command(self) -> None:
        """On command with intensity."""
        cmd = LedCommand(command="on", intensity=0.8)
        assert cmd.command == "on"
        assert abs(cmd.intensity - 0.8) < 1e-6

    def test_pulse_command(self) -> None:
        """Pulse command with duration."""
        cmd = LedCommand(
            command="pulse", intensity=1.0,
            duration_ms=50.0, channel=1,
        )
        assert cmd.command == "pulse"
        assert cmd.duration_ms == 50.0
        assert cmd.channel == 1

    def test_serialization(self) -> None:
        """Command can be serialized to JSON."""
        cmd = LedCommand(
            command="pulse", intensity=0.5,
            duration_ms=100.0, channel=2,
        )
        payload = json.dumps({
            "command": cmd.command,
            "intensity": cmd.intensity,
            "duration_ms": cmd.duration_ms,
            "channel": cmd.channel,
        })
        data = json.loads(payload)
        assert data["command"] == "pulse"
        assert data["intensity"] == 0.5
        assert data["channel"] == 2


class TestLedController:
    """Tests for LedController (requires pyzmq)."""

    def test_instantiation(self) -> None:
        """Controller creates without starting."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.led import LedController
        ctrl = LedController(port=0)
        assert not ctrl.connected
        assert ctrl.poll() is None

    def test_start_stop(self) -> None:
        """Controller starts and stops cleanly."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.led import LedController

        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

        ctrl = LedController(port=port)
        ctrl.start()
        assert ctrl.connected
        ctrl.stop()
        assert not ctrl.connected

    def test_send_without_start(self) -> None:
        """Sending without starting logs warning but doesn't crash."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.led import LedController
        ctrl = LedController(port=0)
        ctrl.send_command(LedCommand(command="on", intensity=1.0))
