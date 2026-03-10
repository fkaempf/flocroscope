"""Tests for GUI theme constants and factory.

Colour constant tests are pure Python.  The ``create_theme()``
test requires DearPyGui and skips gracefully when unavailable.
"""

from __future__ import annotations

import pytest

from flocroscope.gui import theme


_COLOUR_ATTRS = [
    "BG_DARKEST", "BG_DARK", "BG_PANEL", "BG_ELEVATED",
    "BORDER", "SEPARATOR",
    "TEXT_PRIMARY", "TEXT_SECONDARY", "TEXT_DISABLED",
    "ACCENT", "ACCENT_HOVER", "ACCENT_ACTIVE",
    "STATUS_OK", "STATUS_WARN", "STATUS_ERR", "STATUS_OFF",
    "TAB_INACTIVE", "TAB_HOVER",
    "BUTTON_BG", "BUTTON_HOVER", "BUTTON_ACTIVE",
    "INPUT_BG", "INPUT_BORDER",
]

_STYLE_ATTRS = [
    "FRAME_PADDING", "ITEM_SPACING", "ITEM_INNER_SPACING",
    "WINDOW_PADDING",
]


class TestColourConstants:
    """Verify colour tuples have correct structure."""

    @pytest.mark.parametrize("name", _COLOUR_ATTRS)
    def test_colour_is_4_tuple(self, name: str) -> None:
        value = getattr(theme, name)
        assert isinstance(value, tuple)
        assert len(value) == 4

    @pytest.mark.parametrize("name", _COLOUR_ATTRS)
    def test_colour_values_in_range(self, name: str) -> None:
        value = getattr(theme, name)
        for channel in value:
            assert 0 <= channel <= 255


class TestStyleConstants:
    """Verify style tuples have correct structure."""

    @pytest.mark.parametrize("name", _STYLE_ATTRS)
    def test_padding_is_2_tuple(self, name: str) -> None:
        value = getattr(theme, name)
        assert isinstance(value, tuple)
        assert len(value) == 2

    def test_rounding_values_positive(self) -> None:
        assert theme.FRAME_ROUNDING > 0
        assert theme.TAB_ROUNDING > 0
        assert theme.CHILD_ROUNDING > 0

    def test_scrollbar_size_positive(self) -> None:
        assert theme.SCROLLBAR_SIZE > 0


class TestFontConstants:
    """Tests for font-related constants."""

    def test_font_size_positive(self) -> None:
        assert theme.FONT_SIZE > 0

    def test_font_search_paths_non_empty(self) -> None:
        assert len(theme._FONT_SEARCH_PATHS) > 0

    def test_find_font_returns_path_or_none(self) -> None:
        result = theme._find_font()
        if result is not None:
            from pathlib import Path
            assert isinstance(result, Path)
            assert result.exists()


class TestCreateTheme:
    """Tests for the create_theme() factory."""

    def test_create_theme_requires_dearpygui(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for create_theme()")


class TestLoadFont:
    """Tests for the load_font() function."""

    def test_load_font_requires_dearpygui(self) -> None:
        pytest.importorskip("dearpygui")
        pytest.skip("viewport required for load_font()")
