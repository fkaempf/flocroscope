"""Tests for the fly presenter positioning endpoint."""

from __future__ import annotations

import json
import threading
from unittest.mock import MagicMock, patch

import pytest

from virtual_reality.comms.base import PresenterCommand, PresenterStatus


class TestPresenterCommand:
    """Tests for PresenterCommand dataclass."""

    def test_defaults(self) -> None:
        """Default PresenterCommand is retract with zero position."""
        cmd = PresenterCommand()
        assert cmd.command == "retract"
        assert cmd.position_mm == 0.0

    def test_present_command(self) -> None:
        """Present command with default position."""
        cmd = PresenterCommand(command="present")
        assert cmd.command == "present"
        assert cmd.position_mm == 0.0

    def test_position_command(self) -> None:
        """Position command with specific target."""
        cmd = PresenterCommand(command="position", position_mm=12.5)
        assert cmd.command == "position"
        assert abs(cmd.position_mm - 12.5) < 1e-6

    def test_serialization(self) -> None:
        """Command can be serialized to JSON."""
        cmd = PresenterCommand(command="position", position_mm=7.3)
        payload = json.dumps({
            "command": cmd.command,
            "position_mm": cmd.position_mm,
        })
        data = json.loads(payload)
        assert data["command"] == "position"
        assert abs(data["position_mm"] - 7.3) < 1e-6


class TestPresenterStatus:
    """Tests for PresenterStatus dataclass."""

    def test_defaults(self) -> None:
        """Default PresenterStatus is unknown with zero position."""
        status = PresenterStatus()
        assert status.state == "unknown"
        assert status.position_mm == 0.0
        assert status.error == ""

    def test_idle_status(self) -> None:
        """Idle status with position."""
        status = PresenterStatus(
            state="idle", position_mm=5.0, error="",
        )
        assert status.state == "idle"
        assert abs(status.position_mm - 5.0) < 1e-6
        assert status.error == ""

    def test_error_status(self) -> None:
        """Status with an error message."""
        status = PresenterStatus(
            state="error", position_mm=0.0, error="stall detected",
        )
        assert status.state == "error"
        assert status.error == "stall detected"


class TestFlyPresenter:
    """Tests for FlyPresenter endpoint."""

    def test_default_attributes(self) -> None:
        """FlyPresenter initialises with expected defaults."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        assert fp._host == "localhost"
        assert fp._port == 5002
        assert not fp.connected
        assert fp._socket is None

    def test_custom_host_port(self) -> None:
        """FlyPresenter accepts custom host and port."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter(host="192.168.1.10", port=9999)
        assert fp._host == "192.168.1.10"
        assert fp._port == 9999

    def test_start_requires_zmq(self) -> None:
        """start() imports zmq; verify it is importable."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

        fp = FlyPresenter(port=port)
        fp.start()
        assert fp.connected
        assert fp._socket is not None
        fp.stop()

    def test_start_stop(self) -> None:
        """Controller starts and stops cleanly."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

        fp = FlyPresenter(port=port)
        fp.start()
        assert fp.connected
        fp.stop()
        assert not fp.connected
        assert fp._socket is None
        assert fp._ctx is None

    def test_poll_returns_none_before_command(self) -> None:
        """poll() returns None when no command has been sent."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        assert fp.poll() is None

    def test_poll_returns_none_after_drain(self) -> None:
        """poll() returns None after the latest status has been consumed."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        # Manually inject a status to verify drain behaviour.
        fp._latest_status = PresenterStatus(state="idle")
        result = fp.poll()
        assert result is not None
        assert result.state == "idle"
        # Second poll should give None.
        assert fp.poll() is None

    def test_send_command_is_threaded(self) -> None:
        """send_command() dispatches work to a background thread."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        threads_before = threading.enumerate()
        # _socket is None so _do_send returns immediately, but the
        # thread should still be spawned.
        with patch.object(fp, "_do_send") as mock_send:
            event = threading.Event()
            original_do_send = mock_send.side_effect

            def _side_effect(cmd: PresenterCommand) -> None:
                event.set()

            mock_send.side_effect = _side_effect
            cmd = PresenterCommand(command="present")
            fp.send_command(cmd)
            # Wait for the thread to run _do_send.
            assert event.wait(timeout=2.0), "background thread did not run"
            mock_send.assert_called_once_with(cmd)

    def test_send_without_start(self) -> None:
        """Sending without starting doesn't crash (socket is None)."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        fp.send_command(PresenterCommand(command="present"))
        # _do_send exits early when _socket is None; no exception.

    def test_stop_before_start_is_noop(self) -> None:
        """Calling stop() before start() is safe."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        # Should not raise.
        fp.stop()
        assert not fp.connected
        assert fp._socket is None

    def test_present_convenience(self) -> None:
        """present() sends a 'present' command."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        with patch.object(fp, "send_command") as mock:
            fp.present()
            mock.assert_called_once()
            cmd = mock.call_args[0][0]
            assert isinstance(cmd, PresenterCommand)
            assert cmd.command == "present"

    def test_retract_convenience(self) -> None:
        """retract() sends a 'retract' command."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        with patch.object(fp, "send_command") as mock:
            fp.retract()
            mock.assert_called_once()
            cmd = mock.call_args[0][0]
            assert isinstance(cmd, PresenterCommand)
            assert cmd.command == "retract"

    def test_move_to_convenience(self) -> None:
        """move_to() sends a 'position' command with the target position."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        fp = FlyPresenter()
        with patch.object(fp, "send_command") as mock:
            fp.move_to(15.0)
            mock.assert_called_once()
            cmd = mock.call_args[0][0]
            assert isinstance(cmd, PresenterCommand)
            assert cmd.command == "position"
            assert abs(cmd.position_mm - 15.0) < 1e-6

    def test_double_stop_is_safe(self) -> None:
        """Calling stop() twice doesn't raise."""
        zmq = pytest.importorskip("zmq")
        from virtual_reality.comms.presenter import FlyPresenter

        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

        fp = FlyPresenter(port=port)
        fp.start()
        fp.stop()
        fp.stop()
        assert not fp.connected
