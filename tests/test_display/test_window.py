"""Tests for flocroscope.display.window."""

from __future__ import annotations

import inspect

import pytest


class TestSetupPygameWindow:
    """Tests for setup_pygame_window."""

    def test_function_exists(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        assert callable(setup_pygame_window)

    def test_signature_parameters(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        sig = inspect.signature(setup_pygame_window)
        params = list(sig.parameters.keys())
        assert "width" in params
        assert "height" in params
        assert "monitor_x" in params
        assert "monitor_y" in params
        assert "borderless" in params
        assert "opengl" in params

    def test_default_monitor_x(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        sig = inspect.signature(setup_pygame_window)
        assert sig.parameters["monitor_x"].default == 0

    def test_default_monitor_y(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        sig = inspect.signature(setup_pygame_window)
        assert sig.parameters["monitor_y"].default == 0

    def test_default_borderless(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        sig = inspect.signature(setup_pygame_window)
        assert sig.parameters["borderless"].default is True

    def test_default_opengl(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        sig = inspect.signature(setup_pygame_window)
        assert sig.parameters["opengl"].default is True

    def test_width_and_height_are_required(self) -> None:
        from flocroscope.display.window import setup_pygame_window

        sig = inspect.signature(setup_pygame_window)
        # Required params have no default (Parameter.empty).
        assert (
            sig.parameters["width"].default is inspect.Parameter.empty
        )
        assert (
            sig.parameters["height"].default is inspect.Parameter.empty
        )

    def test_creates_window_without_opengl(self) -> None:
        """Create a non-OpenGL pygame window (no GPU required)."""
        pygame = pytest.importorskip("pygame")
        from flocroscope.display.window import setup_pygame_window

        screen = setup_pygame_window(
            width=320,
            height=240,
            borderless=False,
            opengl=False,
        )
        assert screen.get_size() == (320, 240)
        pygame.quit()

    def test_sets_sdl_window_position(self) -> None:
        """Verify SDL_VIDEO_WINDOW_POS env var is set."""
        import os

        pygame = pytest.importorskip("pygame")
        from flocroscope.display.window import setup_pygame_window

        setup_pygame_window(
            width=160,
            height=120,
            monitor_x=100,
            monitor_y=200,
            borderless=False,
            opengl=False,
        )
        assert os.environ.get("SDL_VIDEO_WINDOW_POS") == "100,200"
        pygame.quit()
