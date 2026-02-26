"""Arena geometry utilities for circular boundary enforcement.

Functions for clamping positions to a circular arena, enforcing
minimum distances between entities, and computing 3D separations.
"""

from __future__ import annotations

import math


def clamp_to_arena(
    x: float,
    y: float,
    radius: float,
) -> tuple[float, float]:
    """Clamp a 2D position to stay inside a circular arena.

    If the point lies outside the arena, it is projected back onto
    the boundary circle.

    Args:
        x: X coordinate.
        y: Y coordinate.
        radius: Arena radius in the same units as *x* and *y*.

    Returns:
        The clamped ``(x, y)`` position.
    """
    dist = math.hypot(x, y)
    if dist > radius:
        scale = radius / max(dist, 1e-9)
        return x * scale, y * scale
    return x, y


def enforce_min_distance(
    pos: tuple[float, float],
    other: tuple[float, float],
    min_dist: float,
) -> tuple[float, float]:
    """Push *pos* away from *other* so they are at least *min_dist* apart.

    If the two positions overlap exactly, *pos* is pushed along +X.

    Args:
        pos: The position to adjust as ``(x, y)``.
        other: The reference position as ``(x, y)``.
        min_dist: Minimum allowed distance.

    Returns:
        The adjusted ``(x, y)`` for *pos*.
    """
    px, py = pos
    ox, oy = other
    dx = px - ox
    dy = py - oy
    dist = math.hypot(dx, dy)
    if dist < min_dist:
        if dist < 1e-6:
            px = ox + min_dist
            py = oy
        else:
            scale = min_dist / dist
            px = ox + dx * scale
            py = oy + dy * scale
    return px, py


def compute_camera_fly_distance_mm(
    fly_pos: tuple[float, float],
    cam_pos: tuple[float, float],
    cam_height_mm: float,
) -> float:
    """Compute the 3D distance between camera and fly.

    The fly is assumed to be on the arena plane (height = 0).

    Args:
        fly_pos: Fly position as ``(x, y)`` in mm.
        cam_pos: Camera position as ``(x, y)`` in mm.
        cam_height_mm: Camera height above the arena plane in mm.

    Returns:
        The 3D Euclidean distance in mm.
    """
    fx, fy = fly_pos
    cx, cy = cam_pos
    dx = fx - cx
    dy = fy - cy
    return math.sqrt(dx * dx + dy * dy + cam_height_mm * cam_height_mm)


def compute_min_cam_fly_dist_3d(
    z_near: float,
    fly_bounding_radius: float,
    fly_base_scale: float,
    screen_distance_mm: float,
    safety_margin: float = 1.2,
) -> float:
    """Derive the minimum 3D camera-fly distance to avoid near-plane clipping.

    Solves for *d* in::

        d - fly_bounding_radius * fly_base_scale * (screen_distance_mm / d) = z_near

    Rearranging: ``d² - z_near·d - K = 0`` where
    ``K = fly_bounding_radius * fly_base_scale * screen_distance_mm``.

    Args:
        z_near: Near clipping plane distance in mm.
        fly_bounding_radius: Bounding sphere radius of the raw mesh.
        fly_base_scale: Scale mapping raw mesh to physical mm.
        screen_distance_mm: Screen distance for apparent-size scaling.
        safety_margin: Multiplier on the result for robustness.

    Returns:
        Minimum 3D distance in mm.
    """
    k = fly_bounding_radius * fly_base_scale * screen_distance_mm
    discriminant = z_near * z_near + 4.0 * k
    d_min = (z_near + math.sqrt(discriminant)) / 2.0
    return d_min * safety_margin


def enforce_min_distance_3d(
    fly_pos: tuple[float, float],
    cam_pos: tuple[float, float],
    cam_height_mm: float,
    min_dist_3d: float,
) -> tuple[float, float]:
    """Push fly away from camera to maintain a minimum 3D distance.

    The camera is at ``(cam_x, cam_height, cam_y)`` and the fly is on
    the arena plane at height 0.  If the 3D distance is below
    *min_dist_3d*, the fly's XY position is pushed outward along the
    camera-to-fly direction.

    Args:
        fly_pos: Fly XY position as ``(x, y)``.
        cam_pos: Camera XY position as ``(x, y)``.
        cam_height_mm: Camera height above arena plane.
        min_dist_3d: Minimum allowed 3D distance.

    Returns:
        Adjusted ``(x, y)`` for the fly.
    """
    fx, fy = fly_pos
    cx, cy = cam_pos
    dx = fx - cx
    dy = fy - cy
    xy_dist_sq = dx * dx + dy * dy
    dist_3d_sq = xy_dist_sq + cam_height_mm * cam_height_mm

    if dist_3d_sq >= min_dist_3d * min_dist_3d:
        return fly_pos

    # Required XY distance to achieve min_dist_3d given camera height.
    min_xy_sq = min_dist_3d * min_dist_3d - cam_height_mm * cam_height_mm
    if min_xy_sq <= 0.0:
        return fly_pos

    min_xy = math.sqrt(min_xy_sq)
    xy_dist = math.sqrt(xy_dist_sq)

    if xy_dist < 1e-6:
        return (cx + min_xy, cy)

    scale = min_xy / xy_dist
    return (cx + dx * scale, cy + dy * scale)


def clamp_scale_for_near_plane(
    fly_scale: float,
    fly_bounding_radius: float,
    dist_3d: float,
    z_near: float,
    safety_margin: float = 0.9,
) -> float:
    """Cap the fly scale so the model does not clip the near plane.

    The maximum safe scale is
    ``(dist_3d - z_near) / fly_bounding_radius * safety_margin``.

    Args:
        fly_scale: The desired scale factor.
        fly_bounding_radius: Bounding sphere radius of the raw mesh.
        dist_3d: Current 3D camera-fly distance.
        z_near: Near clipping plane distance.
        safety_margin: Fraction of max scale to allow.

    Returns:
        The clamped scale factor.
    """
    available = dist_3d - z_near
    if available <= 0.0:
        return 0.0
    max_scale = (available / max(fly_bounding_radius, 1e-9)) * safety_margin
    return min(fly_scale, max_scale)
