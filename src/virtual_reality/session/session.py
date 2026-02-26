"""Experiment session lifecycle manager.

A :class:`Session` represents one continuous experimental run.  It
manages trial boundaries, collects events from the comms hub, and
persists session data as YAML + CSV.

Sessions are designed to work with any subset of hardware — the
system degrades gracefully when components are absent.
"""

from __future__ import annotations

import csv
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from virtual_reality.comms.hub import CommsHub
    from virtual_reality.config.schema import (
        SessionConfig,
        VirtualRealityConfig,
    )

logger = logging.getLogger(__name__)


@dataclass
class TrialRecord:
    """Metadata and timing for a single trial within a session.

    Attributes:
        trial_id: Auto-generated unique trial identifier.
        trial_number: Sequential trial number (1-based).
        start_time: Trial start timestamp (seconds since epoch).
        end_time: Trial end timestamp (0 if still running).
        duration_s: Trial duration in seconds.
        metadata: Arbitrary key-value metadata for this trial.
        events: List of timestamped events during the trial.
    """

    trial_id: str = ""
    trial_number: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    duration_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SessionMetadata:
    """Top-level metadata for an experimental session.

    Attributes:
        session_id: Auto-generated unique session identifier.
        start_time: Session start timestamp (ISO format).
        end_time: Session end timestamp (ISO format, empty if
            still running).
        experimenter: Name of the experimenter.
        stimulus_type: Name of the stimulus class used.
        fly_stock_id: Flomington stock ID (if linked).
        fly_cross_id: Flomington cross ID (if linked).
        fly_genotype: Fly genotype string.
        notes: Free-form session notes.
        config_snapshot: Snapshot of key config values.
    """

    session_id: str = ""
    start_time: str = ""
    end_time: str = ""
    experimenter: str = ""
    stimulus_type: str = ""
    fly_stock_id: str = ""
    fly_cross_id: str = ""
    fly_genotype: str = ""
    notes: str = ""
    config_snapshot: dict[str, Any] = field(default_factory=dict)


class Session:
    """Manages the lifecycle of an experimental session.

    A session consists of zero or more trials, each with its own
    metadata and event log.  The session automatically collects
    ScanImage trigger events and FicTrac data when a CommsHub
    is available.

    The session degrades gracefully — it works fine with no comms,
    no Flomington, or no external hardware at all.

    Args:
        config: Full application configuration (uses ``session``
            and ``comms`` subsections).
        comms: Optional CommsHub for collecting hardware events.
        stimulus_type: Name of the active stimulus class.
        experimenter: Name of the experimenter.
    """

    def __init__(
        self,
        config: VirtualRealityConfig | None = None,
        comms: CommsHub | None = None,
        stimulus_type: str = "",
        experimenter: str = "",
    ) -> None:
        self._config = config
        self._comms = comms
        self._started = False
        self._current_trial: TrialRecord | None = None
        self._trials: list[TrialRecord] = []
        self._trial_counter = 0

        self.metadata = SessionMetadata(
            session_id=uuid.uuid4().hex[:12],
            stimulus_type=stimulus_type,
            experimenter=experimenter,
        )

        if config is not None:
            self.metadata.config_snapshot = {
                "arena_radius_mm": config.arena.radius_mm,
                "projection": config.camera.projection,
                "fov_x_deg": config.camera.fov_x_deg,
                "comms_enabled": config.comms.enabled,
                "autonomous": config.autonomous.enabled,
            }

    @property
    def session_id(self) -> str:
        """The unique session identifier."""
        return self.metadata.session_id

    @property
    def is_running(self) -> bool:
        """Whether the session is currently active."""
        return self._started

    @property
    def trial_count(self) -> int:
        """Number of completed trials."""
        return len(self._trials)

    @property
    def current_trial(self) -> TrialRecord | None:
        """The currently active trial, or None."""
        return self._current_trial

    @property
    def trials(self) -> list[TrialRecord]:
        """All completed trial records."""
        return list(self._trials)

    def start(self) -> None:
        """Start the session.

        Records the start timestamp and logs the session ID.
        """
        if self._started:
            logger.warning("Session already started")
            return

        self._started = True
        self.metadata.start_time = datetime.now().isoformat()
        logger.info(
            "Session %s started at %s",
            self.session_id, self.metadata.start_time,
        )

    def stop(self) -> None:
        """Stop the session.

        Ends any active trial and records the end timestamp.
        """
        if not self._started:
            return

        if self._current_trial is not None:
            self.end_trial()

        self.metadata.end_time = datetime.now().isoformat()
        self._started = False
        logger.info(
            "Session %s stopped: %d trials",
            self.session_id, len(self._trials),
        )

    def begin_trial(
        self, metadata: dict[str, Any] | None = None,
    ) -> TrialRecord:
        """Begin a new trial.

        If a trial is already active, it is ended first.

        Args:
            metadata: Optional key-value metadata for this trial
                (genotype, stimulus parameters, etc.).

        Returns:
            The new :class:`TrialRecord`.
        """
        if self._current_trial is not None:
            self.end_trial()

        self._trial_counter += 1
        trial = TrialRecord(
            trial_id=uuid.uuid4().hex[:8],
            trial_number=self._trial_counter,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self._current_trial = trial
        logger.info(
            "Trial %d started (id=%s)",
            trial.trial_number, trial.trial_id,
        )
        return trial

    def end_trial(self) -> TrialRecord | None:
        """End the current trial.

        Returns:
            The completed :class:`TrialRecord`, or None if no
            trial was active.
        """
        if self._current_trial is None:
            return None

        trial = self._current_trial
        trial.end_time = time.time()
        trial.duration_s = trial.end_time - trial.start_time
        self._trials.append(trial)
        self._current_trial = None
        logger.info(
            "Trial %d ended (%.1fs)",
            trial.trial_number, trial.duration_s,
        )
        return trial

    def log_event(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log a timestamped event to the current trial.

        If no trial is active, the event is silently dropped.

        Args:
            event_type: Event type string (e.g. ``"led_pulse"``,
                ``"scanimage_trigger"``, ``"fictrac_position"``).
            data: Optional event data dict.
        """
        if self._current_trial is None:
            return

        event = {
            "time": time.time(),
            "type": event_type,
        }
        if data:
            event["data"] = data
        self._current_trial.events.append(event)

    def collect_comms_events(self) -> None:
        """Poll the CommsHub and log any pending events.

        Call this once per frame during the stimulus loop.
        No-op if no CommsHub is configured.
        """
        if self._comms is None:
            return
        if self._current_trial is None:
            return

        # ScanImage events
        for ev in self._comms.poll_scanimage():
            self.log_event("scanimage", {
                "event_type": ev.event_type,
                "metadata": ev.metadata,
            })

    def save(self, output_dir: str | Path | None = None) -> Path:
        """Save session data to disk.

        Creates a directory named ``{session_id}/`` containing:
        - ``session.json``: Session metadata and trial summaries.
        - ``trials.csv``: Flat CSV of trial timing data.
        - ``events_{trial_id}.json``: Per-trial event logs.

        Args:
            output_dir: Root output directory. Defaults to
                ``config.session.output_dir`` or ``"data/sessions"``.

        Returns:
            Path to the session directory.
        """
        if output_dir is None:
            if (
                self._config is not None
                and hasattr(self._config, "session")
            ):
                output_dir = self._config.session.output_dir
            else:
                output_dir = "data/sessions"

        session_dir = Path(output_dir) / self.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Session metadata
        session_data = {
            "session_id": self.metadata.session_id,
            "start_time": self.metadata.start_time,
            "end_time": self.metadata.end_time,
            "experimenter": self.metadata.experimenter,
            "stimulus_type": self.metadata.stimulus_type,
            "fly_stock_id": self.metadata.fly_stock_id,
            "fly_cross_id": self.metadata.fly_cross_id,
            "fly_genotype": self.metadata.fly_genotype,
            "notes": self.metadata.notes,
            "trial_count": len(self._trials),
            "config_snapshot": self.metadata.config_snapshot,
        }
        meta_path = session_dir / "session.json"
        meta_path.write_text(
            json.dumps(session_data, indent=2) + "\n",
        )

        # Trials CSV
        if self._trials:
            csv_path = session_dir / "trials.csv"
            with csv_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "trial_number", "trial_id",
                    "start_time", "end_time", "duration_s",
                ])
                writer.writeheader()
                for trial in self._trials:
                    writer.writerow({
                        "trial_number": trial.trial_number,
                        "trial_id": trial.trial_id,
                        "start_time": trial.start_time,
                        "end_time": trial.end_time,
                        "duration_s": f"{trial.duration_s:.3f}",
                    })

            # Per-trial event logs
            for trial in self._trials:
                if trial.events:
                    events_path = (
                        session_dir / f"events_{trial.trial_id}.json"
                    )
                    events_path.write_text(
                        json.dumps(trial.events, indent=2) + "\n",
                    )

        logger.info("Session saved to %s", session_dir)
        return session_dir

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of the session state.

        Useful for GUI display and status reporting.
        """
        total_duration = sum(t.duration_s for t in self._trials)
        total_events = sum(
            len(t.events) for t in self._trials
        )
        return {
            "session_id": self.session_id,
            "running": self._started,
            "trial_count": len(self._trials),
            "current_trial": (
                self._current_trial.trial_number
                if self._current_trial else None
            ),
            "total_duration_s": total_duration,
            "total_events": total_events,
        }
