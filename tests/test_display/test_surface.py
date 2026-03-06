"""Tests for flocroscope.display.surface."""

from __future__ import annotations

import inspect

import numpy as np
import pytest


class TestFrameToSurface:
    """Tests for the frame_to_surface helper."""

    def test_function_exists(self) -> None:
        from flocroscope.display.surface import frame_to_surface

        assert callable(frame_to_surface)

    def test_signature(self) -> None:
        from flocroscope.display.surface import frame_to_surface

        sig = inspect.signature(frame_to_surface)
        params = list(sig.parameters.keys())
        assert "img" in params
        assert "target_size" in params

    def test_target_size_defaults_to_none(self) -> None:
        from flocroscope.display.surface import frame_to_surface

        sig = inspect.signature(frame_to_surface)
        assert sig.parameters["target_size"].default is None

    def test_converts_bgr_image(self) -> None:
        cv2 = pytest.importorskip("cv2")
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.surface import frame_to_surface

        if not pygame.get_init():
            pygame.init()
        bgr = np.zeros((10, 20, 3), dtype=np.uint8)
        bgr[:, :, 0] = 255  # blue channel
        surface = frame_to_surface(bgr)
        assert surface.get_size() == (20, 10)

    def test_converts_grayscale_image(self) -> None:
        cv2 = pytest.importorskip("cv2")
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.surface import frame_to_surface

        if not pygame.get_init():
            pygame.init()
        gray = np.full((8, 16), 128, dtype=np.uint8)
        surface = frame_to_surface(gray)
        assert surface.get_size() == (16, 8)

    def test_converts_bgra_image(self) -> None:
        cv2 = pytest.importorskip("cv2")
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.surface import frame_to_surface

        if not pygame.get_init():
            pygame.init()
        bgra = np.zeros((10, 20, 4), dtype=np.uint8)
        surface = frame_to_surface(bgra)
        assert surface.get_size() == (20, 10)

    def test_scaling_with_target_size(self) -> None:
        cv2 = pytest.importorskip("cv2")
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.surface import frame_to_surface

        if not pygame.get_init():
            pygame.init()
        bgr = np.zeros((10, 20, 3), dtype=np.uint8)
        surface = frame_to_surface(bgr, target_size=(40, 20))
        assert surface.get_size() == (40, 20)

    def test_no_scaling_when_size_matches(self) -> None:
        cv2 = pytest.importorskip("cv2")
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.surface import frame_to_surface

        if not pygame.get_init():
            pygame.init()
        bgr = np.zeros((10, 20, 3), dtype=np.uint8)
        surface = frame_to_surface(bgr, target_size=(20, 10))
        assert surface.get_size() == (20, 10)


class TestBgrToSurface:
    """Tests for the bgr_to_surface convenience wrapper."""

    def test_function_exists(self) -> None:
        from flocroscope.display.surface import bgr_to_surface

        assert callable(bgr_to_surface)

    def test_signature(self) -> None:
        from flocroscope.display.surface import bgr_to_surface

        sig = inspect.signature(bgr_to_surface)
        params = list(sig.parameters.keys())
        assert "bgr" in params

    def test_delegates_to_frame_to_surface(self) -> None:
        cv2 = pytest.importorskip("cv2")
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.surface import bgr_to_surface

        if not pygame.get_init():
            pygame.init()
        bgr = np.zeros((12, 24, 3), dtype=np.uint8)
        surface = bgr_to_surface(bgr)
        assert surface.get_size() == (24, 12)
