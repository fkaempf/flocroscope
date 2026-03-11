"""Dark theme and styling for the Flocroscope GUI.

Provides a Flomington-inspired dark theme with a violet accent,
generous rounding, and a glassy scientific-luxe aesthetic.  Call
:func:`create_theme` once after ``dpg.create_context()`` and bind
the returned ID with ``dpg.bind_theme(theme_id)``.
Call :func:`load_font` to bind a nice monospace font (Consolas
preferred, with cross-platform fallbacks).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Colour palette  (0-255 RGBA)
# ------------------------------------------------------------------ #

# Background tiers (darkest -> lightest)
BG_DARKEST = (9, 9, 11, 255)
BG_DARK = (17, 17, 19, 255)
BG_PANEL = (24, 24, 28, 255)
BG_ELEVATED = (32, 32, 38, 255)

# Borders & separators
BORDER = (44, 44, 52, 255)
SEPARATOR = (38, 38, 45, 255)

# Text hierarchy
TEXT_PRIMARY = (240, 240, 245, 255)
TEXT_SECONDARY = (161, 161, 170, 255)
TEXT_DISABLED = (75, 75, 90, 255)

# Accent -- violet, used sparingly
ACCENT = (139, 92, 246, 255)
ACCENT_HOVER = (167, 125, 255, 255)
ACCENT_ACTIVE = (114, 68, 220, 255)

# Semantic status colours
STATUS_OK = (72, 210, 120, 255)
STATUS_WARN = (245, 195, 65, 255)
STATUS_ERR = (235, 70, 70, 255)
STATUS_OFF = (100, 100, 115, 255)

# Tabs
TAB_INACTIVE = (20, 20, 24, 255)
TAB_HOVER = (36, 36, 42, 255)

# Buttons
BUTTON_BG = (34, 34, 42, 255)
BUTTON_HOVER = (44, 44, 54, 255)
BUTTON_ACTIVE = (139, 92, 246, 255)

# Inputs
INPUT_BG = (14, 14, 18, 255)
INPUT_BORDER = (44, 44, 52, 255)

# ------------------------------------------------------------------ #
#  Style constants
# ------------------------------------------------------------------ #

FRAME_PADDING = (10, 6)
ITEM_SPACING = (10, 5)
ITEM_INNER_SPACING = (8, 5)
WINDOW_PADDING = (14, 10)
FRAME_ROUNDING = 6.0
TAB_ROUNDING = 6.0
CHILD_ROUNDING = 12.0
SCROLLBAR_SIZE = 10.0
GRAB_MIN_SIZE = 10.0
GRAB_ROUNDING = 4.0
POPUP_ROUNDING = 8.0


def create_theme() -> int:
    """Build and return a DearPyGui theme ID.

    The caller must bind it globally with
    ``dpg.bind_theme(create_theme())``.
    """
    import dearpygui.dearpygui as dpg

    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            # -- colours --
            dpg.add_theme_color(
                dpg.mvThemeCol_WindowBg, BG_DARKEST,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ChildBg, BG_DARK,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_PopupBg, BG_DARK,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBg, BG_PANEL,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBgHovered, BG_ELEVATED,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBgActive, ACCENT_ACTIVE,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TitleBg, BG_DARKEST,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TitleBgActive, BG_DARK,
            )

            # Tabs
            dpg.add_theme_color(
                dpg.mvThemeCol_Tab, TAB_INACTIVE,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TabHovered, TAB_HOVER,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TabActive, BG_DARK,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TabUnfocused, TAB_INACTIVE,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TabUnfocusedActive, BG_DARK,
            )

            # Buttons
            dpg.add_theme_color(
                dpg.mvThemeCol_Button, BUTTON_BG,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered, BUTTON_HOVER,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive, BUTTON_ACTIVE,
            )

            # Headers (collapsing headers)
            dpg.add_theme_color(
                dpg.mvThemeCol_Header, BG_PANEL,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_HeaderHovered, BG_ELEVATED,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_HeaderActive, ACCENT_ACTIVE,
            )

            # Borders & separators
            dpg.add_theme_color(
                dpg.mvThemeCol_Border, BORDER,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_Separator, SEPARATOR,
            )

            # Text
            dpg.add_theme_color(
                dpg.mvThemeCol_Text, TEXT_PRIMARY,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_TextDisabled, TEXT_DISABLED,
            )

            # Scrollbar
            dpg.add_theme_color(
                dpg.mvThemeCol_ScrollbarBg, BG_DARKEST,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ScrollbarGrab, BORDER,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ScrollbarGrabHovered,
                ACCENT_HOVER,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ScrollbarGrabActive, ACCENT,
            )

            # Accented widgets
            dpg.add_theme_color(
                dpg.mvThemeCol_CheckMark, ACCENT,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_SliderGrab, ACCENT,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_SliderGrabActive, ACCENT_ACTIVE,
            )

            # -- styles --
            dpg.add_theme_style(
                dpg.mvStyleVar_FramePadding, *FRAME_PADDING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_ItemSpacing, *ITEM_SPACING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_ItemInnerSpacing,
                *ITEM_INNER_SPACING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_WindowPadding, *WINDOW_PADDING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding, FRAME_ROUNDING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_TabRounding, TAB_ROUNDING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_ChildRounding, CHILD_ROUNDING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_ScrollbarSize, SCROLLBAR_SIZE,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_GrabMinSize, GRAB_MIN_SIZE,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_GrabRounding, GRAB_ROUNDING,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_PopupRounding, POPUP_ROUNDING,
            )

    return theme_id


# ------------------------------------------------------------------ #
#  Font
# ------------------------------------------------------------------ #

FONT_SIZE = 16

# Preferred fonts in order -- first existing file wins.
_FONT_SEARCH_PATHS = [
    # Windows (via WSL or native)
    Path("/mnt/c/Windows/Fonts/consola.ttf"),
    Path("C:/Windows/Fonts/consola.ttf"),
    Path("/mnt/c/Windows/Fonts/CascadiaMono.ttf"),
    Path("C:/Windows/Fonts/CascadiaMono.ttf"),
    # macOS
    Path("/System/Library/Fonts/Menlo.ttc"),
    Path("/System/Library/Fonts/SFMono-Regular.otf"),
    # Linux common locations
    Path("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"),
    Path(
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ),
    Path(
        "/usr/share/fonts/truetype/liberation/"
        "LiberationMono-Regular.ttf",
    ),
]


def _find_font() -> Path | None:
    """Return the first font file found from the search list."""
    for p in _FONT_SEARCH_PATHS:
        if p.exists():
            return p
    return None


def load_font(size: int = FONT_SIZE) -> int | None:
    """Load and bind a monospace font.

    Searches for Consolas, Cascadia Mono, Menlo, Ubuntu Mono,
    or DejaVu Sans Mono.  Returns the font ID on success, or
    ``None`` if no suitable font was found (DPG default is used).

    Must be called after ``dpg.create_context()``.
    """
    import dearpygui.dearpygui as dpg

    font_path = _find_font()
    if font_path is None:
        logger.info(
            "No preferred font found; using DPG default",
        )
        return None

    with dpg.font_registry():
        font_id = dpg.add_font(str(font_path), size)

    dpg.bind_font(font_id)
    logger.info("Loaded font: %s (%dpt)", font_path.name, size)
    return font_id
