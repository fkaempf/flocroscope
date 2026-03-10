# The Flo-Suite

**Three tools for the complete Drosophila neuroscience workflow: genetics, experiments, and stimulus delivery.**

---

## Executive Summary

The flo-suite is a set of three interconnected software tools that together cover
the full lifecycle of a Drosophila neuroscience experiment -- from maintaining fly
stocks and planning genetic crosses, through scheduling and tracking experiments,
to delivering real-time visual stimuli during two-photon imaging and optogenetics
sessions.

| App | Purpose | Technology | Repository |
|-----|---------|------------|------------|
| **Flomington** | Fly stock and cross management | React 18, Tailwind, Supabase | [fkaempf/flomington](https://github.com/fkaempf/flomington) |
| **Floboratory** | Experiment tracking and review | React 18, Tailwind, Supabase | [fkaempf/floboratory](https://github.com/fkaempf/floboratory) |
| **Flocroscope** | Virtual fly stimulus and hardware control | Python 3.10+, OpenGL, Dear ImGui | [fkaempf/flocroscope](https://github.com/fkaempf/flocroscope) |

The three apps share a single Supabase PostgreSQL database, a common user list,
and a deep-link URL scheme that lets you jump between them with one click. Each
app is independently useful. Together, they eliminate the gap between genetics
bookkeeping and experimental data.

---

## The Problem

A typical Drosophila neuroscience lab juggles three disconnected workflows:

1. **Genetics** -- Which stocks do we have? Which crosses are in progress? Is
   this cross old enough to use? Who is supposed to flip that vial?
2. **Experiments** -- Which genotype was imaged on Tuesday? Did the PI review
   that dataset? Where is the raw data for trial 47?
3. **Stimulus delivery** -- Render the virtual fly, synchronize with the
   two-photon microscope, trigger the LED, and record everything at 60 fps.

These workflows are traditionally managed with spreadsheets, sticky notes, and
one-off scripts. The flo-suite replaces all of them with purpose-built tools
that share data automatically.

---

## The Three Apps

### Flomington -- Fly Stock and Cross Management

Flomington is a lab-internal web app for managing Drosophila genetics. It runs
as a StatiCrypt-encrypted single HTML file hosted on GitHub Pages.

**What it tracks:**

- **Stocks** -- genotype, source (BDSC / VDRC / Kyoto / Janelia), genetic tags
  (GAL4, UAS, Split-GAL4, CsChrimson, GCaMP, balancers), storage temperature,
  copies, flip scheduling, and assigned maintainer.
- **Crosses** -- eight-stage lifecycle from setup through screening, parent
  genotypes, experiment type, target date, temperature-dependent timelines, and
  ownership.
- **Virgin banking** -- collection scheduling and inventory.
- **Labels** -- QR-coded vial labels with 8-character ID prefixes for scanning.

**Key features:**

- localStorage-first with Supabase real-time sync (3-second debounce push,
  instant pull via `postgres_changes` channel).
- PIN-based multi-user authentication.
- Stock splitting, transfers between team members, and flip reminders.
- Temperature-aware timeline calculations (25C vs 18C).
- Genetic tag auto-detection from genotype strings.

**Cross lifecycle stages:**

```
  1. set up
  2. waiting for virgins
  3. collecting virgins
  4. waiting for progeny
  5. collecting progeny
  6. ripening  (3 days opto / 5 days GCaMP)
  7. screening
  8. done
```

**Table prefix:** `flo_`

---

### Floboratory -- Experiment Manager

Floboratory is the experiment tracking layer that connects genetics to raw data.
It shares the same design system and Supabase instance as Flomington.

**What it tracks:**

- **Experiments** -- linked to a Flomington stock or cross via `source_id`,
  with experimenter, date, notes, raw data location, and analysis status.
- **Nine experiment types:** optogenetics, 2p, 2p+vr, behavior, flydisco, vr,
  dissection, immunostain, other.
- **Status workflow:** planned, in-progress, needs-review, complete (plus
  abandoned).
- **Flocroscope sessions** -- linked via `flocroscopeRef` field.

**Key features:**

- Same localStorage + Supabase architecture as Flomington.
- Type-driven progressive disclosure (optogenetics experiments do not show
  immunostain fields and vice versa).
- Audit trail for every change (server-side trigger-based logging).
- Review workflow with PI oversight and experiment locking.
- Deep-link URLs to jump to the source stock/cross in Flomington or the
  acquisition session in Flocroscope.
- Same user list and authentication model as Flomington.

**Status workflow:**

```
  planned --> in-progress --> needs-review --> complete
                  |
                  +--> abandoned
```

**Table prefix:** `flab_`

---

### Flocroscope -- Virtual Fly Stimulus and Hardware Control

Flocroscope is a Python package for rendering virtual fly stimuli and
controlling neuroscience hardware during experiments. It replaces ~40 legacy
scripts with a single modular system.

**What it does:**

- Renders a 3D GLB fly model with OpenGL, Phong lighting (4 directional lights),
  and three projection modes (perspective, equirectangular, equidistant).
- Applies projector warp correction using structured-light calibration maps
  (Gray code + sine phase for subpixel accuracy).
- Integrates with FicTrac ball-tracking, ScanImage two-photon microscopy,
  optogenetics LEDs, and a motorized fly presenter.
- Records trial-based session data: `session.json`, `trials.csv`, per-trial
  event logs, and 60 fps per-frame CSV (fly position, heading, FicTrac state).
- Provides a Dear ImGui GUI with 12 dockable panels.

**Stimulus lifecycle:**

```
  setup() --> update(dt, events) --> render() --> teardown()
```

**Hardware fallback chain:**

```
  FicTrac (treadmill) --> autonomous state machine --> keyboard control
```

Every hardware dependency is optional. The system runs a fully functional
autonomous fly simulation on a laptop with no projector, no cameras, no
FicTrac, and no network.

**CLI entry points:**

| Command | Purpose |
|---------|---------|
| `vr-fly3d` | 3D GLB fly stimulus |
| `vr-fly2d` | 2D sprite fly stimulus |
| `vr-warp-test` | Warp circle calibration test |
| `vr-calibrate` | Camera-projector calibration pipeline |
| `vr-gui` | Dear ImGui control panel (12 panels) |
| `vr-hub` | Standalone CommsHub for testing |

**GUI panels:**

| Panel | Purpose |
|-------|---------|
| Stimulus | Stimulus type selection, parameter editing, launch/stop |
| Session | Session lifecycle, trial management, Flomington auto-populate |
| Config Editor | Runtime editing of all 14 YAML config subsections |
| Comms | CommsHub endpoint status dashboard |
| Calibration | Camera/projector calibration settings and pipeline trigger |
| Mapping | Warp map loading and structured-light pipeline |
| Flomington | Stock/cross lookup by ID, session linking |
| FicTrac | Treadmill data: heading, speed, position, speed history |
| ScanImage | 2-photon sync: trial events, frame clock, acquisition status |
| Optogenetics | LED control: on/off/pulse, intensity, channel, protocols |
| Behaviour | Experiment dashboard: type selector, hardware checklist |
| Tracking | Virtual fly vs real fly: positions, headings, distance |

**YAML config subsections (14):** arena, fly_model, camera, movement,
autonomous, lighting, minimap, warp, display, scaling, calibration, comms,
session, flomington.

---

## Architecture

### System Overview

```
+------------------------------------------------------------------+
|                       SUPABASE  (PostgreSQL)                      |
|                                                                   |
|   flo_stocks    flo_crosses    flab_experiments    flab_audit_log  |
|                                                                   |
+--------+-----------------+------------------+---------------------+
         |                 |                  |
    real-time sync    real-time sync      supabase-py
   (postgres_changes) (postgres_changes)     (SDK)
         |                 |                  |
+--------+------+  +-------+--------+  +-----+-----------+
|               |  |                |  |                  |
|  FLOMINGTON   |  |  FLOBORATORY   |  |   FLOCROSCOPE    |
|  (React SPA)  |  |  (React SPA)   |  |   (Python pkg)   |
|               |  |                |  |                  |
| - Stock mgmt  |  | - Experiment   |  | - OpenGL render  |
| - Cross life- |  |   tracking     |  | - FicTrac recv   |
|   cycle       |  | - Review work- |  | - ScanImage sync |
| - QR labels   |  |   flow         |  | - LED control    |
| - Virgin bank |  | - PI oversight |  | - Dear ImGui GUI |
|               |  |                |  | - Session record |
+-------+-------+  +-------+--------+  +--------+--------+
        |                  |                     |
        +------ deep links ------+------deep links
```

### Component Architecture -- Flocroscope

```
+----------------------------------------------------------------+
|                        FLOCROSCOPE                              |
|                                                                 |
|  +------------------+   +-------------------+   +------------+ |
|  |   config/        |   |   stimulus/       |   |  display/  | |
|  | VirtualReality-  |   | Stimulus ABC      |   | Monitor    | |
|  |   Config (YAML)  |   |  Fly3DStimulus    |   | Surface    | |
|  | 14 subsections   |   |  FlySpriteStim    |   | Window     | |
|  +--------+---------+   |  WarpCircleStim   |   | Minimap    | |
|           |              +--------+----------+   +-----+------+ |
|           |                       |                    |        |
|  +--------v---------+   +--------v----------+         |        |
|  |   comms/         |   |   rendering/      +---------+        |
|  | CommsHub         |   | Shaders (GLSL)    |                  |
|  |  FicTracRecv     |   | GL utils (FBO)    |                  |
|  |  ScanImageSync   |   | GLB loader        |                  |
|  |  LedController   |   | Projections       |                  |
|  |  FlyPresenter    |   +-------------------+                  |
|  |  FlomingtonClient|                                          |
|  +--------+---------+   +-------------------+                  |
|           |              |   session/        |                  |
|  +--------v---------+   | Session lifecycle  |                  |
|  |   gui/           |   | TrialRecord       |                  |
|  | VirtualRealityApp|   | FrameRecorder     |                  |
|  | 12 ImGui panels  |   | JSON + CSV output |                  |
|  +------------------+   +-------------------+                  |
|                                                                 |
|  +-------------------+   +-------------------+                  |
|  |   calibration/    |   |   mapping/        |                  |
|  | Fisheye model     |   | Structured light  |                  |
|  | Pinhole model     |   | Warp maps         |                  |
|  | Intrinsics I/O    |   | Pipeline          |                  |
|  +-------------------+   +-------------------+                  |
+----------------------------------------------------------------+
```

---

## Data Flow

### Experiment Lifecycle (End to End)

The following diagram traces a single experiment from cross setup through
data analysis, showing how data flows between the three apps.

```
 FLOMINGTON                  FLOBORATORY                FLOCROSCOPE
 ----------                  -----------                -----------

 1. Create stock
    (genotype, source,
     genetic tags)
         |
         v
 2. Set up cross
    (virgin x male,
     experiment type)
         |
         |  source_id
         +-----------------> 3. Plan experiment
                                (type, date,
                                 source_id)
                                     |
 4. Cross ripens                     |
    (3d opto / 5d GCaMP)            |
         |                          |
         v                          v
 5. Cross ready              4. Status: in-progress
    (status: screening)              |
         |                          |
         |  QR scan                 |  flocroscopeRef
         +------------------------->+------------------+
                                                       |
                                                       v
                                               6. Run session
                                                  - Render stimulus
                                                  - Record FicTrac
                                                  - Sync ScanImage
                                                  - Trigger LEDs
                                                  - Log trials
                                                       |
                                                       v
                                               7. Save session
                                                  session.json
                                                  trials.csv
                                                  frames.csv
                                                       |
                                    +------------------+
                                    |  push results
                                    v
                             8. Status: needs-review
                                    |
                                    v
                             9. PI reviews data
                                    |
                                    v
                            10. Status: complete
```

### Data Flow Between Apps

```
+-------------+      source_id       +-------------+
|             |  ------------------> |             |
| FLOMINGTON  |                      | FLOBORATORY |
|             | <------------------  |             |
+------+------+   deep link back    +------+------+
       |                                    |
       | QR scan                            | flocroscopeRef
       | (stock/cross ID)                   | (session ID)
       |                                    |
       v                                    v
+------+------------------------------------+------+
|                                                  |
|                  FLOCROSCOPE                     |
|                                                  |
|  Reads:                                          |
|    - Stock genotype, genetic tags                |
|    - Cross parents, status, experiment type      |
|    - Ripening state (ready / not ready)          |
|                                                  |
|  Writes:                                         |
|    - Session metadata (stimulus, duration)        |
|    - Trial count and timing                      |
|    - Cross notes (experiment summary)            |
|                                                  |
+--------------------------------------------------+
```

---

## Cross-Link Scheme

All three apps support bidirectional deep links so users can navigate between
them without copy-pasting IDs.

| From | To | URL Pattern | Purpose |
|------|----|-------------|---------|
| Floboratory | Flomington | `flomington/?s=<id-prefix>` | View source stock/cross |
| Floboratory | Flocroscope | `flocroscope/session/<session-id>` | View acquisition session |
| Flocroscope | Flomington | `flomington/?s=<id-prefix>` | View fly being tested |
| Flocroscope | Floboratory | `floboratory/?exp=<experiment-id>` | View parent experiment |
| Flomington | Floboratory | `floboratory/?source=<stock-or-cross-id>` | View experiments for this stock |

QR labels printed from Flomington encode `?s=<8-char-id-prefix>` URLs. Scanning
a QR code from Flocroscope's GUI auto-populates the session with the fly's
genotype, stock name, cross parents, and age.

---

## Shared Infrastructure

### Supabase Database

All three apps share a single Supabase project. Table prefixes prevent
collisions.

| Prefix | App | Key Tables |
|--------|-----|------------|
| `flo_` | Flomington | `flo_stocks`, `flo_crosses`, `flo_virgin_bank` |
| `flab_` | Floboratory | `flab_experiments`, `flab_tags`, `flab_audit_log` |

Flocroscope reads from `flo_` tables via `supabase-py` and writes session
references to `flab_` tables.

### Sync Protocol

The two web apps (Flomington and Floboratory) use an identical sync strategy:

1. **localStorage-first** -- all data is readable and writable offline.
2. **Push on change** -- modifications are pushed to Supabase with a debounce
   to batch rapid edits.
3. **Pull via real-time** -- Supabase `postgres_changes` channel delivers
   remote updates instantly.
4. **Conflict avoidance** -- a `markEdited()` mechanism flags locally-modified
   records to prevent overwrites from echoed push events.

Flocroscope uses the `supabase-py` SDK for direct queries (stock lookup, cross
lookup, session tagging) rather than real-time subscriptions.

### Authentication

| Mechanism | Scope |
|-----------|-------|
| StatiCrypt password | Decrypts the HTML file (same password for both web apps) |
| PIN-based user selection | Identifies the active user within each web app |
| Supabase anon key | Database access (shared across all three apps) |

All three apps share the same user list. Flocroscope's config stores the
current user name for session ownership tagging.

---

## Deployment

| App | Hosting | Build | Access |
|-----|---------|-------|--------|
| Flomington | GitHub Pages | Single HTML + StatiCrypt | `floriankaempf.com/flomington/` |
| Floboratory | GitHub Pages | Single HTML + StatiCrypt | `floriankaempf.com/floboratory/` |
| Flocroscope | Local install | `pip install -e ".[all]"` | CLI commands (`vr-gui`, `vr-fly3d`, etc.) |

### Flocroscope Installation

```bash
git clone https://github.com/fkaempf/flocroscope.git
cd flocroscope
pip install -e ".[all]"
vr-gui
```

### Flocroscope Dependencies

| Category | Packages |
|----------|----------|
| Core | numpy, opencv-python, pygame, PyOpenGL, pygltflib, PyYAML |
| Display | screeninfo |
| Cameras | harvesters (Alvium), rotpy (FLIR) |
| GUI | imgui[pygame] |
| Comms | pyzmq |
| Dev | pytest, pytest-cov, ruff, mypy |

Every optional dependency is exactly that -- optional. The system gracefully
degrades when any package is missing.

---

## Graceful Degradation

A core design principle across the suite: **nothing is required; everything
is additive.** Each app works standalone, and each subsystem within Flocroscope
works independently.

| Scenario | What Happens |
|----------|--------------|
| No Supabase configured | Web apps work fully offline via localStorage. Flocroscope skips Flomington integration. |
| No FicTrac connected | Flocroscope falls back to autonomous AI, then keyboard control. |
| No ScanImage running | Session proceeds without trial-sync events. |
| No LED controller | LED commands are silently dropped. |
| No fly presenter | Presenter commands are silently dropped. |
| No cameras attached | Calibration pipeline unavailable; stimulus rendering works normally. |
| No GPU / OpenGL | Stimulus rendering unavailable; GUI and session management still work. |
| No pyzmq installed | LED and presenter endpoints are skipped at import time. |
| No imgui installed | CLI stimulus commands still work; GUI is unavailable. |
| Flomington not configured | Session panel hides Flomington section; manual genotype entry works. |
| Floboratory not configured | Flocroscope sessions are saved locally only. |

---

## Hardware Integration (Flocroscope)

Flocroscope communicates with four hardware endpoints through the CommsHub.
Each endpoint runs a background thread with a non-blocking `poll()` interface.

```
+-------------------+     TCP      +-------------------+
|     FicTrac       | -----------> |  FicTracReceiver  |
| (ball tracking)   |   port 2000  | heading, speed,   |
+-------------------+              | x, y (rad -> mm)  |
                                   +-------------------+

+-------------------+     TCP      +-------------------+
|    ScanImage      | -----------> |  ScanImageSync    |
| (2-photon scope)  |   port 5000  | frame_clock,      |
+-------------------+              | trial_start/stop  |
                                   +-------------------+

+-------------------+   ZMQ PUB    +-------------------+
|  LED Controller   | <----------- |  LedController    |
| (optogenetics)    |   port 5001  | on/off/pulse/pwm  |
+-------------------+              | intensity/channel |
                                   +-------------------+

+-------------------+  ZMQ REQ/REP +-------------------+
|  Fly Presenter    | <----------> |  FlyPresenter     |
| (mechanical)      |   port 5002  | present/retract/  |
+-------------------+              | position/home     |
                                   +-------------------+
```

All ports are configurable. Setting any port to `0` disables that endpoint.
The master switch `comms.enabled = false` disables the entire subsystem.

---

## Session Data Format

Every Flocroscope session produces a self-contained directory:

```
data/sessions/<session-id>/
    session.json              # Session metadata, config snapshot
    trials.csv                # Trial timing (number, start, end, duration)
    frames.csv                # Per-frame data at 60 fps
    events_<trial-id>.json    # Timestamped events per trial
```

**session.json** fields: `session_id`, `start_time`, `end_time`,
`experimenter`, `stimulus_type`, `fly_stock_id`, `fly_cross_id`,
`fly_genotype`, `notes`, `trial_count`, `config_snapshot`.

**frames.csv** columns: `timestamp`, `frame`, `fly_x`, `fly_y`,
`fly_heading_deg`, `fly_speed`, `cam_x`, `cam_y`, `cam_heading_deg`,
`fictrac_heading_rad`, `fictrac_x_rad`, `fictrac_y_rad`, `fictrac_speed`.

---

## Future Roadmap

### Near-Term

- **Flomington integration in Flocroscope** -- Complete the `FlomingtonClient`
  placeholder: Supabase queries for stock/cross lookup, QR code scanning,
  session auto-tagging, and results push-back.
- **Floboratory deep links** -- Wire `flocroscopeRef` field to open session
  data directly from the experiment record.
- **FlyDisco compatibility** -- Adapt Flocroscope's session format for
  FlyDisco hardware workflows (arobie/FlyDiscoHardware).

### Medium-Term

- **Analysis pipeline** -- Post-session analysis scripts that read `frames.csv`
  and produce summary statistics, trajectory plots, and behavioral metrics.
- **Cross-app notifications** -- Push notifications from Flomington to
  Floboratory when a cross reaches the "screening" stage.
- **Batch experiment planning** -- Create multiple Floboratory experiments from
  a set of Flomington crosses in one action.

### Long-Term

- **Central dashboard** -- A unified view across all three apps showing active
  crosses, pending experiments, and recent sessions.
- **Multi-rig support** -- Multiple Flocroscope instances reporting to the same
  Floboratory project.
- **Data archival** -- Automatic upload of session data to institutional storage
  with DOI minting.

---

## Quick Reference

### Repository URLs

| App | Repository |
|-----|------------|
| Flomington | `https://github.com/fkaempf/flomington` |
| Floboratory | `https://github.com/fkaempf/floboratory` |
| Flocroscope | `https://github.com/fkaempf/flocroscope` |

### Tech Stack Summary

|  | Flomington | Floboratory | Flocroscope |
|--|------------|-------------|-------------|
| **Language** | JavaScript (ES2022) | JavaScript (ES2022) | Python 3.10+ |
| **UI** | React 18 + Tailwind | React 18 + Tailwind | Dear ImGui + pygame |
| **Rendering** | -- | -- | OpenGL 3.3+ |
| **Storage** | localStorage + Supabase | localStorage + Supabase | YAML + JSON + CSV |
| **DB tables** | `flo_*` | `flab_*` | reads `flo_*`, writes `flab_*` |
| **Hosting** | GitHub Pages | GitHub Pages | Local install |
| **Encryption** | StatiCrypt | StatiCrypt | -- |
| **Auth** | PIN-based | PIN-based | Config file |

---

*The flo-suite is developed and maintained by the Kaempf Lab.*
