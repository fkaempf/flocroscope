"""Dark theme and styling for the Flocroscope GUI.

Provides a professional dark theme with a teal accent colour,
generous whitespace, and clean typography hierarchy.  Call
:func:`create_theme` once after ``dpg.create_context()`` and bind
the returned ID with ``dpg.bind_theme(theme_id)``.
"""

from __future__ import annotations

# ------------------------------------------------------------------ #
#  Colour palette  (0-255 RGBA)
# ------------------------------------------------------------------ #

# Background tiers (darkest → lightest)
BG_DARKEST = (18, 18, 22, 255)
BG_DARK = (25, 25, 32, 255)
BG_PANEL = (34, 34, 42, 255)
BG_ELEVATED = (42, 42, 52, 255)

# Borders & separators
BORDER = (55, 55, 68, 255)
SEPARATOR = (48, 48, 58, 255)

# Text hierarchy
TEXT_PRIMARY = (220, 220, 228, 255)
TEXT_SECONDARY = (140, 140, 155, 255)
TEXT_DISABLED = (85, 85, 100, 255)

# Accent — teal, used sparingly
ACCENT = (0, 184, 172, 255)
ACCENT_HOVER = (0, 210, 196, 255)
ACCENT_ACTIVE = (0, 156, 146, 255)

# Semantic status colours
STATUS_OK = (72, 210, 120, 255)
STATUS_WARN = (240, 190, 60, 255)
STATUS_ERR = (220, 70, 70, 255)
STATUS_OFF = (100, 100, 115, 255)

# Tabs
TAB_INACTIVE = (38, 38, 48, 255)
TAB_HOVER = (50, 50, 62, 255)

# Buttons
BUTTON_BG = (45, 45, 58, 255)
BUTTON_HOVER = (55, 55, 70, 255)
BUTTON_ACTIVE = (0, 184, 172, 255)

# Inputs
INPUT_BG = (22, 22, 30, 255)
INPUT_BORDER = (55, 55, 68, 255)

# ------------------------------------------------------------------ #
#  Style constants
# ------------------------------------------------------------------ #

FRAME_PADDING = (10, 8)
ITEM_SPACING = (10, 8)
ITEM_INNER_SPACING = (8, 6)
WINDOW_PADDING = (16, 16)
FRAME_ROUNDING = 5.0
TAB_ROUNDING = 4.0
CHILD_ROUNDING = 4.0
SCROLLBAR_SIZE = 12.0
GRAB_MIN_SIZE = 10.0


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

    return theme_id
