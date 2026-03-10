"""Inter-process communication for closed-loop experiments.

Provides endpoints for FicTrac (treadmill tracking), ScanImage
(2-photon microscopy sync), optogenetics LED control, fly
presenter positioning, and future Flomington integration.

Example::

    from flocroscope.comms import CommsHub, FicTracFrame
    from flocroscope.config.schema import CommsConfig

    hub = CommsHub(CommsConfig(enabled=True))
    hub.start_all()
    frame = hub.poll_fictrac()  # FicTracFrame | None
    hub.stop_all()
"""

from flocroscope.comms.base import (
    FicTracFrame,
    LedCommand,
    PresenterCommand,
    PresenterStatus,
    TrialEvent,
)
from flocroscope.comms.hub import CommsHub

__all__ = [
    "CommsHub",
    "FicTracFrame",
    "LedCommand",
    "PresenterCommand",
    "PresenterStatus",
    "TrialEvent",
]
