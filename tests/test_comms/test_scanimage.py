"""Tests for ScanImage synchronization endpoint."""

from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from flocroscope.comms.scanimage import ScanImageSync


def _wait_for_port(port: int, timeout: float = 2.0) -> bool:
    """Wait until a TCP port is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.socket() as s:
                s.settimeout(0.1)
                s.connect(("127.0.0.1", port))
            return True
        except OSError:
            time.sleep(0.05)
    return False


def _find_free_port() -> int:
    """Find an available TCP port."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestScanImageSync:
    """Tests for the ScanImage TCP server."""

    def test_instantiation(self) -> None:
        """Server creates without starting."""
        sync = ScanImageSync(port=0)
        assert not sync.connected
        assert sync.poll() == []

    def test_start_stop(self) -> None:
        """Server starts and stops cleanly."""
        port = _find_free_port()
        sync = ScanImageSync(port=port, host="127.0.0.1")
        sync.start()
        try:
            assert _wait_for_port(port)
        finally:
            sync.stop()
        assert not sync.connected

    def test_receive_trial_start(self) -> None:
        """Server receives and parses a trial_start message."""
        port = _find_free_port()
        sync = ScanImageSync(port=port, host="127.0.0.1")
        sync.start()
        try:
            assert _wait_for_port(port)

            with socket.socket() as client:
                client.settimeout(2.0)
                client.connect(("127.0.0.1", port))
                msg = json.dumps({
                    "type": "trial_start", "trial_id": 1,
                }) + "\n"
                client.sendall(msg.encode())
                time.sleep(0.2)

            events = sync.poll()
            assert len(events) == 1
            assert events[0].event_type == "trial_start"
            assert events[0].metadata["trial_id"] == 1
        finally:
            sync.stop()

    def test_multiple_messages(self) -> None:
        """Multiple messages are queued and drained."""
        port = _find_free_port()
        sync = ScanImageSync(port=port, host="127.0.0.1")
        sync.start()
        try:
            assert _wait_for_port(port)

            with socket.socket() as client:
                client.settimeout(2.0)
                client.connect(("127.0.0.1", port))
                for i in range(3):
                    msg = json.dumps({
                        "type": "frame_clock", "frame": i,
                    }) + "\n"
                    client.sendall(msg.encode())
                time.sleep(0.3)

            events = sync.poll()
            assert len(events) == 3
            for i, ev in enumerate(events):
                assert ev.event_type == "frame_clock"
                assert ev.metadata["frame"] == i
        finally:
            sync.stop()

    def test_invalid_json_ignored(self) -> None:
        """Invalid JSON lines are silently ignored."""
        port = _find_free_port()
        sync = ScanImageSync(port=port, host="127.0.0.1")
        sync.start()
        try:
            assert _wait_for_port(port)

            with socket.socket() as client:
                client.settimeout(2.0)
                client.connect(("127.0.0.1", port))
                client.sendall(b"not valid json\n")
                msg = json.dumps({"type": "trial_stop"}) + "\n"
                client.sendall(msg.encode())
                time.sleep(0.2)

            events = sync.poll()
            assert len(events) == 1
            assert events[0].event_type == "trial_stop"
        finally:
            sync.stop()

    def test_poll_empty_when_no_data(self) -> None:
        """Poll returns empty list when no messages received."""
        port = _find_free_port()
        sync = ScanImageSync(port=port, host="127.0.0.1")
        sync.start()
        try:
            assert _wait_for_port(port)
            events = sync.poll()
            assert events == []
        finally:
            sync.stop()

    def test_poll_drains_queue(self) -> None:
        """Second poll returns empty after first drains all."""
        port = _find_free_port()
        sync = ScanImageSync(port=port, host="127.0.0.1")
        sync.start()
        try:
            assert _wait_for_port(port)

            with socket.socket() as client:
                client.settimeout(2.0)
                client.connect(("127.0.0.1", port))
                msg = json.dumps({"type": "trial_start"}) + "\n"
                client.sendall(msg.encode())
                time.sleep(0.2)

            events1 = sync.poll()
            assert len(events1) == 1
            events2 = sync.poll()
            assert events2 == []
        finally:
            sync.stop()
