"""Base types and abstract endpoint for the comms subsystem.

Defines message dataclasses exchanged between endpoints and
the :class:`Endpoint` abstract base class that all concrete
endpoints implement.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


# -------------------------------------------------------------------
# Message types
# -------------------------------------------------------------------

@dataclass
class FicTracFrame:
    """One frame of FicTrac tracking data.

    Fields correspond to the 25-column CSV output format.  Only
    the most commonly used columns are stored; the full raw line
    is available in *raw* if needed.

    Attributes:
        frame_count: Frame counter (col 1).
        delta_rot_lab: Delta rotation vector in lab coords (cols 6-8).
        heading_rad: Integrated heading in lab coords, radians (col 17).
        x_rad: Integrated X position in lab coords, radians (col 15).
        y_rad: Integrated Y position in lab coords, radians (col 16).
        speed: Instantaneous movement speed, rad/frame (col 19).
        direction_rad: Movement direction in lab coords, radians (col 18).
        timestamp_ms: Frame timestamp in ms (col 22).
        dt_ms: Time since last frame in ms (col 24).
        raw: The original CSV line, if retained.
    """

    frame_count: int = 0
    delta_rot_lab: tuple[float, float, float] = (0.0, 0.0, 0.0)
    heading_rad: float = 0.0
    x_rad: float = 0.0
    y_rad: float = 0.0
    speed: float = 0.0
    direction_rad: float = 0.0
    timestamp_ms: float = 0.0
    dt_ms: float = 0.0
    raw: str = ""


@dataclass
class TrialEvent:
    """An event from the ScanImage acquisition system.

    Attributes:
        event_type: One of ``"frame_clock"``, ``"trial_start"``,
            ``"trial_stop"``, or a custom string.
        timestamp: Event timestamp (seconds since epoch).
        metadata: Arbitrary key-value data attached to the event.
    """

    event_type: str = ""
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedCommand:
    """A command sent to the optogenetics LED controller.

    Attributes:
        command: One of ``"on"``, ``"off"``, ``"pulse"``, ``"pwm"``.
        intensity: LED intensity in ``[0.0, 1.0]``.
        duration_ms: Pulse duration in milliseconds (for ``"pulse"``).
        channel: LED channel index.
    """

    command: str = "off"
    intensity: float = 0.0
    duration_ms: float = 0.0
    channel: int = 0


@dataclass
class PresenterCommand:
    """A command sent to the fly presenter mechanism.

    Attributes:
        command: One of ``"present"``, ``"retract"``, ``"position"``,
            ``"home"``.
        position_mm: Target position in mm (for ``"position"``).
    """

    command: str = "retract"
    position_mm: float = 0.0


@dataclass
class PresenterStatus:
    """Status reply from the fly presenter.

    Attributes:
        state: Current state string (e.g. ``"idle"``, ``"moving"``).
        position_mm: Current position in mm.
        error: Error message, or empty string if OK.
    """

    state: str = "unknown"
    position_mm: float = 0.0
    error: str = ""


# -------------------------------------------------------------------
# Endpoint ABC
# -------------------------------------------------------------------

class Endpoint(abc.ABC):
    """Abstract base class for a communication endpoint.

    Each endpoint runs a background thread and exposes a non-blocking
    :meth:`poll` method that the main render loop calls once per frame.
    """

    @abc.abstractmethod
    def start(self) -> None:
        """Start the background thread and open connections."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Signal the background thread to stop and clean up."""

    @abc.abstractmethod
    def poll(self) -> Any | None:
        """Return the latest data without blocking.

        Returns:
            The most recent message, or ``None`` if nothing new.
        """

    @property
    @abc.abstractmethod
    def connected(self) -> bool:
        """Whether the endpoint has an active connection."""
