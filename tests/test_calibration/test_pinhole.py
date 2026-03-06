"""Tests for flocroscope.calibration.pinhole."""

from __future__ import annotations

import inspect

import numpy as np
import pytest


class TestCharucoBoardConfig:
    """Tests for CharucoBoardConfig defaults and fields."""

    def test_default_values(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import CharucoBoardConfig

        cfg = CharucoBoardConfig()
        assert cfg.squares_x == 7
        assert cfg.squares_y == 5
        assert cfg.square_length == pytest.approx(0.03)
        assert cfg.marker_length == pytest.approx(0.015)
        assert cfg.aruco_dict_id == cv2.aruco.DICT_6X6_250

    def test_custom_board(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import CharucoBoardConfig

        cfg = CharucoBoardConfig(
            squares_x=10,
            squares_y=8,
            square_length=0.05,
            marker_length=0.025,
        )
        assert cfg.squares_x == 10
        assert cfg.squares_y == 8
        assert cfg.square_length == pytest.approx(0.05)
        assert cfg.marker_length == pytest.approx(0.025)

    def test_marker_smaller_than_square(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import CharucoBoardConfig

        cfg = CharucoBoardConfig()
        assert cfg.marker_length < cfg.square_length


class TestPinholeResult:
    """Tests for PinholeResult dataclass."""

    def test_creation(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import PinholeResult

        result = PinholeResult(
            K=np.eye(3),
            D=np.zeros(5),
            rms=0.5,
        )
        assert result.rms == pytest.approx(0.5)
        assert result.image_shape == (0, 0)
        assert result.rvecs == []
        assert result.tvecs == []
        np.testing.assert_array_equal(result.K, np.eye(3))

    def test_with_image_shape(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import PinholeResult

        result = PinholeResult(
            K=np.eye(3),
            D=np.zeros(5),
            rms=1.0,
            image_shape=(480, 640),
        )
        assert result.image_shape == (480, 640)

    def test_rvecs_tvecs_are_independent(self) -> None:
        """Ensure default_factory creates separate lists per instance."""
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import PinholeResult

        r1 = PinholeResult(K=np.eye(3), D=np.zeros(5), rms=0.1)
        r2 = PinholeResult(K=np.eye(3), D=np.zeros(5), rms=0.2)
        r1.rvecs.append(np.zeros(3))
        assert len(r2.rvecs) == 0


class TestMakeBoard:
    """Tests for the _make_board helper."""

    def test_returns_three_items(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import (
            CharucoBoardConfig,
            _make_board,
        )

        cfg = CharucoBoardConfig()
        result = _make_board(cfg)
        assert len(result) == 3

    def test_board_has_expected_size(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import (
            CharucoBoardConfig,
            _make_board,
        )

        cfg = CharucoBoardConfig(squares_x=7, squares_y=5)
        _, board, _ = _make_board(cfg)
        size = board.getChessboardSize()
        assert size == (7, 5)


class TestParseFunctions:
    """Tests for function signatures and parameter inspection."""

    def test_detect_charuco_corners_signature(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import detect_charuco_corners

        sig = inspect.signature(detect_charuco_corners)
        params = list(sig.parameters.keys())
        assert "image" in params
        assert "board_config" in params

    def test_calibrate_pinhole_signature(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import calibrate_pinhole

        sig = inspect.signature(calibrate_pinhole)
        params = list(sig.parameters.keys())
        assert "image_paths" in params
        assert "board_config" in params

    def test_detect_pose_signature(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import detect_pose

        sig = inspect.signature(detect_pose)
        params = list(sig.parameters.keys())
        assert "image" in params
        assert "K" in params
        assert "D" in params
        assert "board_config" in params
        assert "undistort" in params
        assert "draw_axes" in params
        assert "axis_length" in params

    def test_detect_pose_default_params(self) -> None:
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import detect_pose

        sig = inspect.signature(detect_pose)
        assert sig.parameters["undistort"].default is True
        assert sig.parameters["draw_axes"].default is True
        assert sig.parameters["axis_length"].default == pytest.approx(0.1)


class TestCalibratePinholeValidation:
    """Tests for calibrate_pinhole input validation."""

    def test_raises_on_insufficient_detections(self, tmp_path) -> None:
        """Calibration must fail if fewer than 3 valid images."""
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import calibrate_pinhole

        # Empty list: no images, so 0 detections < 3.
        with pytest.raises(RuntimeError, match="need >= 3"):
            calibrate_pinhole([])

    def test_raises_on_nonexistent_images(self, tmp_path) -> None:
        """Files that cv2.imread cannot read are skipped; too few remain."""
        cv2 = pytest.importorskip("cv2")
        from flocroscope.calibration.pinhole import calibrate_pinhole

        bogus = [tmp_path / f"fake_{i}.png" for i in range(5)]
        with pytest.raises(RuntimeError, match="need >= 3"):
            calibrate_pinhole(bogus)


@pytest.mark.hardware
class TestPinholeHardware:
    """Hardware-dependent pinhole calibration tests.

    These require a physical ChArUco board and camera, so they are
    automatically skipped in CI via the ``hardware`` marker.
    """

    def test_live_calibration(self) -> None:
        """Calibrate from live camera captures of a physical board."""

    def test_live_pose_detection(self) -> None:
        """Detect board pose from a live camera feed."""
