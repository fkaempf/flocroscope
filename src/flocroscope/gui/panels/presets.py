"""Experiment presets panel.

Provides controls for saving, loading, and managing experiment
configuration presets from the GUI.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocroscope.config.schema import FlocroscopeConfig
    from flocroscope.gui.presets import PresetManager

logger = logging.getLogger(__name__)


class PresetsPanel:
    """Panel for managing experiment presets.

    Args:
        config: Application configuration (mutable reference).
        preset_manager: The preset manager instance.
        current_user: Username of the logged-in user (for author).
    """

    def __init__(
        self,
        config: FlocroscopeConfig,
        preset_manager: PresetManager,
        current_user: str = "",
    ) -> None:
        self._config = config
        self._pm = preset_manager
        self._current_user = current_user
        self._preset_name = ""
        self._preset_desc = ""
        self._preset_tags = ""
        self._selected_preset = ""
        self._experiment_mode = "Behaviour"
        self._status_msg = ""
        self._preset_list: list[str] = []
        self._filter_by_mode = False
        self._filter_tag = ""
        self.group_tag = "grp_presets"

    @property
    def window_tag(self) -> str:
        return self.group_tag

    @property
    def current_user(self) -> str:
        return self._current_user

    @current_user.setter
    def current_user(self, value: str) -> None:
        self._current_user = value

    @property
    def experiment_mode(self) -> str:
        return self._experiment_mode

    @experiment_mode.setter
    def experiment_mode(self, value: str) -> None:
        self._experiment_mode = value

    def build(self, parent: int | str = 0) -> None:
        """Create all DearPyGui widgets (called once)."""
        import dearpygui.dearpygui as dpg

        with dpg.group(parent=parent, tag=self.group_tag):
            dpg.add_text("Experiment Presets")
            dpg.add_separator()

            # -- Save section --
            with dpg.collapsing_header(
                label="Save Current Config as Preset",
                default_open=True,
            ):
                dpg.add_input_text(
                    label="Preset Name",
                    tag="preset_name",
                    width=300,
                    callback=self._on_name,
                )
                dpg.add_input_text(
                    label="Description",
                    tag="preset_desc",
                    width=300,
                    callback=self._on_desc,
                )
                dpg.add_input_text(
                    label="Tags (comma-separated)",
                    tag="preset_tags",
                    width=300,
                    callback=self._on_tags,
                )
                dpg.add_spacer(height=4)
                dpg.add_button(
                    label="Save Preset",
                    tag="preset_save_btn",
                    callback=self._on_save,
                    width=140,
                )

            dpg.add_spacer(height=8)

            # -- Load section --
            with dpg.collapsing_header(
                label="Load Preset",
                default_open=True,
            ):
                dpg.add_text(
                    "0 presets", tag="preset_count",
                    color=(140, 140, 155),
                )
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(
                        label="Filter by mode",
                        tag="preset_filter_mode",
                        default_value=False,
                        callback=self._on_filter_mode,
                    )
                    dpg.add_input_text(
                        label="Tag filter",
                        tag="preset_filter_tag",
                        width=150,
                        callback=self._on_filter_tag,
                    )
                dpg.add_combo(
                    items=[],
                    label="Select Preset",
                    tag="preset_selector",
                    width=300,
                    callback=self._on_select,
                )
                dpg.add_spacer(height=2)
                dpg.add_text(
                    "", tag="preset_info",
                    wrap=450,
                )
                dpg.add_spacer(height=4)
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Load",
                        tag="preset_load_btn",
                        callback=self._on_load,
                        width=80,
                    )
                    dpg.add_button(
                        label="Duplicate",
                        tag="preset_dup_btn",
                        callback=self._on_duplicate,
                        width=80,
                    )
                    dpg.add_button(
                        label="Delete",
                        tag="preset_delete_btn",
                        callback=self._on_delete,
                        width=80,
                    )
                    dpg.add_button(
                        label="Refresh",
                        tag="preset_refresh_btn",
                        callback=self._on_refresh,
                        width=80,
                    )

            dpg.add_spacer(height=4)
            dpg.add_text("", tag="preset_status")

    def update(self) -> None:
        """Push status each frame."""
        import dearpygui.dearpygui as dpg

        dpg.set_value("preset_status", self._status_msg)

        # Refresh preset list periodically on first frame
        if not self._preset_list:
            self._refresh_list()

    # -- callbacks ---------------------------------------------------- #

    def _on_name(self, sender, app_data, user_data):
        self._preset_name = app_data

    def _on_desc(self, sender, app_data, user_data):
        self._preset_desc = app_data

    def _on_tags(self, sender, app_data, user_data):
        self._preset_tags = app_data

    def _on_select(self, sender, app_data, user_data):
        self._selected_preset = app_data
        self._show_preset_info()

    def _on_save(self, sender, app_data, user_data):
        self._save_preset()

    def _on_load(self, sender, app_data, user_data):
        self._load_preset()

    def _on_duplicate(self, sender, app_data, user_data):
        self._duplicate_preset()

    def _on_delete(self, sender, app_data, user_data):
        self._delete_preset()

    def _on_filter_mode(self, sender, app_data, user_data):
        self._filter_by_mode = app_data
        self._refresh_list()

    def _on_filter_tag(self, sender, app_data, user_data):
        self._filter_tag = app_data
        self._refresh_list()

    def _on_refresh(self, sender, app_data, user_data):
        self._refresh_list()

    # -- actions ------------------------------------------------------ #

    def _save_preset(self) -> None:
        if not self._preset_name:
            self._status_msg = "Enter a preset name"
            return

        tags = [
            t.strip() for t in self._preset_tags.split(",")
            if t.strip()
        ]

        try:
            self._pm.save_preset(
                name=self._preset_name,
                config=self._config,
                description=self._preset_desc,
                author=self._current_user,
                experiment_mode=self._experiment_mode,
                tags=tags,
            )
            self._status_msg = (
                f"Saved preset: {self._preset_name}"
            )
            self._refresh_list()
        except Exception as exc:
            self._status_msg = f"Save failed: {exc}"

    def _load_preset(self) -> None:
        if not self._selected_preset:
            self._status_msg = "Select a preset to load"
            return

        result = self._pm.load_preset(self._selected_preset)
        if result is None:
            self._status_msg = (
                f"Preset '{self._selected_preset}' not found"
            )
            return

        _, loaded_config = result
        for f in dataclasses.fields(loaded_config):
            setattr(
                self._config, f.name,
                getattr(loaded_config, f.name),
            )
        self._status_msg = (
            f"Loaded preset: {self._selected_preset}"
        )
        logger.info(
            "Loaded preset: %s", self._selected_preset,
        )

    def _duplicate_preset(self) -> None:
        if not self._selected_preset:
            self._status_msg = "Select a preset to duplicate"
            return

        result = self._pm.load_preset(self._selected_preset)
        if result is None:
            self._status_msg = (
                f"Preset '{self._selected_preset}' not found"
            )
            return

        original, loaded_config = result
        new_name = f"{original.name} (copy)"
        # Avoid name collision
        counter = 2
        while self._pm.preset_exists(new_name):
            new_name = f"{original.name} (copy {counter})"
            counter += 1

        try:
            self._pm.save_preset(
                name=new_name,
                config=loaded_config,
                description=original.description,
                author=self._current_user,
                experiment_mode=original.experiment_mode,
                tags=list(original.tags),
            )
            self._status_msg = f"Duplicated as: {new_name}"
            self._refresh_list()
        except Exception as exc:
            self._status_msg = f"Duplicate failed: {exc}"

    def _delete_preset(self) -> None:
        if not self._selected_preset:
            self._status_msg = "Select a preset to delete"
            return

        if self._pm.delete_preset(self._selected_preset):
            self._status_msg = (
                f"Deleted preset: {self._selected_preset}"
            )
            self._selected_preset = ""
            self._refresh_list()
        else:
            self._status_msg = "Preset not found"

    def _refresh_list(self) -> None:
        mode = (
            self._experiment_mode if self._filter_by_mode
            else ""
        )
        presets = self._pm.list_presets_filtered(
            experiment_mode=mode,
            tag=self._filter_tag,
        )
        self._preset_list = [p.name for p in presets]
        total = len(self._pm.list_presets())
        showing = len(self._preset_list)
        try:
            import dearpygui.dearpygui as dpg
            dpg.configure_item(
                "preset_selector",
                items=self._preset_list,
            )
            count_text = (
                f"{showing} of {total} presets"
                if showing != total
                else f"{total} preset(s)"
            )
            dpg.set_value("preset_count", count_text)
        except Exception:
            pass

    def _show_preset_info(self) -> None:
        if not self._selected_preset:
            try:
                import dearpygui.dearpygui as dpg
                dpg.set_value("preset_info", "")
            except Exception:
                pass
            return

        meta = self._pm.load_preset_metadata(
            self._selected_preset,
        )
        if meta is None:
            try:
                import dearpygui.dearpygui as dpg
                dpg.set_value("preset_info", "")
            except Exception:
                pass
            return

        lines = [
            f"Name: {meta.name}",
            f"Author: {meta.author or 'unknown'}",
            f"Mode: {meta.experiment_mode}",
            f"Created: {meta.created_at}",
            f"Updated: {meta.updated_at}",
        ]
        if meta.description:
            lines.append(f"Desc: {meta.description}")
        if meta.tags:
            lines.append(
                f"Tags: {', '.join(meta.tags)}",
            )
        try:
            import dearpygui.dearpygui as dpg
            dpg.set_value("preset_info", "\n".join(lines))
        except Exception:
            pass
