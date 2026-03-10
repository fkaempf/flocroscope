"""Tests for the session management module."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from flocroscope.config.schema import FlocroscopeConfig
from flocroscope.session.session import (
    Session,
    SessionMetadata,
    TrialRecord,
)


class TestSessionMetadata:
    """Tests for SessionMetadata dataclass."""

    def test_defaults(self) -> None:
        """Default metadata has empty fields."""
        meta = SessionMetadata()
        assert meta.session_id == ""
        assert meta.start_time == ""
        assert meta.experimenter == ""
        assert meta.config_snapshot == {}

    def test_custom_values(self) -> None:
        """Custom values are stored correctly."""
        meta = SessionMetadata(
            session_id="abc123",
            experimenter="Flo",
            stimulus_type="fly_3d",
        )
        assert meta.session_id == "abc123"
        assert meta.experimenter == "Flo"


class TestTrialRecord:
    """Tests for TrialRecord dataclass."""

    def test_defaults(self) -> None:
        """Default trial has zero timing."""
        trial = TrialRecord()
        assert trial.trial_number == 0
        assert trial.duration_s == 0.0
        assert trial.events == []
        assert trial.metadata == {}

    def test_independent_events(self) -> None:
        """Each trial gets its own events list."""
        t1 = TrialRecord()
        t2 = TrialRecord()
        t1.events.append({"type": "test"})
        assert len(t2.events) == 0


class TestSession:
    """Tests for Session lifecycle management."""

    def test_creation(self) -> None:
        """Session creates with a unique ID."""
        session = Session()
        assert len(session.session_id) == 12
        assert not session.is_running
        assert session.trial_count == 0

    def test_creation_with_config(self) -> None:
        """Session captures config snapshot."""
        cfg = FlocroscopeConfig()
        session = Session(config=cfg)
        snap = session.metadata.config_snapshot
        assert "arena_radius_mm" in snap
        assert snap["arena_radius_mm"] == cfg.arena.radius_mm

    def test_start_stop(self) -> None:
        """Session starts and stops cleanly."""
        session = Session()
        session.start()
        assert session.is_running
        assert session.metadata.start_time != ""
        session.stop()
        assert not session.is_running
        assert session.metadata.end_time != ""

    def test_double_start_ignored(self) -> None:
        """Starting a running session is a no-op."""
        session = Session()
        session.start()
        start_time = session.metadata.start_time
        session.start()
        assert session.metadata.start_time == start_time

    def test_stop_without_start(self) -> None:
        """Stopping before starting is a no-op."""
        session = Session()
        session.stop()
        assert not session.is_running

    def test_begin_end_trial(self) -> None:
        """Trial lifecycle works correctly."""
        session = Session()
        session.start()
        trial = session.begin_trial(metadata={"stim": "fly_3d"})
        assert trial.trial_number == 1
        assert session.current_trial is trial

        ended = session.end_trial()
        assert ended is trial
        assert ended.duration_s > 0
        assert session.current_trial is None
        assert session.trial_count == 1

    def test_end_trial_without_begin(self) -> None:
        """Ending when no trial active returns None."""
        session = Session()
        session.start()
        assert session.end_trial() is None

    def test_begin_trial_auto_ends_previous(self) -> None:
        """Beginning a new trial ends the current one."""
        session = Session()
        session.start()
        session.begin_trial()
        session.begin_trial()
        assert session.trial_count == 1
        assert session.current_trial.trial_number == 2

    def test_multiple_trials(self) -> None:
        """Multiple trials accumulate correctly."""
        session = Session()
        session.start()
        for i in range(3):
            session.begin_trial()
            session.end_trial()
        assert session.trial_count == 3
        assert session.trials[0].trial_number == 1
        assert session.trials[2].trial_number == 3

    def test_log_event(self) -> None:
        """Events are logged to the current trial."""
        session = Session()
        session.start()
        session.begin_trial()
        session.log_event("led_pulse", {"intensity": 0.8})
        session.log_event("fictrac_position", {"x": 1.0})

        trial = session.end_trial()
        assert len(trial.events) == 2
        assert trial.events[0]["type"] == "led_pulse"
        assert trial.events[1]["data"]["x"] == 1.0

    def test_log_event_no_trial(self) -> None:
        """Logging without an active trial is silently dropped."""
        session = Session()
        session.start()
        session.log_event("test")  # should not raise

    def test_stop_ends_active_trial(self) -> None:
        """Stopping the session ends any active trial."""
        session = Session()
        session.start()
        session.begin_trial()
        session.stop()
        assert session.trial_count == 1
        assert session.current_trial is None

    def test_summary(self) -> None:
        """Summary returns expected fields."""
        session = Session()
        session.start()
        summary = session.summary()
        assert summary["session_id"] == session.session_id
        assert summary["running"] is True
        assert summary["trial_count"] == 0
        assert summary["current_trial"] is None

    def test_summary_with_trial(self) -> None:
        """Summary reflects active trial."""
        session = Session()
        session.start()
        session.begin_trial()
        summary = session.summary()
        assert summary["current_trial"] == 1

    def test_trials_list_is_copy(self) -> None:
        """trials property returns a copy."""
        session = Session()
        session.start()
        session.begin_trial()
        session.end_trial()
        trials = session.trials
        trials.clear()
        assert session.trial_count == 1

    def test_experimenter(self) -> None:
        """Experimenter name is stored."""
        session = Session(experimenter="Flo")
        assert session.metadata.experimenter == "Flo"


class TestSessionSave:
    """Tests for session data persistence."""

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """Save creates the session directory."""
        session = Session()
        session.start()
        session.stop()
        out = session.save(output_dir=tmp_path)
        assert out.exists()
        assert out.is_dir()
        assert (out / "session.json").exists()

    def test_save_session_json(self, tmp_path: Path) -> None:
        """session.json contains expected fields."""
        session = Session(experimenter="Flo")
        session.start()
        session.stop()
        out = session.save(output_dir=tmp_path)

        data = json.loads((out / "session.json").read_text())
        assert data["session_id"] == session.session_id
        assert data["experimenter"] == "Flo"
        assert data["trial_count"] == 0

    def test_save_trials_csv(self, tmp_path: Path) -> None:
        """trials.csv contains trial timing data."""
        session = Session()
        session.start()
        session.begin_trial()
        time.sleep(0.01)
        session.end_trial()
        session.stop()
        out = session.save(output_dir=tmp_path)

        csv_path = out / "trials.csv"
        assert csv_path.exists()
        lines = csv_path.read_text().strip().split("\n")
        assert len(lines) == 2  # header + 1 trial
        assert "trial_number" in lines[0]

    def test_save_events_json(self, tmp_path: Path) -> None:
        """Per-trial event logs are saved."""
        session = Session()
        session.start()
        session.begin_trial()
        session.log_event("test_event", {"val": 42})
        trial = session.end_trial()
        session.stop()
        out = session.save(output_dir=tmp_path)

        events_file = out / f"events_{trial.trial_id}.json"
        assert events_file.exists()
        events = json.loads(events_file.read_text())
        assert len(events) == 1
        assert events[0]["type"] == "test_event"

    def test_save_empty_session(self, tmp_path: Path) -> None:
        """Saving a session with no trials works."""
        session = Session()
        session.start()
        session.stop()
        out = session.save(output_dir=tmp_path)
        assert (out / "session.json").exists()
        assert not (out / "trials.csv").exists()

    def test_save_uses_config_dir(self, tmp_path: Path) -> None:
        """Save uses config.session.output_dir when available."""
        cfg = FlocroscopeConfig()
        cfg.session.output_dir = str(tmp_path / "custom")
        session = Session(config=cfg)
        session.start()
        session.stop()
        out = session.save()
        assert str(tmp_path / "custom") in str(out)


class TestSessionCommsIntegration:
    """Tests for session + comms hub integration."""

    def test_collect_without_comms(self) -> None:
        """collect_comms_events is a no-op without hub."""
        session = Session()
        session.start()
        session.begin_trial()
        session.collect_comms_events()  # should not raise
        session.end_trial()

    def test_collect_without_trial(self) -> None:
        """collect_comms_events is a no-op without active trial."""
        hub = MagicMock()
        session = Session(comms=hub)
        session.start()
        session.collect_comms_events()
        hub.poll_scanimage.assert_not_called()
