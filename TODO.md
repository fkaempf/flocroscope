# TODO — Flocroscope

Things we still want to implement, roughly in priority order.

## High Priority

### Flomington Supabase Integration
- Replace placeholder methods in `src/flocroscope/comms/flomington.py` with real `supabase-py` SDK calls
- Query `stocks` and `crosses` tables with field maps (camelCase JS / snake_case Postgres)
- Real-time subscriptions via `postgres_changes` channel
- QR code scanning: parse `?s=<8-char-id-prefix>` URLs to look up stocks/crosses
- Auto-tag sessions with fly metadata (genotype, cross parents, age)
- Push trial summaries back to Flomington as cross notes
- Respect ripening logic (3 days optogenetics/retinal, 5 days GCaMP)

### Calibration Pipeline Wiring
- Wire `vr-calibrate` CLI and CalibrationPanel to real pipeline stages:
  1. Chessboard detection from camera captures
  2. Fisheye K/D/xi or pinhole K/D intrinsic calibration
  3. Structured-light projector-camera mapping (sine/gray patterns)
  4. Optional sparse dot-grid refinement
  5. Save `mapx.npy` / `mapy.npy` output
- Requires hardware: Alvium or FLIR camera + projector

### Mapping Pipeline GUI
- Wire MappingPanel "Run Mapping Pipeline" to structured-light pipeline
- Show live progress (pattern number, phase decoding status)
- Preview loaded warp maps as a heatmap overlay

## Medium Priority

### Ruff + Mypy Clean Pass
- Run `ruff check src/ tests/ --fix` and resolve remaining warnings
- Run `ruff format src/ tests/` for consistent style
- Run `mypy src/flocroscope/` and fix type errors
- CI workflows (`.github/workflows/lint.yml`) are ready but haven't been validated

### Video Recording
- Record stimulus output (what the projector shows) to video file
- Could use `cv2.VideoWriter` on the rendered frame each loop iteration
- Optional: record camera feed simultaneously for verification

### Multi-Fly Stimulus
- Render multiple virtual flies simultaneously in the arena
- Each with independent position, heading, and controller
- Configurable via YAML (number of flies, spawn positions)

### Session Panel — Live Comms Display
- Pass CommsHub to SessionPanel for live FicTrac heading/speed display
- Show ScanImage frame sync status during recording
- Add "Link to Flomington" button that triggers stock/cross lookup

## Low Priority

### Sphinx / MkDocs API Documentation
- Auto-generate API docs from docstrings
- Host on GitHub Pages alongside the code
- Include architecture diagrams and usage guides

### GPU CI with Mesa Software Renderer
- Tests that need OpenGL/pygame currently skip in CI
- Install Mesa `llvmpipe` in GitHub Actions to run them
- Would cover: window creation, surface conversion, shader compilation

### pip install Workflow
- Currently requires `$env:PYTHONPATH` to run
- `pip install -e ".[gui,dev]"` should work but hasn't been tested end-to-end on Windows
- Add a setup verification script

### CLI Improvements
- `vr-fly3d --list-monitors` to show available displays
- `vr-gui --theme dark/light` for ImGui theme selection
- Config validation with clear error messages on startup

### Hardware Test Stubs
- Stubs exist in `tests/test_hardware/test_hardware_stubs.py` with `@pytest.mark.hardware`
- Flesh out with expected behavior for FicTrac live connection, camera capture
- Run manually when hardware is connected

---

*Last updated: 2026-03-06*
