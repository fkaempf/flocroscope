"""Tests for flocroscope.math_utils.arena."""

from __future__ import annotations

import math

import pytest

from flocroscope.math_utils.arena import (
    clamp_scale_for_near_plane,
    clamp_to_arena,
    compute_camera_fly_distance_mm,
    compute_min_cam_fly_dist_3d,
    enforce_min_distance,
    enforce_min_distance_3d,
)


class TestClampToArena:
    """Tests for clamp_to_arena."""

    def test_inside_unchanged(self) -> None:
        x, y = clamp_to_arena(5.0, 5.0, 40.0)
        assert x == pytest.approx(5.0)
        assert y == pytest.approx(5.0)

    def test_on_boundary_unchanged(self) -> None:
        x, y = clamp_to_arena(40.0, 0.0, 40.0)
        assert math.hypot(x, y) == pytest.approx(40.0)

    def test_outside_clamped(self) -> None:
        x, y = clamp_to_arena(60.0, 0.0, 40.0)
        assert math.hypot(x, y) == pytest.approx(40.0)
        assert x == pytest.approx(40.0)

    def test_origin_stays(self) -> None:
        x, y = clamp_to_arena(0.0, 0.0, 40.0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)

    def test_diagonal_outside(self) -> None:
        x, y = clamp_to_arena(100.0, 100.0, 40.0)
        assert math.hypot(x, y) == pytest.approx(40.0, abs=1e-4)


class TestEnforceMinDistance:
    """Tests for enforce_min_distance."""

    def test_already_far_enough(self) -> None:
        pos = enforce_min_distance((10.0, 0.0), (0.0, 0.0), 5.0)
        assert pos == pytest.approx((10.0, 0.0))

    def test_too_close_pushed_away(self) -> None:
        pos = enforce_min_distance((1.0, 0.0), (0.0, 0.0), 5.0)
        assert math.hypot(pos[0], pos[1]) == pytest.approx(5.0)

    def test_overlapping_pushed_along_x(self) -> None:
        pos = enforce_min_distance((0.0, 0.0), (0.0, 0.0), 3.0)
        assert pos == pytest.approx((3.0, 0.0))

    def test_at_exact_boundary(self) -> None:
        pos = enforce_min_distance((5.0, 0.0), (0.0, 0.0), 5.0)
        assert pos == pytest.approx((5.0, 0.0))


class TestComputeCameraFlyDistance:
    """Tests for compute_camera_fly_distance_mm."""

    def test_same_position_returns_height(self) -> None:
        dist = compute_camera_fly_distance_mm(
            (0.0, 0.0), (0.0, 0.0), 5.0,
        )
        assert dist == pytest.approx(5.0)

    def test_horizontal_distance(self) -> None:
        dist = compute_camera_fly_distance_mm(
            (3.0, 0.0), (0.0, 4.0), 0.0,
        )
        assert dist == pytest.approx(5.0)

    def test_3d_distance(self) -> None:
        dist = compute_camera_fly_distance_mm(
            (3.0, 0.0), (0.0, 4.0), 12.0,
        )
        assert dist == pytest.approx(13.0)


class TestComputeMinCamFlyDist3D:
    """Tests for compute_min_cam_fly_dist_3d."""

    def test_positive_and_reasonable(self) -> None:
        d_min = compute_min_cam_fly_dist_3d(
            z_near=1.0,
            fly_bounding_radius=1.5,
            fly_base_scale=1.0,
            screen_distance_mm=60.0,
        )
        assert d_min > 1.0
        assert d_min < 100.0

    def test_safety_margin_scales(self) -> None:
        d1 = compute_min_cam_fly_dist_3d(1.0, 1.5, 1.0, 60.0, 1.0)
        d2 = compute_min_cam_fly_dist_3d(1.0, 1.5, 1.0, 60.0, 1.5)
        assert d2 == pytest.approx(d1 * 1.5)

    def test_larger_fly_needs_more_distance(self) -> None:
        d_small = compute_min_cam_fly_dist_3d(1.0, 0.5, 1.0, 60.0, 1.0)
        d_large = compute_min_cam_fly_dist_3d(1.0, 3.0, 1.0, 60.0, 1.0)
        assert d_large > d_small

    def test_zero_bounding_radius(self) -> None:
        d = compute_min_cam_fly_dist_3d(1.0, 0.0, 1.0, 60.0, 1.0)
        assert d == pytest.approx(1.0)


class TestEnforceMinDistance3D:
    """Tests for enforce_min_distance_3d."""

    def test_already_far_enough(self) -> None:
        pos = enforce_min_distance_3d(
            (20.0, 0.0), (0.0, 0.0), 0.89, 5.0,
        )
        assert pos == pytest.approx((20.0, 0.0))

    def test_too_close_pushed_away(self) -> None:
        pos = enforce_min_distance_3d(
            (1.0, 0.0), (0.0, 0.0), 0.89, 5.0,
        )
        dist_3d = math.sqrt(pos[0] ** 2 + pos[1] ** 2 + 0.89 ** 2)
        assert dist_3d >= 5.0 - 0.01

    def test_directly_below_camera(self) -> None:
        pos = enforce_min_distance_3d(
            (0.0, 0.0), (0.0, 0.0), 0.89, 5.0,
        )
        assert pos[0] > 0.0
        dist_3d = math.sqrt(pos[0] ** 2 + pos[1] ** 2 + 0.89 ** 2)
        assert dist_3d >= 5.0 - 0.01

    def test_height_exceeds_min_dist(self) -> None:
        pos = enforce_min_distance_3d(
            (1.0, 1.0), (0.0, 0.0), 10.0, 5.0,
        )
        assert pos == pytest.approx((1.0, 1.0))

    def test_preserves_direction(self) -> None:
        pos = enforce_min_distance_3d(
            (1.0, 1.0), (0.0, 0.0), 0.89, 10.0,
        )
        # Direction from camera to fly should be preserved.
        assert pos[0] > 0.0
        assert pos[1] > 0.0
        assert pos[0] == pytest.approx(pos[1], rel=1e-3)


class TestClampScaleForNearPlane:
    """Tests for clamp_scale_for_near_plane."""

    def test_within_limit_unchanged(self) -> None:
        result = clamp_scale_for_near_plane(
            fly_scale=1.0,
            fly_bounding_radius=1.5,
            dist_3d=20.0,
            z_near=1.0,
        )
        assert result == pytest.approx(1.0)

    def test_excessive_scale_clamped(self) -> None:
        result = clamp_scale_for_near_plane(
            fly_scale=100.0,
            fly_bounding_radius=1.5,
            dist_3d=5.0,
            z_near=1.0,
        )
        assert result < 100.0
        assert result * 1.5 <= (5.0 - 1.0)

    def test_behind_camera_returns_zero(self) -> None:
        result = clamp_scale_for_near_plane(
            fly_scale=1.0,
            fly_bounding_radius=1.5,
            dist_3d=0.5,
            z_near=1.0,
        )
        assert result == 0.0

    def test_safety_margin_applied(self) -> None:
        r1 = clamp_scale_for_near_plane(100.0, 1.5, 5.0, 1.0, 0.9)
        r2 = clamp_scale_for_near_plane(100.0, 1.5, 5.0, 1.0, 0.5)
        assert r2 < r1
