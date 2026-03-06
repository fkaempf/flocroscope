"""Abstract base class for stimulus presentations.

Every stimulus follows the same lifecycle::

    stimulus.setup()
    while running:
        stimulus.update(dt, events)
        stimulus.render()
    stimulus.teardown()

The :meth:`run` convenience method implements this loop with
pygame event handling, FPS tracking, and optional session recording.
"""

from __future__ import annotations

import abc
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.session.session import Session

logger = logging.getLogger(__name__)


class Stimulus(abc.ABC):
    """Abstract stimulus base class.

    Subclasses must implement :meth:`setup`, :meth:`update`,
    :meth:`render`, and :meth:`teardown`.
    """

    @abc.abstractmethod
    def setup(self) -> None:
        """Initialise GPU resources, load models, etc."""

    @abc.abstractmethod
    def update(self, dt: float, events: list) -> None:
        """Advance simulation state.

        Args:
            dt: Wall-clock seconds since the last frame.
            events: List of ``pygame.event.Event`` objects.
        """

    @abc.abstractmethod
    def render(self) -> None:
        """Draw the current frame."""

    @abc.abstractmethod
    def teardown(self) -> None:
        """Release GPU resources and close windows."""

    def get_state(self) -> dict:
        """Return the current stimulus state for data recording.

        Override in subclasses to provide per-frame data (fly
        position, heading, etc.).  The default returns an empty dict.
        """
        return {}

    def run(
        self,
        target_fps: int = 60,
        session: Session | None = None,
        record: bool = True,
    ) -> None:
        """Run the stimulus main loop.

        Optionally integrates with a :class:`Session` for automatic
        experiment tracking and per-frame data recording.

        When a session is provided:

        - A trial is automatically begun at start and ended at exit.
        - :meth:`Session.collect_comms_events` is called each frame.
        - Per-frame state is recorded to CSV (if *record* is True
          and the stimulus implements :meth:`get_state`).
        - The session is saved on exit.

        The stimulus works identically with or without a session.

        Args:
            target_fps: Target frame rate (used for clock tick).
            session: Optional session for experiment recording.
            record: Whether to record per-frame data to CSV.
        """
        import pygame

        self.setup()
        clock = pygame.time.Clock()
        running = True
        last_time = time.perf_counter()

        # Data recorder
        recorder = None
        if session is not None and record:
            from flocroscope.session.recorder import (
                FrameRecorder,
            )
            output_dir = session.save()
            recorder = FrameRecorder(output_dir / "frames.csv")
            recorder.start()

        # Start session trial if provided
        if session is not None:
            if not session.is_running:
                session.start()
            session.begin_trial(metadata={
                "stimulus": type(self).__name__,
                "target_fps": target_fps,
            })

        try:
            while running:
                now = time.perf_counter()
                dt = now - last_time
                last_time = now

                events = pygame.event.get()
                for event in events:
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False

                if not running:
                    break

                self.update(dt, events)
                self.render()

                # Collect comms events into session
                if session is not None:
                    session.collect_comms_events()

                # Record per-frame data
                if recorder is not None:
                    state = self.get_state()
                    if state:
                        recorder.record(**state)

                pygame.display.flip()
                clock.tick(target_fps)
        finally:
            # Stop recorder
            if recorder is not None:
                recorder.stop()

            # End trial and save session
            if session is not None:
                session.end_trial()
                session.save()

            self.teardown()
