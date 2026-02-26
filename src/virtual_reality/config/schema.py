"""Dataclass configuration schemas for the virtual reality system.

Each subsystem has its own configuration dataclass. The top-level
``VirtualRealityConfig`` composes them all into a single tree that
can be serialized to / deserialized from YAML.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArenaConfig:
    """Circular arena geometry.

    Attributes:
        radius_mm: Radius of the circular arena in millimeters.
    """

    radius_mm: float = 40.0


@dataclass
class FlyModelConfig:
    """3D fly model loading and scaling.

    Attributes:
        model_path: Path to the GLB model file.
        phys_length_mm: Target physical length (longest mesh dimension)
            in millimeters.
        base_scale: Extra multiplier applied after physical scaling.
        yaw_offset_deg: Degrees to rotate the model so its nose faces
            the motion direction.
    """

    model_path: str = ""
    sprite_folder: str = ""
    phys_length_mm: float = 3.0
    base_scale: float = 1.0
    yaw_offset_deg: float = 0.0


@dataclass
class CameraConfig:
    """Observer camera position and projection.

    Attributes:
        x_mm: Camera X position in millimeters.
        y_mm: Camera Y position in millimeters.
        height_mm: Camera height above the arena plane in millimeters.
        speed_mm_s: Camera translation speed in mm/s.
        turn_deg_s: Camera rotation speed in degrees/s.
        stand_turn_mult: Multiplier on turn speed when camera is
            stationary.
        z_speed_mm_s: Camera vertical speed in mm/s.
        fov_x_deg: Horizontal field of view in degrees.
        fov_y_deg: Vertical field of view in degrees.
        projection: Projection mode: ``perspective``, ``equirect``,
            or ``equidistant``.
        allow_ultrawide: Allow FOV near or beyond 180 degrees.
        flip_model_for_ultrawide: Flip mesh about X for spherical
            projection to keep the fly upright.
    """

    x_mm: float = 0.0
    y_mm: float = -40.0
    height_mm: float = 0.89
    speed_mm_s: float = 20.0
    turn_deg_s: float = 200.0
    stand_turn_mult: float = 1.5
    z_speed_mm_s: float = 20.0
    fov_x_deg: float = 200.0
    fov_y_deg: float = 60.0
    projection: str = "equirect"
    allow_ultrawide: bool = True
    flip_model_for_ultrawide: bool = True


@dataclass
class MovementConfig:
    """Fly movement parameters.

    Attributes:
        speed_mm_s: Forward speed in mm/s.
        back_mm_s: Backward speed in mm/s.
        turn_deg_s: Turn rate in degrees/s.
        stand_turn_mult: Multiplier on turn speed when standing still.
        walk_turn_noise_deg_rms: Per-frame heading noise (RMS degrees)
            applied during forward movement.
        walk_trans_noise_mm_rms: Per-frame lateral noise (RMS mm)
            applied during forward movement.
        start_x: Initial fly X position in mm.
        start_y: Initial fly Y position in mm.
        start_heading_deg: Initial fly heading in degrees.
    """

    speed_mm_s: float = 20.0
    back_mm_s: float = 12.8
    turn_deg_s: float = 200.0
    stand_turn_mult: float = 1.5
    walk_turn_noise_deg_rms: float = 20.0
    walk_trans_noise_mm_rms: float = 1.0
    start_x: float = 0.0
    start_y: float = -20.0
    start_heading_deg: float = 0.0


@dataclass
class AutonomousConfig:
    """Autonomous fly state machine parameters.

    Attributes:
        enabled: Whether autonomous mode is active.
        mean_run_dur: Mean duration of the running state in seconds.
        mean_pause_dur: Mean duration of the paused state in seconds.
        turn_std_deg: Standard deviation of random turn during pause.
        edge_turn_deg: Stronger turn applied near the arena boundary.
        edge_thresh_frac: Fraction of arena radius at which edge
            avoidance begins.
    """

    enabled: bool = True
    mean_run_dur: float = 1.0
    mean_pause_dur: float = 0.7
    turn_std_deg: float = 80.0
    edge_turn_deg: float = 120.0
    edge_thresh_frac: float = 0.8


@dataclass
class LightingConfig:
    """Phong lighting for 3D rendering.

    Four directional lights from above (N, E, S, W).

    Attributes:
        ambient: Base ambient light multiplier.
        intensities: Strengths for N, E, S, W directional lights.
        elevation_deg: Light elevation angle above horizon (degrees).
        max_gain: Maximum allowed total light gain.
    """

    ambient: float = 0.6
    intensities: tuple[float, ...] = (2.0, 2.0, 2.0, 2.0)
    elevation_deg: float = 65.0
    max_gain: float = 4.0


@dataclass
class MinimapConfig:
    """2D overhead minimap visualization.

    Attributes:
        enabled: Whether to show the minimap overlay.
        width: Minimap width in pixels.
        height: Minimap height in pixels.
        pad: Padding from screen edge in pixels.
        trail_secs: Duration of position trail in seconds.
        trail_color: RGB color tuple for the trail.
        trail_thick: Trail line thickness in pixels.
        hz: Minimap refresh rate in Hz.
    """

    enabled: bool = True
    width: int = 420
    height: int = 420
    pad: int = 24
    trail_secs: float = 5.0
    trail_color: tuple[int, ...] = (255, 200, 0)
    trail_thick: int = 2
    hz: int = 60


@dataclass
class WarpConfig:
    """Projector warp map paths.

    Attributes:
        mapx_path: Path to the mapx.npy warp map file.
        mapy_path: Path to the mapy.npy warp map file.
    """

    mapx_path: str = ""
    mapy_path: str = ""


@dataclass
class DisplayConfig:
    """Display and window settings.

    Attributes:
        bg_color: Background color as an RGB tuple (0-255).
        target_fps: Target frames per second.
        borderless: Whether to create a borderless window.
        monitor: Which monitor to use: ``right`` or ``left``.
    """

    bg_color: tuple[int, ...] = (255, 255, 255)
    target_fps: int = 60
    borderless: bool = True
    monitor: str = "right"


@dataclass
class ScalingConfig:
    """Physical-to-pixel scaling parameters.

    Attributes:
        screen_distance_mm: Fixed physical eye-to-screen distance.
        apparent_distance_mm: Override for apparent distance. ``None``
            uses the live camera-fly separation.
        dist_scale_smooth_hz: Smoothing rate for scale transitions.
        min_cam_fly_dist_mm: Fallback minimum camera-fly distance
            (used only when *auto_min_distance* is ``False``).
        auto_min_distance: Derive the minimum distance from the near
            plane and fly bounding sphere instead of using the
            hardcoded *min_cam_fly_dist_mm*.
        near_plane_safety: Safety margin multiplier for the derived
            minimum distance.
    """

    screen_distance_mm: float = 60.0
    apparent_distance_mm: float | None = None
    dist_scale_smooth_hz: float = 8.0
    min_cam_fly_dist_mm: float = 1.5
    auto_min_distance: bool = True
    near_plane_safety: float = 1.2


@dataclass
class CalibrationConfig:
    """Calibration pipeline settings.

    Attributes:
        camera_type: Camera driver to use: ``alvium`` or ``rotpy``.
        proj_w: Projector width in pixels.
        proj_h: Projector height in pixels.
        mode: Capture mode: ``gray`` or ``sine_hybrid``.
        periods_x: Number of sine periods along X axis.
        periods_y: Number of sine periods along Y axis.
        nphase: Number of phase-shift steps.
        avg_per: Number of frames to average per pattern.
        exposure_ms: Camera exposure time in milliseconds.
        gain_db: Camera gain in decibels.
    """

    camera_type: str = "alvium"
    proj_w: int = 1280
    proj_h: int = 800
    mode: str = "sine_hybrid"
    periods_x: int = 128
    periods_y: int = 96
    nphase: int = 15
    avg_per: int = 5
    exposure_ms: float = 10.0
    gain_db: float = 0.0


@dataclass
class CommsConfig:
    """Inter-process communication settings.

    All endpoints are optional.  Set a port to ``0`` to disable
    that endpoint.  The system runs normally with any subset of
    endpoints active.

    Attributes:
        enabled: Master switch for the comms subsystem.
        fictrac_host: FicTrac TCP host address.
        fictrac_port: FicTrac socket port (0 = disabled).
        fictrac_ball_radius_mm: Physical ball radius for rad → mm
            conversion.
        scanimage_port: ScanImage TCP server port (0 = disabled).
        led_port: Optogenetics LED ZMQ PUB port (0 = disabled).
        presenter_host: Fly presenter controller host.
        presenter_port: Fly presenter ZMQ REQ port (0 = disabled).
        log_messages: Whether to log individual messages at DEBUG.
    """

    enabled: bool = False
    fictrac_host: str = "localhost"
    fictrac_port: int = 2000
    fictrac_ball_radius_mm: float = 4.5
    scanimage_port: int = 5000
    led_port: int = 5001
    presenter_host: str = "localhost"
    presenter_port: int = 5002
    log_messages: bool = False


@dataclass
class SessionConfig:
    """Experiment session settings.

    Attributes:
        output_dir: Directory for session data output.
        auto_save: Whether to auto-save session events.
        log_fictrac: Whether to log raw FicTrac data.
        log_stimulus: Whether to log stimulus state each frame.
        log_interval_ms: Minimum interval between log entries in ms.
    """

    output_dir: str = "data/sessions"
    auto_save: bool = True
    log_fictrac: bool = True
    log_stimulus: bool = True
    log_interval_ms: float = 16.67  # ~60 Hz


@dataclass
class VirtualRealityConfig:
    """Top-level configuration composing all subsystem configs.

    Attributes:
        arena: Circular arena geometry.
        fly_model: 3D fly model loading and scaling.
        camera: Observer camera position and projection.
        movement: Fly movement parameters.
        autonomous: Autonomous fly state machine.
        lighting: Phong lighting for 3D rendering.
        minimap: 2D overhead minimap visualization.
        warp: Projector warp map paths.
        display: Display and window settings.
        scaling: Physical-to-pixel scaling parameters.
        calibration: Calibration pipeline settings.
        comms: Inter-process communication settings.
        session: Experiment session settings.
    """

    arena: ArenaConfig = field(default_factory=ArenaConfig)
    fly_model: FlyModelConfig = field(default_factory=FlyModelConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    movement: MovementConfig = field(default_factory=MovementConfig)
    autonomous: AutonomousConfig = field(default_factory=AutonomousConfig)
    lighting: LightingConfig = field(default_factory=LightingConfig)
    minimap: MinimapConfig = field(default_factory=MinimapConfig)
    warp: WarpConfig = field(default_factory=WarpConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    scaling: ScalingConfig = field(default_factory=ScalingConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    comms: CommsConfig = field(default_factory=CommsConfig)
    session: SessionConfig = field(default_factory=SessionConfig)


def _resolve_default_paths() -> VirtualRealityConfig:
    """Create a config with platform-aware default paths filled in."""
    is_mac = sys.platform == "darwin"
    config = VirtualRealityConfig()

    if is_mac:
        base = Path("/Users/fkampf/Documents")
        cal = base / "screen.calibration" / "configs"
        config.fly_model.model_path = str(
            base / "virtual.fly" / "testmodel.glb"
        )
        config.fly_model.sprite_folder = str(
            base / "virtual.fly" / "og_pics"
        )
    else:
        cal = Path("D:/screen.calibration/configs")
        config.fly_model.model_path = r"D:\virtual.fly\fly.glb"
        config.fly_model.sprite_folder = r"D:\virtual.fly\og_pics"

    mapping = cal / "camera.projector.mapping"
    config.warp.mapx_path = str(
        mapping / "mapx.experimental.npy"
    )
    config.warp.mapy_path = str(
        mapping / "mapy.experimental.npy"
    )

    config.camera.y_mm = -config.arena.radius_mm
    return config
