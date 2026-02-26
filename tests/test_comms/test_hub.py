"""Tests for the CommsHub central manager."""

from __future__ import annotations

import pytest

from virtual_reality.comms.base import (
    FicTracFrame,
    LedCommand,
    PresenterCommand,
    TrialEvent,
)
from virtual_reality.comms.hub import CommsHub
from virtual_reality.config.schema import CommsConfig


class TestCommsHubDisabled:
    """Tests for CommsHub with all endpoints disabled."""

    def test_all_ports_zero_starts_cleanly(self) -> None:
        """Hub with all ports=0 starts and stops without error."""
        cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,
            scanimage_port=0,
            led_port=0,
            presenter_port=0,
        )
        hub = CommsHub(cfg)
        hub.start_all()
        assert hub.fictrac is None
        assert hub.scanimage is None
        assert hub.led is None
        assert hub.presenter is None
        hub.stop_all()

    def test_poll_fictrac_returns_none(self) -> None:
        """poll_fictrac returns None when not configured."""
        cfg = CommsConfig(enabled=True, fictrac_port=0)
        hub = CommsHub(cfg)
        assert hub.poll_fictrac() is None

    def test_poll_scanimage_returns_empty(self) -> None:
        """poll_scanimage returns empty list when not configured."""
        cfg = CommsConfig(enabled=True, scanimage_port=0)
        hub = CommsHub(cfg)
        assert hub.poll_scanimage() == []

    def test_poll_presenter_returns_none(self) -> None:
        """poll_presenter returns None when not configured."""
        cfg = CommsConfig(enabled=True, presenter_port=0)
        hub = CommsHub(cfg)
        assert hub.poll_presenter() is None

    def test_send_led_noop_when_disabled(self) -> None:
        """send_led is a no-op when LED not configured."""
        cfg = CommsConfig(enabled=True, led_port=0)
        hub = CommsHub(cfg)
        hub.send_led(LedCommand(command="on", intensity=1.0))

    def test_send_presenter_noop_when_disabled(self) -> None:
        """send_presenter is a no-op when not configured."""
        cfg = CommsConfig(enabled=True, presenter_port=0)
        hub = CommsHub(cfg)
        hub.send_presenter(PresenterCommand(command="present"))

    def test_status_all_false(self) -> None:
        """Status reports all endpoints disconnected."""
        cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,
            scanimage_port=0,
            led_port=0,
            presenter_port=0,
        )
        hub = CommsHub(cfg)
        status = hub.status
        assert status == {
            "fictrac": False,
            "scanimage": False,
            "led": False,
            "presenter": False,
        }

    def test_stop_all_idempotent(self) -> None:
        """Calling stop_all multiple times is safe."""
        cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,
            scanimage_port=0,
            led_port=0,
            presenter_port=0,
        )
        hub = CommsHub(cfg)
        hub.start_all()
        hub.stop_all()
        hub.stop_all()


class TestCommsHubConfig:
    """Test CommsConfig dataclass defaults."""

    def test_default_disabled(self) -> None:
        """Comms is disabled by default."""
        cfg = CommsConfig()
        assert cfg.enabled is False

    def test_default_ports(self) -> None:
        """Default ports match expected values."""
        cfg = CommsConfig()
        assert cfg.fictrac_port == 2000
        assert cfg.scanimage_port == 5000
        assert cfg.led_port == 5001
        assert cfg.presenter_port == 5002

    def test_ball_radius_default(self) -> None:
        """Default ball radius is 4.5 mm."""
        cfg = CommsConfig()
        assert cfg.fictrac_ball_radius_mm == 4.5


class TestCommsHubIntegration:
    """Integration tests for CommsHub with real sockets."""

    def test_scanimage_endpoint_starts(self) -> None:
        """ScanImage endpoint starts when port > 0."""
        import socket as sock_mod

        # Find a free port
        with sock_mod.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

        cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,
            scanimage_port=port,
            led_port=0,
            presenter_port=0,
        )
        hub = CommsHub(cfg)
        hub.start_all()
        try:
            assert hub.scanimage is not None
        finally:
            hub.stop_all()
