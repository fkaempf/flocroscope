# Flocroscope

**Virtual fly stimulus rendering and projector-camera calibration for Drosophila neuroscience experiments.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-483%20passed-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20check-mypy-blue.svg)](https://mypy-lang.org/)

> **Part of the flo-suite** -- Flocroscope works alongside
> [Flomington](https://github.com/fkaempf/flomington) (Drosophila stock management)
> and [Floboratory](https://github.com/fkaempf/floboratory) (experiment tracking)
> to provide an end-to-end neuroscience workflow from fly genetics through stimulus
> delivery to data analysis. See [SUITE.md](SUITE.md) for the full ecosystem overview.

---

## Overview

Flocroscope renders realistic virtual fly stimuli inside a circular arena and
projects them through a calibrated projector-camera warp map. It is designed for
closed-loop neuroscience experiments where a tethered *Drosophila* on a FicTrac
treadmill interacts with a virtual conspecific displayed on a curved projection
screen.

The system consolidates two former standalone repositories -- `virtual.fly`
(24 Python scripts for stimulus rendering) and `screen.calibration` (~15 files
for projector mapping) -- into a single, well-structured, fully typed Python
package.

## Features

- **3D GLB fly model** -- OpenGL rendering with Phong lighting (4 directional
  lights), perspective / equidistant-fisheye / equirectangular projection modes,
  and automatic physical scaling (mm to pixels).
- **2D sprite fly** -- Lightweight turntable-image renderer using pre-rendered
  fly photographs, for setups that do not require full 3D.
- **Projector warp correction** -- Calibrated `mapx`/`mapy` lookup textures
  applied in a fullscreen-quad shader pass for accurate stimulus delivery on
  curved screens.
- **Structured-light calibration** -- Gray code for integer-precision mapping
  plus phase-shifted sinusoidal fringes for subpixel refinement.
- **Fisheye and pinhole camera calibration** -- MEI (xi) fisheye model and
  standard pinhole model with robust outlier filtering and intrinsics I/O.
- **Autonomous fly AI** -- Run/pause state machine with configurable durations,
  heading noise, and edge-avoidance steering near the arena boundary.
- **Control chain fallback** -- FicTrac treadmill (closed-loop) falls back to
  autonomous AI, which falls back to keyboard WASD control. Each layer activates
  automatically when the one above it is unavailable.
- **2D minimap overlay** -- Overhead view showing fly position, camera FOV cone,
  and timestamped movement trail.
- **Dear ImGui GUI** -- 12 dockable panels for real-time control, monitoring,
  and configuration editing.
- **Session management** -- Trial-based experiment lifecycle with JSON metadata,
  CSV trial summaries, per-trial event logs, and per-frame data recording.
- **Communications hub** -- Central manager for 5 inter-process endpoints
  (FicTrac, ScanImage, LED, Presenter, Flomington) with background threads and
  non-blocking polling.
- **Graceful degradation** -- Every external dependency is optional. The core
  stimulus runs standalone on a laptop with no projector, no cameras, no
  treadmill, and no network.
- **YAML configuration** -- 14 nested dataclass sections with sensible defaults.
  Override only what you need.

## Quick Start

**1. Install**

```bash
pip install -e ".[all]"
```

**2. Configure** (optional -- defaults work out of the box)

```bash
cp configs/example_minimal.yaml my_config.yaml
```

**3. Run**

```bash
vr-fly3d my_config.yaml
```

An autonomous virtual fly will walk around the arena. Press `Escape` to exit.
No hardware required.

## Installation

```bash
# Core only (rendering, calibration, config)
pip install -e .

# Individual extras
pip install -e ".[display]"    # screeninfo for multi-monitor detection
pip install -e ".[alvium]"     # Allied Vision Alvium camera driver
pip install -e ".[flir]"       # FLIR/Spinnaker camera driver via RotPy
pip install -e ".[gui]"        # Dear ImGui panels (imgui[pygame])
pip install -e ".[comms]"      # ZMQ endpoints (pyzmq)
pip install -e ".[dev]"        # pytest, pytest-cov, ruff, mypy

# Everything
pip install -e ".[all]"
```

### Core Dependencies

| Package | Purpose |
|---------|---------|
| numpy >= 1.24 | Array math, warp maps |
| opencv-python >= 4.8 | Calibration, image processing |
| pygame >= 2.5 | Window management, event loop |
| PyOpenGL >= 3.1 | OpenGL rendering |
| pygltflib >= 1.15 | GLB model loading |
| PyYAML >= 6.0 | Configuration serialization |

## CLI Entry Points

| Command | Description |
|---------|-------------|
| `vr-fly3d` | 3D GLB fly stimulus with full rendering pipeline |
| `vr-fly2d` | 2D sprite fly stimulus (turntable images) |
| `vr-warp-test` | Warp circle calibration verification |
| `vr-calibrate` | Projector-camera calibration pipeline |
| `vr-gui` | Dear ImGui GUI with all 12 panels |
| `vr-hub` | Standalone CommsHub for endpoint testing |

All commands accept a YAML config file as a positional argument. Without one,
platform-aware defaults are used.

## Architecture

```
src/virtual_reality/
    config/           # Dataclass schemas, YAML loader, platform paths
    cameras/          # Camera Protocol + Alvium/RotPy drivers + factory
    calibration/      # Fisheye/pinhole calibration, intrinsics I/O
    mapping/          # Structured light, warp maps, pipeline, refinement
    rendering/        # GL utils, shaders, GLB loader, projections
    math_utils/       # Matrix transforms, arena geometry, lighting
    stimulus/         # Stimulus ABC + Fly3D / FlySprite / WarpCircle + controllers
    display/          # Monitor picking, surface conversion, minimap, window
    pipeline/         # Calibration pipeline orchestrator
    comms/            # Inter-process communication endpoints + CommsHub
    session/          # Experiment session lifecycle + trial tracking
    gui/              # Dear ImGui application + 12 panels
    legacy/           # Archived original scripts (read-only reference)
```

### Stimulus Lifecycle

Every stimulus implements the same four-method interface:

```python
class Stimulus(ABC):
    def setup(self) -> None: ...       # Init GPU resources, load models
    def update(self, dt, events): ...  # Advance simulation state
    def render(self) -> None: ...      # Draw the current frame
    def teardown(self) -> None: ...    # Release resources
```

The built-in `run()` method adds a pygame event loop, FPS clock, optional
session recording, and automatic trial management.

### Stimulus Types

| Class | Module | Description |
|-------|--------|-------------|
| `Fly3DStimulus` | `stimulus/fly_3d.py` | Full 3D GLB model with Phong lighting, offscreen FBO, and warp pass |
| `FlySpriteStimulus` | `stimulus/fly_sprite.py` | 2D turntable images with angle-based sprite selection and warp correction |
| `WarpCircleStimulus` | `stimulus/warp_circle.py` | Oscillating circle through the warp map for calibration verification |

### Rendering Pipeline (Fly3D)

1. **Offscreen pass** -- Render the fly model to a framebuffer object (FBO) at
   camera resolution with Phong shading and the selected projection mode.
2. **Warp pass** -- Sample the offscreen texture through the `mapx`/`mapy` warp
   map via a fullscreen-quad shader to produce the projector-space output.

### Projection Modes

| Mode | Config Value | Use Case |
|------|-------------|----------|
| Perspective | `"perspective"` | Standard rectilinear projection |
| Equidistant fisheye | `"equidistant"` | Wide-angle curved screens |
| Equirectangular | `"equirect"` | Ultra-wide FOV (up to 360 degrees) |

## GUI Panels

The Dear ImGui interface (`vr-gui`) provides 12 panels grouped by function.

### Core

| Panel | Description |
|-------|-------------|
| **Stimulus** | Live stimulus preview and control (start/stop, fly position, heading) |
| **Session** | Session lifecycle (start/stop/save), trial management, summary stats |
| **Config Editor** | Edit all 14 configuration sections at runtime |
| **Comms** | CommsHub connection status and per-endpoint monitoring |

### Hardware

| Panel | Description |
|-------|-------------|
| **Calibration** | Camera/projector calibration settings, intrinsics display, pipeline trigger |
| **Mapping** | Warp map loading, dimensions display, structured-light pipeline trigger |

### Dedicated Endpoints

| Panel | Description |
|-------|-------------|
| **FicTrac** | Ball-tracking readout: heading, speed, position, speed history |
| **ScanImage** | 2-photon imaging sync: trial events, frame clock, acquisition status |
| **Optogenetics** | LED control: on/off/pulse, intensity, channel selection, protocol presets |

### Overview

| Panel | Description |
|-------|-------------|
| **Behaviour** | Experiment dashboard: type selector, hardware checklist, session/recording status |
| **Tracking** | Virtual fly vs real fly: positions, headings, distance, angular offset |
| **Flomington** | Fly stock/cross database lookup and session linking |

All panels degrade gracefully. When a backing subsystem is unavailable, the
panel displays a disabled state with a clear message.

## Communications

The `CommsHub` manages all inter-process communication. Each endpoint is
independently optional -- set its port to `0` or leave `comms.enabled: false`
to disable.

| Endpoint | Protocol | Port | Purpose |
|----------|----------|------|---------|
| **FicTrac** | TCP socket | 2000 | Ball-tracking: heading, speed, position (rad to mm via ball radius) |
| **ScanImage** | TCP server | 5000 | 2-photon trial events: frame clock, trial start/stop |
| **LED** | ZMQ PUB | 5001 | Optogenetics: on/off/pulse/PWM with intensity and channel |
| **Presenter** | ZMQ REQ/REP | 5002 | Fly positioning: present/retract/position/home + status |
| **Flomington** | Supabase | -- | Stock/cross lookup and session tagging (placeholder) |

Each endpoint runs a background thread with non-blocking `poll()`. Endpoints
that fail to connect are logged as warnings but do not prevent the rest of the
system from running.

### Control Chain

```
FicTrac treadmill (closed-loop)
    |  unavailable?
    v
Autonomous AI (run/pause state machine)
    |  disabled?
    v
Keyboard WASD (manual control)
```

Each layer activates automatically. A developer can run `vr-fly3d` on a laptop
with no treadmill and get a fully functional autonomous simulation.

## Graceful Degradation

Flocroscope is built so that every component beyond core rendering is optional.
The `CommsHub` creates only those endpoints whose port is configured to a
positive value. Endpoints that throw on `start()` are caught, logged, and
skipped. Camera drivers are imported lazily inside `start()` methods. Missing
SDKs produce a clear error, not an import crash. `pyzmq` is a soft dependency --
ZMQ-based endpoints defer their import. The config loader ignores unknown YAML
keys and fills missing sections with dataclass defaults.

This means you can run `vr-fly3d` on a laptop with no projector, no cameras, no
FicTrac, and no network, and still get a fully functional autonomous fly
simulation with minimap overlay.

## Configuration

YAML configuration with 14 nested sections. All values have sensible defaults.

### Minimal Config

```yaml
arena:
  radius_mm: 40.0

autonomous:
  enabled: true
```

### Full Reference

```yaml
arena:
  radius_mm: 40.0                  # Circular arena radius (mm)

fly_model:
  model_path: "fly.glb"           # Path to GLB model file
  sprite_folder: "og_pics"        # Path to sprite images (for vr-fly2d)
  phys_length_mm: 3.0             # Target fly body length (mm)

camera:
  fov_x_deg: 200.0                # Horizontal field of view (degrees)
  projection: "equirect"          # perspective | equirect | equidistant

movement:
  speed_mm_s: 20.0                # Forward speed (mm/s)
  start_heading_deg: 0.0          # Initial heading (degrees)

autonomous:
  enabled: true                   # Autonomous mode (false = keyboard)
  mean_run_dur: 1.0               # Mean run duration (seconds)

lighting:
  ambient: 0.6                    # Base ambient light
  intensities: [2.0, 2.0, 2.0, 2.0]  # N, E, S, W directional lights

minimap:
  enabled: true                   # Show overhead minimap overlay
  trail_secs: 5.0                 # Movement trail duration (seconds)

warp:
  mapx_path: ""                   # Path to mapx.npy (empty = no warp)
  mapy_path: ""                   # Path to mapy.npy

display:
  target_fps: 60                  # Target frame rate
  borderless: true                # Borderless window
  monitor: "right"                # Monitor selection

scaling:
  screen_distance_mm: 60.0        # Physical eye-to-screen distance (mm)

calibration:
  camera_type: "alvium"           # Camera driver: alvium | rotpy
  proj_w: 1280                    # Projector width (pixels)
  proj_h: 800                     # Projector height (pixels)

comms:
  enabled: false                  # Master switch for all endpoints
  fictrac_port: 2000              # FicTrac TCP port (0 = disabled)
  fictrac_ball_radius_mm: 4.5     # Ball radius for rad-to-mm
  scanimage_port: 5000            # ScanImage TCP port (0 = disabled)
  led_port: 5001                  # LED ZMQ PUB port (0 = disabled)
  presenter_port: 5002            # Presenter ZMQ REQ port (0 = disabled)
```

See [`configs/example.yaml`](configs/example.yaml) for a fully commented
reference with every field documented.

### Loading Configuration

```python
from virtual_reality.config.schema import VirtualRealityConfig
from virtual_reality.config.loader import load_config, save_config

config = VirtualRealityConfig()           # All defaults
config = load_config("my_config.yaml")    # Merge with defaults
save_config(config, "my_config.yaml")     # Save current state
```

## Session Data

Each experiment session produces a self-contained directory:

```
data/sessions/<session-id>/
    session.json       # Metadata (config, start/end times, trial count)
    trials.csv         # Trial timing summary
    trial_001.json     # Timestamped events for trial 1
    frames.csv         # Per-frame stimulus state (60 fps)
```

## Calibration Pipeline

1. **Chessboard detection** -- Detect corners in captured images for camera
   intrinsics estimation.
2. **Fisheye K/D/xi calibration** -- Fit the MEI omnidirectional model (or
   standard pinhole) with robust outlier filtering.
3. **Structured-light mapping** -- Project Gray code + sine fringe patterns,
   capture with camera, decode to pixel-accurate correspondence.
4. **Warp map output** -- Produce `mapx.npy` / `mapy.npy` files consumed by
   the stimulus renderer as GPU textures.

```bash
vr-calibrate --config calibration_config.yaml
```

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest tests/

# Run tests with coverage
pytest tests/ --cov=virtual_reality

# Type checking
mypy src/virtual_reality/

# Linting
ruff check src/
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.gpu` | Requires OpenGL context (skipped by default) |
| `@pytest.mark.hardware` | Requires physical camera/projector (skipped by default) |

### Coding Standards

- Python 3.10+ with `X | Y` union syntax (not `Optional[X]`)
- Google Python Style Guide docstrings
- Type annotations on all public APIs
- Tests written before implementation (TDD)
- Conventional commit messages: `feat(module): description`

## License

[MIT](LICENSE)

---

*Flocroscope is part of the [flo-suite](SUITE.md) for Drosophila neuroscience experiment management.*
