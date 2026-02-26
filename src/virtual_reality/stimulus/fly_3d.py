"""3D GLB fly stimulus.

Renders a 3D fly model in a circular arena using OpenGL, with
projector warp correction, multiple projection modes, and Phong
lighting.  This is the main stimulus module that replaces
``3d_object_fly4.py``.
"""

from __future__ import annotations

import ctypes
import logging
import math
import time
from collections import deque
from pathlib import Path

import numpy as np

from virtual_reality.config.schema import VirtualRealityConfig
from virtual_reality.math_utils.arena import (
    clamp_scale_for_near_plane,
    clamp_to_arena,
    compute_camera_fly_distance_mm,
    compute_min_cam_fly_dist_3d,
    enforce_min_distance_3d,
)
from virtual_reality.math_utils.geometry import compute_light_dirs
from virtual_reality.math_utils.transforms import (
    look_at,
    mat4_rotate_x,
    mat4_rotate_y,
    mat4_scale,
    mat4_translate,
    perspective,
)
from virtual_reality.rendering.projections import (
    PROJ_PERSPECTIVE,
    projection_mode_to_int,
)
from virtual_reality.rendering.shaders import (
    FLY_FRAG_SRC,
    FLY_VERT_SRC,
    WARP_FRAG_SRC,
    WARP_VERT_SRC,
)
from virtual_reality.stimulus.base import Stimulus

logger = logging.getLogger(__name__)


class Fly3DStimulus(Stimulus):
    """3D fly model stimulus with projector warp correction.

    Composes rendering, warp mapping, minimap, and movement
    controllers into a single runnable stimulus.

    The rendering pipeline uses two passes:

    1. **Offscreen pass**: Render the 3D fly model to an FBO at
       camera resolution, using Phong lighting and configurable
       projection (perspective / equidistant / equirectangular).
    2. **Warp pass**: Draw a fullscreen quad that samples the
       offscreen texture through the projector-camera warp map.

    Args:
        config: Full configuration dataclass.
    """

    def __init__(self, config: VirtualRealityConfig | None = None) -> None:
        if config is None:
            config = VirtualRealityConfig()
        self.config = config
        self._running = False
        self._comms = None
        self._use_fictrac = False

    # ------------------------------------------------------------------ setup

    def setup(self) -> None:
        """Initialise pygame, OpenGL context, load model and warp maps."""
        import pygame
        from OpenGL import GL

        from virtual_reality.display.monitor import pick_monitor
        from virtual_reality.display.window import setup_pygame_window
        from virtual_reality.mapping.warp import (
            load_warp_map,
            warp_to_gl_texture,
        )
        from virtual_reality.rendering.gl_utils import (
            create_offscreen_fbo,
            create_program,
            create_texture_2d,
            create_texture_from_image,
        )
        from virtual_reality.rendering.glb_loader import load_glb

        cfg = self.config
        logger.info("Fly3DStimulus.setup() - initialising")

        # -- Load warp map (optional) --
        _have_warp = bool(cfg.warp.mapx_path and cfg.warp.mapy_path)
        if _have_warp:
            try:
                warp = load_warp_map(
                    cfg.warp.mapx_path, cfg.warp.mapy_path,
                )
                warp_uv = warp_to_gl_texture(warp)
                self._cam_w = warp.cam_w
                self._cam_h = warp.cam_h
                self._proj_w = warp.proj_w
                self._proj_h = warp.proj_h
            except Exception as exc:
                logger.warning("Could not load warp maps: %s", exc)
                _have_warp = False

        if not _have_warp:
            logger.info(
                "No warp maps configured — running without warp",
            )
            self._cam_w = cfg.calibration.proj_w
            self._cam_h = cfg.calibration.proj_h
            self._proj_w = cfg.calibration.proj_w
            self._proj_h = cfg.calibration.proj_h
            # Identity warp: each pixel maps to itself (normalised UVs)
            warp_uv = np.zeros(
                (self._proj_h, self._proj_w, 2), dtype=np.float32,
            )
            warp_uv[:, :, 0] = np.linspace(
                0, 1, self._proj_w, dtype=np.float32,
            )[np.newaxis, :]
            warp_uv[:, :, 1] = np.linspace(
                0, 1, self._proj_h, dtype=np.float32,
            )[:, np.newaxis]

        # -- Pygame window on projector monitor --
        pygame.init()
        mon = pick_monitor(
            self._proj_w, self._proj_h, which=cfg.display.monitor,
        )

        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_MAJOR_VERSION, 3,
        )
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_MINOR_VERSION, 3,
        )
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK,
            pygame.GL_CONTEXT_PROFILE_CORE,
        )
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1,
        )
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)

        setup_pygame_window(
            self._proj_w, self._proj_h,
            monitor_x=mon.x, monitor_y=mon.y,
            borderless=cfg.display.borderless,
            opengl=True,
        )
        pygame.display.set_caption("Virtual Reality - 3D Fly")

        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glViewport(0, 0, self._proj_w, self._proj_h)
        GL.glDisable(GL.GL_DEPTH_TEST)

        # -- Warp quad program --
        self._warp_prog = create_program(WARP_VERT_SRC, WARP_FRAG_SRC)
        GL.glUseProgram(self._warp_prog)

        quad_verts = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
            -1.0,  1.0, 0.0, 1.0,
             1.0,  1.0, 1.0, 1.0,
        ], dtype=np.float32)

        self._warp_vao = GL.glGenVertexArrays(1)
        self._warp_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._warp_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._warp_vbo)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER, quad_verts.nbytes,
            quad_verts, GL.GL_STATIC_DRAW,
        )
        stride = 4 * quad_verts.itemsize

        loc_pos = GL.glGetAttribLocation(self._warp_prog, "in_pos")
        GL.glEnableVertexAttribArray(loc_pos)
        GL.glVertexAttribPointer(
            loc_pos, 2, GL.GL_FLOAT, GL.GL_FALSE,
            stride, ctypes.c_void_p(0),
        )
        loc_uv = GL.glGetAttribLocation(self._warp_prog, "in_uv")
        GL.glEnableVertexAttribArray(loc_uv)
        GL.glVertexAttribPointer(
            loc_uv, 2, GL.GL_FLOAT, GL.GL_FALSE,
            stride, ctypes.c_void_p(2 * quad_verts.itemsize),
        )
        GL.glBindVertexArray(0)

        # Warp texture (RG32F)
        self._warp_tex = create_texture_2d(
            self._proj_w, self._proj_h,
            GL.GL_RG32F, GL.GL_RG, GL.GL_FLOAT,
        )
        self._u_cam = GL.glGetUniformLocation(self._warp_prog, "u_cam")
        self._u_warp = GL.glGetUniformLocation(
            self._warp_prog, "u_warp",
        )
        self._u_useWarp = GL.glGetUniformLocation(
            self._warp_prog, "u_useWarp",
        )
        GL.glUniform1i(self._u_cam, 0)
        GL.glUniform1i(self._u_warp, 1)

        # Upload warp UV data
        warp_c = np.ascontiguousarray(warp_uv.astype(np.float32))
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._warp_tex)
        GL.glTexSubImage2D(
            GL.GL_TEXTURE_2D, 0, 0, 0,
            self._proj_w, self._proj_h,
            GL.GL_RG, GL.GL_FLOAT,
            warp_c.ctypes.data_as(ctypes.c_void_p),
        )

        # -- Offscreen FBO for fly camera --
        self._fly_fbo, self._cam_tex, self._depth_rb = (
            create_offscreen_fbo(self._cam_w, self._cam_h)
        )

        # -- 3D fly shader program --
        self._fly_prog = create_program(FLY_VERT_SRC, FLY_FRAG_SRC)
        GL.glUseProgram(self._fly_prog)

        self._u_mvp = GL.glGetUniformLocation(self._fly_prog, "u_mvp")
        self._u_model = GL.glGetUniformLocation(
            self._fly_prog, "u_model",
        )
        self._u_view = GL.glGetUniformLocation(
            self._fly_prog, "u_view",
        )
        self._u_far = GL.glGetUniformLocation(self._fly_prog, "u_far")
        self._u_fovY = GL.glGetUniformLocation(
            self._fly_prog, "u_fovY",
        )
        self._u_fovX = GL.glGetUniformLocation(
            self._fly_prog, "u_fovX",
        )
        self._u_projMode = GL.glGetUniformLocation(
            self._fly_prog, "u_projMode",
        )
        self._u_baseColor = GL.glGetUniformLocation(
            self._fly_prog, "u_baseColor",
        )
        self._u_hasTexture = GL.glGetUniformLocation(
            self._fly_prog, "u_hasTexture",
        )
        self._u_tex = GL.glGetUniformLocation(
            self._fly_prog, "u_baseColorTex",
        )
        self._u_ambient = GL.glGetUniformLocation(
            self._fly_prog, "u_ambient",
        )
        self._u_lightInt = GL.glGetUniformLocation(
            self._fly_prog, "u_lightIntensities",
        )
        self._u_lightDirs = GL.glGetUniformLocation(
            self._fly_prog, "u_lightDirs",
        )
        self._u_lightMax = GL.glGetUniformLocation(
            self._fly_prog, "u_lightMaxGain",
        )
        GL.glUniform1i(self._u_tex, 0)

        # -- Load GLB model --
        mesh = load_glb(cfg.fly_model.model_path)
        self._mesh = mesh

        # Flip Y for ultrawide projection
        cam_cfg = cfg.camera
        proj_mode = projection_mode_to_int(cam_cfg.projection)
        if cam_cfg.fov_x_deg > 180.0 and proj_mode != PROJ_PERSPECTIVE:
            mesh.vertices[:, 1] *= -1.0
            mesh.vertices[:, 4] *= -1.0

        # Upload textures per draw call
        self._draw_textures: list[int | None] = []
        for dc in mesh.draw_calls:
            tex = None
            if dc.base_color_image is not None:
                tex = create_texture_from_image(dc.base_color_image)
            self._draw_textures.append(tex)

        # Compute physical scaling
        pos = mesh.vertices[:, 0:3]
        extents = pos.max(axis=0) - pos.min(axis=0)
        longest = float(extents.max()) if extents.max() > 0 else 1.0
        self._fly_base_scale = (
            cfg.fly_model.base_scale
            * cfg.fly_model.phys_length_mm / longest
        )
        self._fly_bounding_radius = mesh.bounding_radius

        # -- Fly mesh VAO/VBO/EBO --
        self._fly_vao = GL.glGenVertexArrays(1)
        self._fly_vbo = GL.glGenBuffers(1)
        self._fly_ebo = GL.glGenBuffers(1)

        GL.glBindVertexArray(self._fly_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._fly_vbo)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER, mesh.vertices.nbytes,
            mesh.vertices, GL.GL_STATIC_DRAW,
        )
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._fly_ebo)
        GL.glBufferData(
            GL.GL_ELEMENT_ARRAY_BUFFER, mesh.indices.nbytes,
            mesh.indices, GL.GL_STATIC_DRAW,
        )

        stride_f = 12 * 4  # 12 floats * 4 bytes
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(
            0, 3, GL.GL_FLOAT, GL.GL_FALSE,
            stride_f, ctypes.c_void_p(0),
        )
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(
            1, 3, GL.GL_FLOAT, GL.GL_FALSE,
            stride_f, ctypes.c_void_p(3 * 4),
        )
        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(
            2, 4, GL.GL_FLOAT, GL.GL_FALSE,
            stride_f, ctypes.c_void_p(6 * 4),
        )
        GL.glEnableVertexAttribArray(3)
        GL.glVertexAttribPointer(
            3, 2, GL.GL_FLOAT, GL.GL_FALSE,
            stride_f, ctypes.c_void_p(10 * 4),
        )
        GL.glBindVertexArray(0)

        # -- Set static lighting uniforms --
        light_dirs = compute_light_dirs(cfg.lighting.elevation_deg)
        light_int = np.array(
            cfg.lighting.intensities[:4], dtype=np.float32,
        )
        if light_int.shape[0] < 4:
            light_int = np.resize(light_int, 4)

        GL.glUseProgram(self._fly_prog)
        GL.glUniform1f(self._u_ambient, cfg.lighting.ambient)
        GL.glUniform4fv(self._u_lightInt, 1, light_int)
        GL.glUniform3fv(self._u_lightDirs, 4, light_dirs.astype(np.float32))
        GL.glUniform1f(self._u_lightMax, cfg.lighting.max_gain)

        # -- Camera/projection config --
        aspect = self._cam_w / float(self._cam_h)
        self._proj_mode = proj_mode
        fov_x_rad = math.radians(cam_cfg.fov_x_deg)

        if cam_cfg.projection == "equirect":
            fov_y_rad = fov_x_rad * (self._cam_h / self._cam_w)
        else:
            fov_y_rad = 2.0 * math.atan(
                math.tan(0.5 * fov_x_rad) / max(aspect, 1e-6),
            )

        max_fov_y = math.radians(179.0)
        max_fov_x = math.radians(359.0)
        if cam_cfg.allow_ultrawide:
            self._fov_y_rad = min(fov_y_rad, max_fov_y)
            self._fov_x_rad = min(fov_x_rad, max_fov_x)
        else:
            self._fov_y_rad = min(fov_y_rad, math.radians(120.0))
            self._fov_x_rad = min(fov_x_rad, math.radians(160.0))

        self._z_near = 1.0
        self._z_far = 10.0 * cfg.arena.radius_mm

        # Derive minimum 3D camera-fly distance from near plane.
        if cfg.scaling.auto_min_distance:
            self._min_dist_3d = compute_min_cam_fly_dist_3d(
                z_near=self._z_near,
                fly_bounding_radius=self._fly_bounding_radius,
                fly_base_scale=self._fly_base_scale,
                screen_distance_mm=cfg.scaling.screen_distance_mm,
                safety_margin=cfg.scaling.near_plane_safety,
            )
            logger.info(
                "Derived min 3D cam-fly distance: %.2f mm "
                "(near=%.1f, bound_r=%.3f, base_scale=%.4f)",
                self._min_dist_3d, self._z_near,
                self._fly_bounding_radius, self._fly_base_scale,
            )
        else:
            self._min_dist_3d = cfg.scaling.min_cam_fly_dist_mm

        if self._proj_mode == PROJ_PERSPECTIVE:
            self._proj_mat = perspective(
                self._fov_y_rad, aspect,
                z_near=self._z_near, z_far=self._z_far,
            )
        else:
            self._proj_mat = np.eye(4, dtype=np.float32)

        self._flip_model = (
            cam_cfg.flip_model_for_ultrawide
            and self._proj_mode != PROJ_PERSPECTIVE
            and cam_cfg.fov_x_deg > 180.0
        )

        # -- State variables --
        mov = cfg.movement
        self._fly_x = mov.start_x
        self._fly_y = mov.start_y
        self._fly_heading = math.radians(mov.start_heading_deg)
        self._cam_x = cam_cfg.x_mm
        self._cam_y = cam_cfg.y_mm
        self._cam_height = cam_cfg.height_mm
        self._cam_heading = math.radians(mov.start_heading_deg)
        self._yaw_offset_deg = cfg.fly_model.yaw_offset_deg
        self._use_warp = True

        # Scaling state
        dist = compute_camera_fly_distance_mm(
            (self._fly_x, self._fly_y),
            (self._cam_x, self._cam_y),
            self._cam_height,
        )
        self._fly_scale_target = self._fly_base_scale * (
            cfg.scaling.screen_distance_mm / max(dist, 1e-6)
        )
        self._fly_scale_current = self._fly_scale_target

        # Trail for minimap
        self._trail: deque = deque()
        self._trail_max_secs = cfg.minimap.trail_secs

        # Controller — FicTrac (closed-loop), autonomous, or keyboard
        self._comms = None
        self._use_fictrac = False

        if cfg.comms.enabled:
            try:
                from virtual_reality.comms.hub import CommsHub
                from virtual_reality.comms.fictrac_controller import (
                    FicTracController,
                )
                self._comms = CommsHub(cfg.comms)
                self._comms.start_all()
                self._controller = FicTracController(
                    hub=self._comms,
                    ball_radius_mm=cfg.comms.fictrac_ball_radius_mm,
                    arena_radius=cfg.arena.radius_mm,
                )
                self._use_fictrac = True
                logger.info("Using FicTrac controller (closed-loop)")
            except Exception as exc:
                logger.warning(
                    "Comms init failed, falling back: %s", exc,
                )
                self._comms = None

        if not self._use_fictrac and cfg.autonomous.enabled:
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
        elif not self._use_fictrac:
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

        # Minimap
        self._minimap_enabled = cfg.minimap.enabled
        self._next_minimap_t = 0.0

        if self._minimap_enabled:
            self._setup_minimap(cfg)

        self._running = True
        logger.info(
            "Fly3DStimulus ready: cam=%dx%d proj=%dx%d mode=%s",
            self._cam_w, self._cam_h,
            self._proj_w, self._proj_h,
            cam_cfg.projection,
        )

    def _setup_minimap(self, cfg: VirtualRealityConfig) -> None:
        """Initialise the minimap renderer."""
        import cv2

        from virtual_reality.display.minimap import build_minimap_base

        mc = cfg.minimap
        self._map_w = mc.width
        self._map_h = mc.height
        self._map_pad = mc.pad

        R = cfg.arena.radius_mm
        half_h = (mc.height - 2 * mc.pad) / 2.0
        half_w = (mc.width - 2 * mc.pad) / 2.0
        self._map_scale = min(half_h / R, half_w / R)
        self._map_cu = mc.width // 2
        self._map_cv = mc.pad + int(round(R * self._map_scale))

        cv2.namedWindow("minimap", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("minimap", mc.width, mc.height)

        self._minimap_base = build_minimap_base(
            R, mc.width, mc.height,
            self._map_cu, self._map_cv, self._map_scale,
        )

    # --------------------------------------------------------------- update

    def update(self, dt: float, events: list) -> None:
        """Update fly position, camera, and controllers."""
        import pygame

        cfg = self.config

        # Handle events
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_u:
                    self._use_warp = not self._use_warp
                    logger.info("Warp: %s", self._use_warp)

        # Update controller
        if self._use_fictrac:
            self._controller.update(dt)
            self._fly_x = self._controller.x
            self._fly_y = self._controller.y
            self._fly_heading = self._controller.heading_rad
        elif cfg.autonomous.enabled:
            self._controller.update(dt)
            self._fly_x = self._controller.x
            self._fly_y = self._controller.y
            self._fly_heading = self._controller.heading_rad
        else:
            keys = pygame.key.get_pressed()
            self._controller.forward = keys[pygame.K_w]
            self._controller.backward = keys[pygame.K_s]
            self._controller.turn_left = keys[pygame.K_a]
            self._controller.turn_right = keys[pygame.K_d]
            self._controller.update(dt)
            self._fly_x = self._controller.x
            self._fly_y = self._controller.y
            self._fly_heading = self._controller.heading_rad

        # Camera movement (arrow keys)
        keys = pygame.key.get_pressed()
        cam_turn = math.radians(cfg.camera.turn_deg_s) * dt
        if keys[pygame.K_LEFT]:
            self._cam_heading -= cam_turn
        if keys[pygame.K_RIGHT]:
            self._cam_heading += cam_turn

        cam_speed = cfg.camera.speed_mm_s * dt
        if keys[pygame.K_UP]:
            self._cam_x += cam_speed * math.sin(self._cam_heading)
            self._cam_y += cam_speed * math.cos(self._cam_heading)
        if keys[pygame.K_DOWN]:
            self._cam_x -= cam_speed * math.sin(self._cam_heading)
            self._cam_y -= cam_speed * math.cos(self._cam_heading)

        # Clamp camera to arena
        self._cam_x, self._cam_y = clamp_to_arena(
            self._cam_x, self._cam_y, cfg.arena.radius_mm,
        )

        # Enforce minimum 3D distance (accounts for camera height)
        self._fly_x, self._fly_y = enforce_min_distance_3d(
            (self._fly_x, self._fly_y),
            (self._cam_x, self._cam_y),
            self._cam_height,
            self._min_dist_3d,
        )
        self._fly_x, self._fly_y = clamp_to_arena(
            self._fly_x, self._fly_y, cfg.arena.radius_mm,
        )

        # Smooth scaling with near-plane clamping
        dist = compute_camera_fly_distance_mm(
            (self._fly_x, self._fly_y),
            (self._cam_x, self._cam_y),
            self._cam_height,
        )
        self._fly_scale_target = self._fly_base_scale * (
            cfg.scaling.screen_distance_mm / max(dist, 1e-6)
        )
        self._fly_scale_target = clamp_scale_for_near_plane(
            self._fly_scale_target,
            self._fly_bounding_radius,
            dist,
            self._z_near,
        )
        if cfg.scaling.dist_scale_smooth_hz > 0:
            alpha = 1.0 - math.exp(
                -cfg.scaling.dist_scale_smooth_hz * dt,
            )
        else:
            alpha = 1.0
        self._fly_scale_current += alpha * (
            self._fly_scale_target - self._fly_scale_current
        )

        # Trail
        now = time.time()
        self._trail.append((now, self._fly_x, self._fly_y))
        cutoff = now - self._trail_max_secs
        while self._trail and self._trail[0][0] < cutoff:
            self._trail.popleft()

    # --------------------------------------------------------------- render

    def render(self) -> None:
        """Render the 3D fly and apply warp correction."""
        from OpenGL import GL

        cfg = self.config

        # -- Pass 1: Render fly to offscreen FBO --
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fly_fbo)
        GL.glViewport(0, 0, self._cam_w, self._cam_h)
        GL.glEnable(GL.GL_DEPTH_TEST)

        bg = cfg.display.bg_color
        GL.glClearColor(bg[0] / 255.0, bg[1] / 255.0, bg[2] / 255.0, 1.0)
        GL.glClear(
            GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT,
        )

        # View matrix
        eye = [self._cam_x, self._cam_height, self._cam_y]
        fwd = [
            math.sin(self._cam_heading),
            0.0,
            math.cos(self._cam_heading),
        ]
        target = [eye[0] + fwd[0], eye[1] + fwd[1], eye[2] + fwd[2]]
        view_mat = look_at(
            np.array(eye), np.array(target), np.array([0, 1, 0]),
        )

        # Model matrix
        yaw = -self._fly_heading + math.radians(self._yaw_offset_deg)
        base_rot = mat4_rotate_y(yaw)
        if self._flip_model:
            base_rot = mat4_rotate_x(math.pi) @ base_rot
        model_mat = (
            mat4_translate(self._fly_x, 0.0, self._fly_y)
            @ base_rot
            @ mat4_scale(self._fly_scale_current)
        )
        mvp = self._proj_mat @ view_mat @ model_mat

        GL.glUseProgram(self._fly_prog)
        GL.glBindVertexArray(self._fly_vao)
        GL.glUniformMatrix4fv(
            self._u_view, 1, GL.GL_FALSE,
            view_mat.T.astype(np.float32),
        )
        GL.glUniformMatrix4fv(
            self._u_mvp, 1, GL.GL_FALSE,
            mvp.T.astype(np.float32),
        )
        GL.glUniformMatrix4fv(
            self._u_model, 1, GL.GL_FALSE,
            model_mat.T.astype(np.float32),
        )
        GL.glUniform1f(self._u_far, self._z_far)
        GL.glUniform1f(self._u_fovY, self._fov_y_rad)
        GL.glUniform1f(self._u_fovX, self._fov_x_rad)
        GL.glUniform1i(self._u_projMode, self._proj_mode)

        # Draw each mesh primitive
        idx_stride = ctypes.sizeof(ctypes.c_uint32)
        for dc, tex in zip(
            self._mesh.draw_calls, self._draw_textures,
        ):
            GL.glUniform4fv(
                self._u_baseColor, 1,
                dc.base_color_factor.astype(np.float32),
            )
            GL.glUniform1i(
                self._u_hasTexture, 1 if tex is not None else 0,
            )
            if tex is not None:
                GL.glActiveTexture(GL.GL_TEXTURE0)
                GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
            GL.glDrawElements(
                GL.GL_TRIANGLES, dc.count, GL.GL_UNSIGNED_INT,
                ctypes.c_void_p(dc.base_index * idx_stride),
            )

        GL.glBindVertexArray(0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glDisable(GL.GL_DEPTH_TEST)

        # -- Pass 2: Warp to screen --
        GL.glViewport(0, 0, self._proj_w, self._proj_h)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        GL.glUseProgram(self._warp_prog)
        GL.glUniform1i(
            self._u_useWarp, 1 if self._use_warp else 0,
        )
        GL.glBindVertexArray(self._warp_vao)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._cam_tex)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._warp_tex)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        GL.glBindVertexArray(0)

        # -- Minimap --
        if self._minimap_enabled:
            self._render_minimap()

    def _render_minimap(self) -> None:
        """Draw the minimap overlay if it's time."""
        import cv2

        from virtual_reality.display.minimap import (
            draw_minimap_dynamic,
            world_to_minimap,
        )

        now = time.time()
        if now < self._next_minimap_t:
            return
        self._next_minimap_t = now + 1.0 / self.config.minimap.hz

        trail_uv = [
            world_to_minimap(
                tx, ty, self._map_cu, self._map_cv, self._map_scale,
            )
            for _, tx, ty in self._trail
        ]

        import pygame
        fps = pygame.time.Clock().get_fps()

        map_img = draw_minimap_dynamic(
            self._minimap_base,
            self._fly_x, self._fly_y, self._fly_heading,
            trail_uv,
            self.config.minimap.trail_color,
            self.config.minimap.trail_thick,
            self._map_cu, self._map_cv, self._map_scale,
            fps,
            self._cam_x, self._cam_y, self._cam_heading,
            self.config.camera.fov_x_deg,
            self.config.arena.radius_mm,
        )

        cv2.imshow("minimap", map_img)
        cv2.waitKey(1)

    # ------------------------------------------------------------ teardown

    def teardown(self) -> None:
        """Release GPU resources and stop comms."""
        from OpenGL import GL

        logger.info("Fly3DStimulus.teardown()")

        if self._comms is not None:
            self._comms.stop_all()
            self._comms = None

        tex_list = [self._warp_tex, self._cam_tex]
        for tex in self._draw_textures:
            if tex is not None:
                tex_list.append(tex)
        GL.glDeleteTextures(tex_list)

        GL.glDeleteRenderbuffers(1, [self._depth_rb])
        GL.glDeleteFramebuffers(1, [self._fly_fbo])
        GL.glDeleteBuffers(
            3, [self._warp_vbo, self._fly_vbo, self._fly_ebo],
        )
        GL.glDeleteVertexArrays(2, [self._warp_vao, self._fly_vao])
        GL.glDeleteProgram(self._warp_prog)
        GL.glDeleteProgram(self._fly_prog)

        import pygame
        pygame.quit()

        if self._minimap_enabled:
            import cv2
            cv2.destroyAllWindows()

        self._running = False

    # ------------------------------------------------------------ state

    def get_state(self) -> dict:
        """Return the current stimulus state for data recording.

        Returns:
            Dict with fly position, heading, camera position,
            scale, and controller info.
        """
        return {
            "fly_x": self._fly_x,
            "fly_y": self._fly_y,
            "fly_heading_deg": math.degrees(self._fly_heading),
            "cam_x": self._cam_x,
            "cam_y": self._cam_y,
            "cam_height": self._cam_height,
            "cam_heading_deg": math.degrees(self._cam_heading),
            "fly_scale": self._fly_scale_current,
            "use_warp": self._use_warp,
            "controller": (
                "fictrac" if self._use_fictrac
                else "autonomous" if self.config.autonomous.enabled
                else "keyboard"
            ),
        }


def _build_parser() -> "argparse.ArgumentParser":
    """Build the argument parser for the 3D fly stimulus CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the 3D GLB fly stimulus with projector warp.",
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
    """CLI entry point for the 3D fly stimulus."""
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

    stimulus = Fly3DStimulus(config=config)

    # Create session for experiment tracking
    from virtual_reality.session.session import Session
    session = Session(
        config=config,
        comms=stimulus._comms,
        stimulus_type="Fly3DStimulus",
    )

    stimulus.run(
        target_fps=config.display.target_fps,
        session=session,
    )


if __name__ == "__main__":
    main()
