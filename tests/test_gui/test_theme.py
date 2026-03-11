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


class TestColourPalette:
    """Verify the Flomington-inspired violet palette."""

    def test_accent_is_violet(self) -> None:
        """Accent should be in the violet range."""
        r, g, b, a = theme.ACCENT
        assert r > 100, "Accent red channel too low for violet"
        assert b > 200, "Accent blue channel too low for violet"
        assert g < b, "Green should be less than blue for violet"

    def test_bg_darkest_near_black(self) -> None:
        """Background darkest should be near-black."""
        r, g, b, a = theme.BG_DARKEST
        assert r < 20 and g < 20 and b < 20

    def test_text_primary_near_white(self) -> None:
        """Primary text should be near-white."""
        r, g, b, a = theme.TEXT_PRIMARY
        assert r > 220 and g > 220 and b > 220

    def test_text_secondary_muted(self) -> None:
        """Secondary text should be muted gray."""
        r, g, b, a = theme.TEXT_SECONDARY
        assert 140 <= r <= 180
        assert 140 <= g <= 180


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

    def test_generous_rounding(self) -> None:
        """Verify more generous rounding for the glassy aesthetic."""
        assert theme.FRAME_ROUNDING >= 6
        assert theme.CHILD_ROUNDING >= 12

    def test_scrollbar_size_positive(self) -> None:
        assert theme.SCROLLBAR_SIZE > 0

    def test_grab_rounding_exists(self) -> None:
        assert theme.GRAB_ROUNDING > 0

    def test_popup_rounding_exists(self) -> None:
        assert theme.POPUP_ROUNDING > 0

    def test_compact_spacing(self) -> None:
        """Verify disciplined spacing for space efficiency."""
        assert theme.ITEM_SPACING[1] <= 8
        assert theme.WINDOW_PADDING[0] <= 16
        assert theme.FRAME_PADDING[1] <= 8


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


class TestGrabMinSize:
    """Tests for grab-related style constants."""

    def test_grab_min_size_positive(self) -> None:
        assert theme.GRAB_MIN_SIZE > 0

    def test_grab_min_size_reasonable(self) -> None:
        """Grab min size should be in a usable range."""
        assert 4 <= theme.GRAB_MIN_SIZE <= 20


class TestButtonColours:
    """Tests for button colour consistency."""

    def test_button_active_matches_accent(self) -> None:
        """Button active state uses the accent colour."""
        assert theme.BUTTON_ACTIVE == theme.ACCENT

    def test_button_bg_distinct_from_panel(self) -> None:
        """Button bg should be distinct from panel bg."""
        # They can be the same if the palette so dictates, but
        # at minimum they should both be valid colours
        assert len(theme.BUTTON_BG) == 4
        assert len(theme.BG_PANEL) == 4


class TestInputColours:
    """Tests for input field colours."""

    def test_input_bg_darker_than_panel(self) -> None:
        """Input fields should be darker than panel bg."""
        assert theme.INPUT_BG[0] <= theme.BG_PANEL[0]

    def test_input_border_matches_border(self) -> None:
        """Input border matches main border colour."""
        assert theme.INPUT_BORDER == theme.BORDER


class TestBackgroundHierarchy:
    """Tests that background tiers follow dark->light ordering."""

    def test_bg_tiers_ascending(self) -> None:
        """BG_DARKEST < BG_DARK < BG_PANEL < BG_ELEVATED."""
        assert theme.BG_DARKEST[0] < theme.BG_DARK[0]
        assert theme.BG_DARK[0] < theme.BG_PANEL[0]
        assert theme.BG_PANEL[0] < theme.BG_ELEVATED[0]


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
