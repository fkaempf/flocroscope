"""Central communications hub.

Manages all endpoint lifecycles and provides a single interface
for the stimulus loop to poll data and send commands.  Every
endpoint is optional — the hub works with any subset of
endpoints enabled.

Example usage::

    from virtual_reality.config.schema import CommsConfig
    hub = CommsHub(CommsConfig(enabled=True, fictrac_port=2000))
    hub.start_all()
    # in render loop:
    frame = hub.poll_fictrac()
    events = hub.poll_scanimage()
    hub.send_led(LedCommand(command="pulse", intensity=0.8))
    # on exit:
    hub.stop_all()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from virtual_reality.comms.base import (
    FicTracFrame,
    LedCommand,
    PresenterCommand,
    PresenterStatus,
    TrialEvent,
)

if TYPE_CHECKING:
    from virtual_reality.comms.fictrac import FicTracReceiver
    from virtual_reality.comms.led import LedController
    from virtual_reality.comms.presenter import FlyPresenter
    from virtual_reality.comms.scanimage import ScanImageSync
    from virtual_reality.config.schema import CommsConfig

logger = logging.getLogger(__name__)


class CommsHub:
    """Central manager for all communication endpoints.

    Each endpoint is created only if its port is configured to a
    positive value.  Endpoints that fail to start are logged but
    do not prevent the rest from running.

    Args:
        config: Communications configuration dataclass.
    """

    def __init__(self, config: CommsConfig) -> None:
        self._config = config
        self.fictrac: FicTracReceiver | None = None
        self.scanimage: ScanImageSync | None = None
        self.led: LedController | None = None
        self.presenter: FlyPresenter | None = None

    def start_all(self) -> None:
        """Create and start all configured endpoints."""
        cfg = self._config

        if cfg.fictrac_port > 0:
            try:
                from virtual_reality.comms.fictrac import (
                    FicTracReceiver,
                )
                self.fictrac = FicTracReceiver(
                    host=cfg.fictrac_host, port=cfg.fictrac_port,
                )
                self.fictrac.start()
            except Exception as exc:
                logger.warning("FicTrac start failed: %s", exc)
                self.fictrac = None

        if cfg.scanimage_port > 0:
            try:
                from virtual_reality.comms.scanimage import (
                    ScanImageSync,
                )
                self.scanimage = ScanImageSync(port=cfg.scanimage_port)
                self.scanimage.start()
            except Exception as exc:
                logger.warning("ScanImage start failed: %s", exc)
                self.scanimage = None

        if cfg.led_port > 0:
            try:
                from virtual_reality.comms.led import LedController
                self.led = LedController(port=cfg.led_port)
                self.led.start()
            except Exception as exc:
                logger.warning("LED controller start failed: %s", exc)
                self.led = None

        if cfg.presenter_port > 0:
            try:
                from virtual_reality.comms.presenter import (
                    FlyPresenter,
                )
                self.presenter = FlyPresenter(
                    host=cfg.presenter_host, port=cfg.presenter_port,
                )
                self.presenter.start()
            except Exception as exc:
                logger.warning("Presenter start failed: %s", exc)
                self.presenter = None

        active = [
            name for name, ep in [
                ("fictrac", self.fictrac),
                ("scanimage", self.scanimage),
                ("led", self.led),
                ("presenter", self.presenter),
            ]
            if ep is not None
        ]
        logger.info("CommsHub started: %s", active or "(none)")

    def stop_all(self) -> None:
        """Stop all running endpoints."""
        for name, ep in [
            ("fictrac", self.fictrac),
            ("scanimage", self.scanimage),
            ("led", self.led),
            ("presenter", self.presenter),
        ]:
            if ep is not None:
                try:
                    ep.stop()
                except Exception as exc:
                    logger.warning("Error stopping %s: %s", name, exc)

        self.fictrac = None
        self.scanimage = None
        self.led = None
        self.presenter = None
        logger.info("CommsHub stopped")

    # --------------------------------------------------------- polling

    def poll_fictrac(self) -> FicTracFrame | None:
        """Get the latest FicTrac frame, or ``None``."""
        if self.fictrac is None:
            return None
        return self.fictrac.poll()

    def poll_scanimage(self) -> list[TrialEvent]:
        """Drain queued ScanImage events (may be empty)."""
        if self.scanimage is None:
            return []
        return self.scanimage.poll()

    def poll_presenter(self) -> PresenterStatus | None:
        """Get the latest presenter status, or ``None``."""
        if self.presenter is None:
            return None
        return self.presenter.poll()

    # -------------------------------------------------------- sending

    def send_led(self, cmd: LedCommand) -> None:
        """Publish an LED command (no-op if LED not configured)."""
        if self.led is not None:
            self.led.send_command(cmd)

    def send_presenter(self, cmd: PresenterCommand) -> None:
        """Send a presenter command (no-op if not configured)."""
        if self.presenter is not None:
            self.presenter.send_command(cmd)

    # ------------------------------------------------------- status

    @property
    def status(self) -> dict[str, bool]:
        """Connection status of all endpoints."""
        return {
            "fictrac": (
                self.fictrac.connected if self.fictrac else False
            ),
            "scanimage": (
                self.scanimage.connected if self.scanimage else False
            ),
            "led": self.led.connected if self.led else False,
            "presenter": (
                self.presenter.connected if self.presenter else False
            ),
        }


def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the CommsHub CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the CommsHub standalone for testing.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a YAML config file.",
    )
    parser.add_argument(
        "--fictrac-port",
        type=int,
        default=None,
        help="Override FicTrac port (0 to disable).",
    )
    parser.add_argument(
        "--scanimage-port",
        type=int,
        default=None,
        help="Override ScanImage port (0 to disable).",
    )
    return parser


def main() -> None:
    """CLI entry point: run the hub standalone for testing."""
    import argparse
    import time

    from virtual_reality.logging_config import setup_logging

    setup_logging()

    parser = _build_parser()
    args = parser.parse_args()

    if args.config is not None:
        from virtual_reality.config.loader import load_config
        config = load_config(args.config)
        cfg = config.comms
    else:
        from virtual_reality.config.schema import CommsConfig
        cfg = CommsConfig(
            enabled=True,
            fictrac_port=2000,
            scanimage_port=5000,
            led_port=5001,
            presenter_port=0,
        )

    # Apply CLI overrides
    if args.fictrac_port is not None:
        cfg.fictrac_port = args.fictrac_port
    if args.scanimage_port is not None:
        cfg.scanimage_port = args.scanimage_port

    cfg.enabled = True
    hub = CommsHub(cfg)
    hub.start_all()

    print("CommsHub running. Press Ctrl+C to stop.")
    try:
        while True:
            frame = hub.poll_fictrac()
            if frame:
                print(
                    f"FicTrac: heading={frame.heading_rad:.2f} "
                    f"speed={frame.speed:.4f}",
                )
            events = hub.poll_scanimage()
            for ev in events:
                print(f"ScanImage: {ev.event_type} {ev.metadata}")
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        hub.stop_all()
