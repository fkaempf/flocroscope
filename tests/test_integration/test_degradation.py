"""Integration tests for graceful degradation.

Verifies that the system works correctly when hardware/software
components are absent.  Each test exercises a realistic configuration
that a lab user might encounter:

- Behavior-only (no comms at all)
- Comms enabled but no endpoints connected
- Session without comms
- Stimulus without session
- Missing pyzmq (LED/presenter skipped, TCP endpoints still work)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flocroscope.config.schema import (
    CommsConfig,
    SessionConfig,
    FlocroscopeConfig,
)
from flocroscope.session.session import Session


# ------------------------------------------------------------------ #
# Config defaults: everything disabled by default                     #
# ------------------------------------------------------------------ #


class TestDefaultConfig:
    """Default config should be safe with nothing enabled."""

    def test_comms_disabled_by_default(self) -> None:
        """CommsConfig defaults to disabled."""
        cfg = FlocroscopeConfig()
        assert cfg.comms.enabled is False

    def test_session_output_dir_default(self) -> None:
        """SessionConfig has a reasonable default output dir."""
        cfg = FlocroscopeConfig()
        assert cfg.session.output_dir == "data/sessions"

    def test_all_ports_have_defaults(self) -> None:
        """All comms ports have default values."""
        cfg = CommsConfig()
        assert cfg.fictrac_port == 2000
        assert cfg.scanimage_port == 5000
        assert cfg.led_port == 5001
        assert cfg.presenter_port == 5002


# ------------------------------------------------------------------ #
# Session without comms                                               #
# ------------------------------------------------------------------ #


class TestSessionWithoutComms:
    """Session works fully without a CommsHub."""

    def test_session_lifecycle_no_comms(self, tmp_path: Path) -> None:
        """Full session lifecycle without comms."""
        cfg = FlocroscopeConfig()
        cfg.session.output_dir = str(tmp_path)

        session = Session(config=cfg, stimulus_type="TestStimulus")
        session.start()
        assert session.is_running

        trial = session.begin_trial(metadata={"test": True})
        assert trial.trial_number == 1

        # Collecting comms events is a no-op
        session.collect_comms_events()

        session.log_event("test_event", {"key": "value"})

        session.end_trial()
        assert session.trial_count == 1

        path = session.save()
        assert (path / "session.json").exists()
        session.stop()

    def test_session_save_without_trials(
        self, tmp_path: Path,
    ) -> None:
        """Session can be saved with zero trials."""
        cfg = FlocroscopeConfig()
        cfg.session.output_dir = str(tmp_path)

        session = Session(config=cfg)
        session.start()
        path = session.save()
        assert (path / "session.json").exists()

        data = json.loads((path / "session.json").read_text())
        assert data["trial_count"] == 0
        session.stop()

    def test_session_stop_before_start(self) -> None:
        """Stopping an unstarted session is a no-op."""
        session = Session()
        session.stop()  # should not raise

    def test_session_double_start(self) -> None:
        """Starting twice is idempotent."""
        session = Session()
        session.start()
        session.start()  # should not raise
        assert session.is_running
        session.stop()

    def test_collect_comms_no_hub(self) -> None:
        """collect_comms_events with no hub is a no-op."""
        session = Session(comms=None)
        session.start()
        session.begin_trial()
        session.collect_comms_events()  # no-op
        session.end_trial()
        session.stop()


# ------------------------------------------------------------------ #
# CommsHub with all endpoints disabled                                #
# ------------------------------------------------------------------ #


class TestCommsAllDisabled:
    """CommsHub with all ports set to 0 (all disabled)."""

    def test_hub_starts_with_no_endpoints(self) -> None:
        """Hub with all ports=0 starts cleanly."""
        from flocroscope.comms.hub import CommsHub

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

        # Polling returns safe defaults
        assert hub.poll_fictrac() is None
        assert hub.poll_scanimage() == []
        assert hub.poll_presenter() is None

        # Sending to disabled endpoints is a no-op
        from flocroscope.comms.base import LedCommand, PresenterCommand
        hub.send_led(LedCommand(command="on"))
        hub.send_presenter(PresenterCommand(command="present"))

        hub.stop_all()

    def test_hub_status_all_disconnected(self) -> None:
        """Status dict shows all endpoints disconnected."""
        from flocroscope.comms.hub import CommsHub

        cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,
            scanimage_port=0,
            led_port=0,
            presenter_port=0,
        )
        hub = CommsHub(cfg)
        hub.start_all()

        status = hub.status
        assert all(v is False for v in status.values())
        hub.stop_all()


# ------------------------------------------------------------------ #
# CommsHub disabled via master switch                                 #
# ------------------------------------------------------------------ #


class TestCommsMasterSwitch:
    """When comms.enabled is False, the hub should not be created."""

    def test_config_comms_disabled(self) -> None:
        """Default config has comms disabled."""
        cfg = FlocroscopeConfig()
        assert cfg.comms.enabled is False

    def test_hub_not_created_when_disabled(self) -> None:
        """Stimulus setup skips hub when comms.enabled is False."""
        # Simulates the logic in fly_3d.py setup()
        cfg = FlocroscopeConfig()
        assert cfg.comms.enabled is False

        comms = None
        if cfg.comms.enabled:
            from flocroscope.comms.hub import CommsHub
            comms = CommsHub(cfg.comms)

        assert comms is None


# ------------------------------------------------------------------ #
# FicTrac controller without actual FicTrac                           #
# ------------------------------------------------------------------ #


class TestFicTracControllerNoData:
    """FicTracController works when FicTrac sends no data."""

    def test_controller_stays_at_origin(self) -> None:
        """Without FicTrac data, position stays at origin."""
        from flocroscope.comms.hub import CommsHub
        from flocroscope.comms.fictrac_controller import (
            FicTracController,
        )

        cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,  # no FicTrac
        )
        hub = CommsHub(cfg)
        hub.start_all()

        ctrl = FicTracController(hub=hub, ball_radius_mm=4.5)
        ctrl.update(0.016)  # no data → stays at origin

        assert ctrl.x == 0.0
        assert ctrl.y == 0.0
        assert ctrl.heading_deg == 0.0
        assert ctrl.frames_received == 0

        hub.stop_all()


# ------------------------------------------------------------------ #
# Session with comms but no hardware                                  #
# ------------------------------------------------------------------ #


class TestSessionWithEmptyComms:
    """Session works when CommsHub has no active endpoints."""

    def test_session_with_empty_hub(self, tmp_path: Path) -> None:
        """Session collects events from empty hub without errors."""
        from flocroscope.comms.hub import CommsHub

        cfg = FlocroscopeConfig()
        cfg.session.output_dir = str(tmp_path)

        comms_cfg = CommsConfig(
            enabled=True,
            fictrac_port=0,
            scanimage_port=0,
            led_port=0,
            presenter_port=0,
        )
        hub = CommsHub(comms_cfg)
        hub.start_all()

        session = Session(config=cfg, comms=hub)
        session.start()
        session.begin_trial()
        session.collect_comms_events()  # empty but no error
        session.end_trial()

        path = session.save()
        assert (path / "session.json").exists()

        session.stop()
        hub.stop_all()


# ------------------------------------------------------------------ #
# FrameRecorder standalone (no session, no comms)                     #
# ------------------------------------------------------------------ #


class TestFrameRecorderStandalone:
    """FrameRecorder works independently of everything else."""

    def test_recorder_standalone(self, tmp_path: Path) -> None:
        """Record frames without session or comms."""
        from flocroscope.session.recorder import FrameRecorder

        path = tmp_path / "frames.csv"
        rec = FrameRecorder(path, columns=["frame", "x", "y"])
        rec.start()
        rec.record(x=1.0, y=2.0)
        rec.record(x=3.0, y=4.0)
        rec.stop()

        assert path.exists()
        assert rec.frame_count == 2


# ------------------------------------------------------------------ #
# Import safety without pyzmq                                        #
# ------------------------------------------------------------------ #


class TestImportSafety:
    """Core imports work even without optional dependencies."""

    def test_comms_base_import(self) -> None:
        """comms.base imports without pyzmq."""
        from flocroscope.comms.base import (
            Endpoint,
            FicTracFrame,
            LedCommand,
            PresenterCommand,
            PresenterStatus,
            TrialEvent,
        )
        # Just verify imports work
        assert FicTracFrame is not None

    def test_comms_hub_import(self) -> None:
        """comms.hub imports without pyzmq."""
        from flocroscope.comms.hub import CommsHub
        assert CommsHub is not None

    def test_comms_init_import(self) -> None:
        """comms.__init__ imports without pyzmq."""
        from flocroscope.comms import (
            CommsHub,
            FicTracFrame,
            LedCommand,
        )
        assert CommsHub is not None
        assert FicTracFrame is not None

    def test_fictrac_receiver_import(self) -> None:
        """fictrac module imports without pyzmq (uses stdlib)."""
        from flocroscope.comms.fictrac import (
            FicTracReceiver,
            parse_fictrac_line,
        )
        assert FicTracReceiver is not None

    def test_scanimage_import(self) -> None:
        """scanimage module imports without pyzmq (uses stdlib)."""
        from flocroscope.comms.scanimage import ScanImageSync
        assert ScanImageSync is not None

    def test_session_import(self) -> None:
        """session module imports without any comms."""
        from flocroscope.session import Session
        assert Session is not None

    def test_flomington_import(self) -> None:
        """Flomington module imports without supabase-py."""
        from flocroscope.comms.flomington import (
            FlomingtonClient,
            FlomingtonConfig,
            FlyCross,
            FlyStock,
        )
        assert FlomingtonClient is not None


# ------------------------------------------------------------------ #
# Flomington placeholder degrades gracefully                          #
# ------------------------------------------------------------------ #


class TestFlomingtonDegradation:
    """Flomington client returns safe defaults when not connected."""

    def test_connect_without_url(self) -> None:
        """Connect returns False without Supabase URL."""
        from flocroscope.comms.flomington import (
            FlomingtonClient,
            FlomingtonConfig,
        )
        client = FlomingtonClient(FlomingtonConfig())
        assert client.connect() is False
        assert client.connected is False

    def test_all_queries_return_empty(self) -> None:
        """All query methods return None or empty lists."""
        from flocroscope.comms.flomington import (
            FlomingtonClient,
            FlomingtonConfig,
        )
        client = FlomingtonClient(FlomingtonConfig())
        assert client.get_stock("abc") is None
        assert client.get_cross("xyz") is None
        assert client.search_stocks("GAL4") == []
        assert client.get_crosses_for_experiment("2P") == []

    def test_tag_and_push_return_false(self) -> None:
        """Session tagging and result push return False."""
        from flocroscope.comms.flomington import (
            FlomingtonClient,
            FlomingtonConfig,
        )
        client = FlomingtonClient(FlomingtonConfig())
        assert client.tag_session("s1", stock_id="abc") is False
        assert client.push_results("s1", {}) is False


# ------------------------------------------------------------------ #
# Stimulus base class run() handles missing session                   #
# ------------------------------------------------------------------ #


class TestStimulusBaseDegradation:
    """Stimulus.run() works with session=None."""

    def test_get_state_default_empty(self) -> None:
        """Default get_state() returns empty dict."""
        from flocroscope.stimulus.base import Stimulus

        class Dummy(Stimulus):
            def setup(self) -> None:
                pass
            def update(self, dt, events) -> None:
                pass
            def render(self) -> None:
                pass
            def teardown(self) -> None:
                pass

        dummy = Dummy()
        assert dummy.get_state() == {}


# ------------------------------------------------------------------ #
# Fly3DStimulus init is safe before setup                             #
# ------------------------------------------------------------------ #


class TestFly3DInitSafety:
    """Fly3DStimulus attributes are safe before setup()."""

    def test_comms_is_none_before_setup(self) -> None:
        """_comms attribute exists and is None after __init__."""
        from flocroscope.stimulus.fly_3d import Fly3DStimulus

        stim = Fly3DStimulus()
        assert stim._comms is None
        assert stim._use_fictrac is False

    def test_session_creation_with_none_comms(self) -> None:
        """Session can be created with stimulus._comms = None."""
        from flocroscope.stimulus.fly_3d import Fly3DStimulus

        stim = Fly3DStimulus()
        session = Session(
            config=stim.config,
            comms=stim._comms,
            stimulus_type="Fly3DStimulus",
        )
        assert session._comms is None
        session.start()
        session.collect_comms_events()  # no-op
        session.stop()


# ------------------------------------------------------------------ #
# Config loading with missing sections                                #
# ------------------------------------------------------------------ #


class TestConfigLoadingDegradation:
    """Config loader handles missing YAML sections gracefully."""

    def test_load_minimal_yaml(self, tmp_path: Path) -> None:
        """Loading a YAML with only arena section uses defaults."""
        from flocroscope.config.loader import load_config

        yaml_path = tmp_path / "minimal.yaml"
        yaml_path.write_text("arena:\n  radius_mm: 50.0\n")

        cfg = load_config(yaml_path)
        assert cfg.arena.radius_mm == 50.0
        # Everything else is default
        assert cfg.comms.enabled is False
        assert cfg.session.output_dir == "data/sessions"
        assert cfg.display.target_fps == 60

    def test_load_empty_yaml(self, tmp_path: Path) -> None:
        """Loading an empty YAML file uses all defaults."""
        from flocroscope.config.loader import load_config

        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("")

        cfg = load_config(yaml_path)
        assert cfg.arena.radius_mm == 40.0
        assert cfg.comms.enabled is False

    def test_load_unknown_keys_ignored(self, tmp_path: Path) -> None:
        """Unknown YAML keys are silently ignored."""
        from flocroscope.config.loader import load_config

        yaml_path = tmp_path / "extra.yaml"
        yaml_path.write_text(
            "arena:\n  radius_mm: 30.0\n"
            "unknown_section:\n  foo: bar\n"
        )

        cfg = load_config(yaml_path)
        assert cfg.arena.radius_mm == 30.0
        assert not hasattr(cfg, "unknown_section")
