"""2D sprite-based fly stimulus.

Displays pre-rendered turntable images of a fly as a 2D sprite,
with keyboard or autonomous control.  This is a lighter-weight
alternative to :class:`Fly3DStimulus` that does not require GLB
loading or 3D shaders.

The sprite is drawn in camera space and optionally warped to
projector space using the same warp map pipeline.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import deque
from pathlib import Path

import numpy as np

from virtual_reality.config.schema import VirtualRealityConfig
from virtual_reality.math_utils.arena import clamp_to_arena
from virtual_reality.stimulus.base import Stimulus

logger = logging.getLogger(__name__)


def _load_sprites(
    folder: str | Path,
    pattern: str = r"fly[-_]?(\d+)\.\w+$",
    near_white: int = 245,
    crop_margin_px: int = 2,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Load turntable sprite images, crop to bounding box, and return masks.

    Images are sorted by the angle extracted from their filename.
    Foreground pixels are those with any channel value below
    *near_white*.  Each sprite is cropped to the tight bounding box
    of the foreground mask plus *crop_margin_px* on each side.

    Args:
        folder: Directory containing sprite images.
        pattern: Regex with a capture group for the angle.
        near_white: Threshold below which a pixel is foreground.
        crop_margin_px: Extra pixels kept around the detected fly
            when cropping the sprite.

    Returns:
        ``(sprites, masks)`` where each list has one entry per
        angle, sorted by angle.  Sprites are BGR uint8, masks are
        boolean arrays.

    Raises:
        FileNotFoundError: If *folder* does not exist or is empty.
    """
    import cv2

    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Sprite folder not found: {folder}")

    entries: list[tuple[int, Path]] = []
    regex = re.compile(pattern)
    for p in folder.iterdir():
        m = regex.search(p.name)
        if m:
            angle = int(m.group(1))
            entries.append((angle, p))

    if not entries:
        raise FileNotFoundError(
            f"No sprites matching {pattern!r} in {folder}",
        )

    entries.sort(key=lambda e: e[0])

    sprites: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    for _, path in entries:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue

        # Build foreground mask (uint8 for cropping)
        if img.ndim == 2:
            fg = (img < near_white).astype(np.uint8)
        elif img.shape[2] == 4:
            fg = (img[:, :, 3] > 0).astype(np.uint8)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            fg = (gray < near_white).astype(np.uint8)

        # Convert to BGR
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Crop to tight bounding box of foreground
        ys, xs = np.where(fg > 0)
        if len(xs) == 0 or len(ys) == 0:
            continue
        x0 = max(0, int(xs.min()) - crop_margin_px)
        x1 = min(img.shape[1], int(xs.max()) + 1 + crop_margin_px)
        y0 = max(0, int(ys.min()) - crop_margin_px)
        y1 = min(img.shape[0], int(ys.max()) + 1 + crop_margin_px)

        sprites.append(img[y0:y1, x0:x1].copy())
        masks.append(fg[y0:y1, x0:x1].astype(bool))

    logger.info("Loaded %d sprites from %s", len(sprites), folder)
    return sprites, masks


def _angle_to_index(heading_deg: float, n_frames: int) -> int:
    """Map a heading angle to a sprite frame index.

    Args:
        heading_deg: Heading in degrees.
        n_frames: Total number of sprite frames.

    Returns:
        Index into the sprite list.
    """
    deg = heading_deg % 360.0
    frac = deg / 360.0
    idx = int(round(frac * (n_frames - 1)))
    return max(0, min(idx, n_frames - 1))


def _render_sprite_masked(
    canvas: np.ndarray,
    sprite: np.ndarray,
    mask: np.ndarray,
    center_x: int,
    center_y: int,
    scale: float = 1.0,
) -> None:
    """Blit a masked sprite onto a canvas at a given position.

    Only pixels where *mask* is True are copied.

    Args:
        canvas: BGR uint8 image (modified in place).
        sprite: BGR uint8 sprite image.
        mask: Boolean foreground mask.
        center_x: Center X position on the canvas.
        center_y: Center Y position on the canvas.
        scale: Scale factor applied to the sprite.
    """
    import cv2

    spr = sprite
    msk = mask
    if scale != 1.0:
        new_w = max(1, int(round(spr.shape[1] * scale)))
        new_h = max(1, int(round(spr.shape[0] * scale)))
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        spr = cv2.resize(spr, (new_w, new_h), interpolation=interp)
        msk = cv2.resize(
            msk.astype(np.uint8), (new_w, new_h),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool)

    h, w = spr.shape[:2]
    x0 = center_x - w // 2
    y0 = center_y - h // 2

    # Clip to canvas bounds
    x1 = max(0, x0)
    y1 = max(0, y0)
    x2 = min(canvas.shape[1], x0 + w)
    y2 = min(canvas.shape[0], y0 + h)

    if x1 >= x2 or y1 >= y2:
        return

    sx1 = x1 - x0
    sy1 = y1 - y0
    sx2 = sx1 + (x2 - x1)
    sy2 = sy1 + (y2 - y1)

    roi = canvas[y1:y2, x1:x2]
    spr_c = spr[sy1:sy2, sx1:sx2]
    msk_c = msk[sy1:sy2, sx1:sx2]
    roi[msk_c] = spr_c[msk_c]


class FlySpriteStimulus(Stimulus):
    """2D sprite fly stimulus.

    Loads turntable images from a folder, selects the frame
    matching the fly's heading, and draws it at the projected
    screen position with distance-based scaling.

    Args:
        config: Full configuration dataclass.
        sprite_folder: Path to the folder with numbered sprite
            images.  If ``None``, uses ``config.fly_model.model_path``
            parent directory.
        ref_distance_mm: Distance at which the sprite is shown
            at *ref_height_px*.
        ref_height_px: Sprite height in pixels at *ref_distance_mm*.
    """

    def __init__(
        self,
        config: VirtualRealityConfig | None = None,
        sprite_folder: str | Path | None = None,
        ref_distance_mm: float = 220.0,
        ref_height_px: float = 260.0,
    ) -> None:
        if config is None:
            config = VirtualRealityConfig()
        self.config = config
        self._sprite_folder = sprite_folder
        self._ref_dist_mm = ref_distance_mm
        self._ref_height_px = ref_height_px
        self._use_warp = True

    def setup(self) -> None:
        """Load sprites, create window, initialise controllers."""
        import cv2
        import pygame

        cfg = self.config
        logger.info("FlySpriteStimulus.setup()")

        # Load sprites
        folder = self._sprite_folder
        if folder is None:
            if cfg.fly_model.sprite_folder:
                folder = Path(cfg.fly_model.sprite_folder)
            else:
                folder = Path(cfg.fly_model.model_path).parent
        self._sprites, self._masks = _load_sprites(folder)
        self._n_frames = len(self._sprites)
        if self._n_frames == 0:
            raise RuntimeError("No sprite frames loaded")

        self._ref_sprite_h = self._sprites[0].shape[0]

        # Try to load warp maps (optional for sprite mode)
        self._warp_enabled = False
        self._mapx = None
        self._mapy = None
        if cfg.warp.mapx_path and cfg.warp.mapy_path:
            try:
                from virtual_reality.mapping.warp import load_warp_map
                warp = load_warp_map(
                    cfg.warp.mapx_path, cfg.warp.mapy_path,
                )
                self._mapx = warp.mapx
                self._mapy = warp.mapy
                self._cam_w = warp.cam_w
                self._cam_h = warp.cam_h
                self._proj_w = warp.proj_w
                self._proj_h = warp.proj_h
                self._warp_enabled = True
            except Exception as exc:
                logger.warning("Could not load warp maps: %s", exc)

        # Window size
        if self._warp_enabled:
            win_w = self._proj_w
            win_h = self._proj_h
        else:
            win_w = cfg.calibration.proj_w
            win_h = cfg.calibration.proj_h
            self._cam_w = win_w
            self._cam_h = win_h

        # Pygame window (software rendering, no OpenGL needed)
        from virtual_reality.display.monitor import pick_monitor
        mon = pick_monitor(win_w, win_h, which=cfg.display.monitor)

        from virtual_reality.display.window import setup_pygame_window
        self._screen = setup_pygame_window(
            win_w, win_h,
            monitor_x=mon.x, monitor_y=mon.y,
            borderless=cfg.display.borderless,
            opengl=False,
        )
        pygame.display.set_caption("Virtual Reality - 2D Fly")

        # Pre-allocate camera-space canvas
        self._canvas = np.zeros(
            (self._cam_h, self._cam_w, 3), dtype=np.uint8,
        )

        # Pixel mapping: world mm to camera-space pixels
        self._px_per_mm = self._cam_w / (2.0 * cfg.arena.radius_mm)
        self._cx = self._cam_w // 2
        self._cy = self._cam_h // 2

        # Camera position (observer viewpoint)
        self._cam_x = cfg.camera.x_mm
        self._cam_y = cfg.camera.y_mm
        self._cam_heading = 0.0

        # State
        mov = cfg.movement
        self._fly_x = mov.start_x
        self._fly_y = mov.start_y
        self._fly_heading = mov.start_heading_deg

        # Controller
        if cfg.autonomous.enabled:
            from virtual_reality.stimulus.autonomous import (
                AutonomousFlyController,
            )
            ac = cfg.autonomous
            self._controller = AutonomousFlyController(
                arena_radius=cfg.arena.radius_mm,
                speed=mov.speed_mm_s,
                run_duration=ac.mean_run_dur,
                pause_duration=ac.mean_pause_dur,
                turn_rate=mov.turn_deg_s,
                edge_margin=(
                    cfg.arena.radius_mm * (1.0 - ac.edge_thresh_frac)
                ),
            )
            self._controller.x = self._fly_x
            self._controller.y = self._fly_y
            self._controller.heading_deg = self._fly_heading
        else:
            from virtual_reality.stimulus.keyboard_control import (
                KeyboardFlyController,
            )
            self._controller = KeyboardFlyController(
                arena_radius=cfg.arena.radius_mm,
                speed=mov.speed_mm_s,
                turn_rate=mov.turn_deg_s,
            )
            self._controller.x = self._fly_x
            self._controller.y = self._fly_y
            self._controller.heading_deg = self._fly_heading

        # Trail
        self._trail: deque = deque()
        self._trail_max_secs = cfg.minimap.trail_secs

        logger.info(
            "FlySpriteStimulus ready: %d frames, cam=%dx%d warp=%s",
            self._n_frames, self._cam_w, self._cam_h,
            self._warp_enabled,
        )

    def update(self, dt: float, events: list) -> None:
        """Handle input and advance fly position."""
        import pygame

        cfg = self.config

        # Events
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_u:
                    self._use_warp = not self._use_warp

        # Controller
        if cfg.autonomous.enabled:
            self._controller.update(dt)
        else:
            keys = pygame.key.get_pressed()
            self._controller.forward = keys[pygame.K_w]
            self._controller.backward = keys[pygame.K_s]
            self._controller.turn_left = keys[pygame.K_a]
            self._controller.turn_right = keys[pygame.K_d]
            self._controller.update(dt)

        self._fly_x = self._controller.x
        self._fly_y = self._controller.y
        self._fly_heading = self._controller.heading_deg

        # Trail
        now = time.time()
        self._trail.append((now, self._fly_x, self._fly_y))
        cutoff = now - self._trail_max_secs
        while self._trail and self._trail[0][0] < cutoff:
            self._trail.popleft()

    def render(self) -> None:
        """Draw the sprite and optionally warp to projector space."""
        import pygame

        cfg = self.config

        # Clear canvas
        bg = cfg.display.bg_color
        self._canvas[:] = bg[:3]

        # Select sprite frame from heading
        idx = _angle_to_index(self._fly_heading, self._n_frames)

        # Distance-based scaling
        dist_mm = max(1.0, abs(self._fly_y) + 1.0)
        height_px = self._ref_height_px * (self._ref_dist_mm / dist_mm)
        scale = height_px / max(1.0, self._ref_sprite_h)
        scale = max(0.1, min(scale, 10.0))

        # Screen position
        px = int(round(self._cx + self._fly_x * self._px_per_mm))
        py = self._cy

        # Draw sprite
        _render_sprite_masked(
            self._canvas,
            self._sprites[idx],
            self._masks[idx],
            px, py, scale,
        )

        # Warp if enabled
        if self._warp_enabled and self._use_warp:
            import cv2
            proj_frame = cv2.remap(
                self._canvas, self._mapx, self._mapy,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0),
            )
        else:
            proj_frame = self._canvas

        # Convert to pygame surface
        from virtual_reality.display.surface import bgr_to_surface
        surf = bgr_to_surface(proj_frame)
        target_w, target_h = self._screen.get_size()
        if (
            surf.get_width() != target_w
            or surf.get_height() != target_h
        ):
            surf = pygame.transform.scale(surf, (target_w, target_h))
        self._screen.blit(surf, (0, 0))

    def teardown(self) -> None:
        """Clean up pygame."""
        import pygame

        logger.info("FlySpriteStimulus.teardown()")
        pygame.quit()

    def get_state(self) -> dict:
        """Return the current stimulus state for data recording."""
        return {
            "fly_x": self._fly_x,
            "fly_y": self._fly_y,
            "fly_heading_deg": self._fly_heading,
            "controller": (
                "autonomous" if self.config.autonomous.enabled
                else "keyboard"
            ),
        }


def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the 2D sprite stimulus CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the 2D sprite fly stimulus.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to a YAML configuration file.",
    )
    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=None,
        help="Override target FPS.",
    )
    parser.add_argument(
        "--no-warp",
        action="store_true",
        default=False,
        help="Disable projector warp map even if configured.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--windowed",
        action="store_true",
        default=False,
        help="Run in a windowed (bordered) mode.",
    )
    group.add_argument(
        "--fullscreen",
        action="store_true",
        default=False,
        help="Run in borderless fullscreen mode.",
    )
    parser.add_argument(
        "--monitor", "-m",
        type=str,
        default=None,
        help="Monitor selection: 'left' or 'right'.",
    )
    return parser


def main() -> None:
    """CLI entry point for the 2D fly stimulus."""
    import argparse

    from virtual_reality.config.loader import load_config
    from virtual_reality.config.schema import _resolve_default_paths
    from virtual_reality.logging_config import setup_logging

    setup_logging()

    parser = _build_parser()
    args = parser.parse_args()

    if args.config is not None:
        config = load_config(args.config)
    else:
        config = _resolve_default_paths()

    # Apply CLI overrides
    if args.fps is not None:
        config.display.target_fps = args.fps
    if args.no_warp:
        config.warp.mapx_path = ""
        config.warp.mapy_path = ""
    if args.windowed:
        config.display.borderless = False
    elif args.fullscreen:
        config.display.borderless = True
    if args.monitor is not None:
        config.display.monitor = args.monitor

    stimulus = FlySpriteStimulus(config=config)

    from virtual_reality.session.session import Session
    session = Session(
        config=config,
        stimulus_type="FlySpriteStimulus",
    )

    stimulus.run(
        target_fps=config.display.target_fps,
        session=session,
    )


if __name__ == "__main__":
    main()
