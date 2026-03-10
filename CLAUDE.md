# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Flocroscope** is a modular Python package for rendering virtual fly stimuli in neuroscience experiments and calibrating projector-camera systems. It consolidates the former `virtual.fly` (24 Python scripts) and `screen.calibration` (~15 files) repositories into a single well-structured package.

## Architecture

### Repository Layout

```
flocroscope/                   # Project root
    src/flocroscope/           # Python package
        config/                # Dataclass schemas, YAML loader, paths
        cameras/               # Camera Protocol + Alvium/RotPy drivers
        calibration/           # Fisheye/pinhole calibration, intrinsics I/O
        mapping/               # Structured light, warp maps, pipeline
        rendering/             # GL utils, shaders, GLB loader, projections
        math_utils/            # Matrix transforms, arena geometry, lighting
        stimulus/              # Stimulus ABC + Fly3D/FlySprite/WarpCircle
        display/               # Monitor picking, surface, minimap, window
        pipeline/              # Calibration pipeline orchestrator
        comms/                 # Inter-process comms (FicTrac, ScanImage, LED)
        session/               # Experiment session lifecycle + trial tracking
        gui/                   # Dear ImGui application + 12 panels
        legacy/                # Archived original scripts (read-only)
    tests/                     # Test suite (~490 tests)
    configs/                   # Calibration data (warp maps, intrinsics)
    assets/                    # Binary assets (not in git)
        models/                # fly.glb, testmodel.glb
        sprites/               # og_pics/, red_pics/, interp* frame sets
    calibration.pictures/      # Reference calibration photographs
    data/sessions/             # Experiment session output
```

### Key Concepts

- **Projector warp maps**: `mapx.npy`/`mapy.npy` files define pixel mapping from projector space to camera space
- **Structured-light**: Gray code for integer precision + sine phase for subpixel accuracy
- **Camera Protocol**: `cameras.base.Camera` defines the interface (start/grab/stop)
- **Config system**: Nested dataclasses with YAML serialization (`config.schema.FlocroscopeConfig`)
- **Stimulus lifecycle**: `setup() -> update(dt, events) -> render() -> teardown()`

### Communications (`comms/`)

The `comms` module provides optional inter-process communication for closed-loop experiments. It is managed by `CommsHub`, which creates and supervises individual endpoints:

- `fictrac.py` / `fictrac_controller.py`: Receives ball-tracking data (heading, speed, position) from FicTrac over TCP and converts radians to mm using the configured ball radius.
- `scanimage.py`: Listens for trial events (frame clock, trial start/stop) from ScanImage 2-photon microscopy over TCP.
- `led.py`: Publishes optogenetics LED commands (on/off/pulse/PWM) via ZMQ PUB socket.
- `presenter.py`: Sends fly presenter commands (present/retract/position/home) and receives status via ZMQ REQ/REP.
- `flomington.py`: Placeholder for future Flomington Drosophila stock management integration (Supabase backend, QR code lookup, session tagging).
- `hub.py`: Central `CommsHub` that manages all endpoint lifecycles and exposes a single polling/sending interface for the stimulus loop. Also provides the `vr-hub` CLI entry point.

Each endpoint implements the `Endpoint` ABC (`base.py`): `start()`, `stop()`, `poll()`, and a `connected` property. Endpoints run background threads and expose non-blocking `poll()` methods.

### Session Management (`session/`)

The `session` module manages experiment session lifecycles:

- `session.py`: `Session` class that tracks trial boundaries, collects timestamped events from the CommsHub, and persists data as `session.json` (metadata), `trials.csv` (timing), and per-trial event JSON files.
- `recorder.py`: Lower-level recording utilities for continuous data streams (FicTrac frames, stimulus state).

Sessions work with any subset of hardware -- no comms, no Flomington, or no external hardware at all.

### GUI Panels

The Dear ImGui GUI (`gui/app.py`) composes the following panels (in `gui/panels/`):

- **StimulusPanel**: Live stimulus preview and control (start/stop, fly position, heading).
- **ConfigEditorPanel**: Edit all configuration sections at runtime.
- **CommsPanel**: CommsHub connection status and endpoint monitoring.
- **SessionPanel**: Session lifecycle controls (start/stop/save), trial management, and summary.
- **CalibrationPanel**: Camera/projector calibration settings and pipeline trigger.
- **MappingPanel**: Warp map loading, dimensions display, and structured-light pipeline trigger.
- **FlomingtonPanel**: Fly stock/cross database lookup and session linking.
- **FicTracPanel**: Dedicated treadmill/ball-tracking data (heading, speed, position, speed history).
- **ScanImagePanel**: 2-photon imaging sync (trial events, frame clock, acquisition status).
- **OptogeneticsPanel**: LED control (on/off/pulse, intensity, channel, protocol presets).
- **BehaviourPanel**: Experiment dashboard (type selector, hardware checklist, session/recording status).
- **TrackingPanel**: Virtual fly vs real fly relationship (positions, headings, distance, angular offset).

### Graceful Degradation

The system is designed so that every external dependency is optional. The core stimulus rendering works standalone with no hardware attached. The `CommsHub` creates only those endpoints whose port is configured to a positive value; endpoints that fail to start are logged as warnings but do not prevent the rest from running. The `Session` module works with or without a `CommsHub`. GUI panels display placeholder states when their backing subsystem is unavailable. This means a developer can run `vr-fly3d` on a laptop with no projector, no cameras, no FicTrac, and no network, and still get a fully functional autonomous fly simulation with minimap overlay.

## Build & Test Commands

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=flocroscope

# Type checking
mypy src/flocroscope/

# Linting
ruff check src/
```

## CLI Entry Points

```bash
vr-fly3d      # 3D GLB fly stimulus
vr-fly2d      # 2D sprite fly stimulus
vr-warp-test  # Warp circle calibration test
vr-calibrate  # Calibration pipeline
vr-gui        # Dear ImGui GUI
vr-hub        # Standalone CommsHub for testing communications
```

## Dependencies

- **Core**: numpy, opencv-python, pygame, PyOpenGL, pygltflib, PyYAML
- **Optional**: screeninfo, harvesters (Alvium), rotpy (FLIR), imgui[pygame] (GUI)
- **Dev**: pytest, pytest-cov, ruff, mypy

## Coding Standards

- Python 3.10+ (use `X | Y` union syntax, not `Optional[X]`)
- Google Python Style Guide docstrings
- Type annotations on all public APIs
- Tests written before implementation (TDD)
- Conventional commit messages: `feat(module): description`

## Test Markers

- `@pytest.mark.gpu`: Requires OpenGL context (skipped by default)
- `@pytest.mark.hardware`: Requires physical camera/projector (skipped by default)

## Legacy Files

Original scripts are archived in `src/flocroscope/legacy/` for reference. The key decomposition:

| Legacy File | New Location |
|---|---|
| `3d_object_fly4.py` | `rendering/*`, `stimulus/fly_3d.py`, `stimulus/autonomous.py`, `display/minimap.py`, `math_utils/*` |
| `mapping_utils.py` | `mapping/structured_light.py` |
| `fisheye_KDxi.py` | `calibration/fisheye.py` |
| `mapping_pipeline.py` | `mapping/pipeline.py` |
| `CamAlvium.py` / `CamRotPy.py` | `cameras/alvium.py` / `cameras/rotpy_driver.py` |
